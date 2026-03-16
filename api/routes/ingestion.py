import os
import shutil
from typing import List
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Depends, Request
from core.database import db, logger
from core.config import settings
from core.postgres import get_db
from core.security import RoleChecker, get_current_user
from services.news_monitor import extract_news_risk_via_llm
from services.erp_integration import ingest_erp_bom
from models.schemas import ContractData, RawTextPayload, ERPBOMPayload, NewsRiskData, TokenData
from models.pg_models import AuditLog, DocumentMetadata, User as DBUser
from services.ingestion_tasks import process_document_task
from services.ingestion_core import process_pdf_and_extract, process_contract, extract_contract_via_llm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.prompt_loader import load_prompt

router = APIRouter(prefix="/api/ingest", tags=["Ingestion"])

# RBAC Dependencies
admin_only = RoleChecker(["admin"])
analyst_or_admin = RoleChecker(["analyst", "admin"])


@router.post("/process-contract", status_code=status.HTTP_201_CREATED)
async def process_contract_route(
    request: Request,
    contract: ContractData, 
    current_user: TokenData = Depends(get_current_user),
    db_sql: AsyncSession = Depends(get_db)
):
    if contract.overall_extraction_confidence < 0.5:
        raise HTTPException(status_code=422, detail="Extraction confidence too low. Requires manual review.")

    try:
        return await process_contract(contract, current_user, db_sql, ip_address=request.client.host)
    except Exception as e:
        logger.error(f"Failed to map contract to Neo4j: {e}")
        raise HTTPException(status_code=500, detail="Database mapping failed")

@router.post("/process-news", status_code=status.HTTP_201_CREATED)
async def process_news(
    request: Request,
    news: NewsRiskData, 
    current_user: TokenData = Depends(get_current_user),
    db_sql: AsyncSession = Depends(get_db)
):

    from core.outbox import push_to_outbox
    
    params = {
        "event_type": news.event_classification.event_type,
        "severity": news.event_classification.severity,
        "summary": news.summary,
        "impacted_entities": news.impact_details.entities_affected,
        "username": current_user.username
    }
    
    try:
        # Instead of direct Neo4j update, push to Outbox
        await push_to_outbox(db_sql, "sync_news", params)
        
        # Audit Log in PostgreSQL
        if db_sql:
            user_res = await db_sql.execute(select(DBUser).filter(DBUser.username == current_user.username))
            user = user_res.scalars().first()
            if user:
                import json
                audit = AuditLog(
                    user_id=user.id, 
                    action="ingest_news", 
                    target_node=news.event_classification.event_type,
                    new_value=json.dumps(news.model_dump()),
                    ip_address=request.client.host
                )
                db_sql.add(audit)
        
        # Commit both Outbox and Audit Log
        await db_sql.commit()
                
        return {"message": f"News event '{news.event_classification.event_type}' queued for Knowledge Graph sync"}
    except Exception as e:
        logger.error(f"Failed to queue news for Neo4j: {e}")
        raise HTTPException(status_code=500, detail="Database queuing failed")

@router.post("/upload-contract", status_code=status.HTTP_201_CREATED)
async def upload_pdf(
    request: Request,
    file: UploadFile = File(...), 
    current_user: TokenData = Depends(admin_only),
    db_sql: AsyncSession = Depends(get_db)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
        
    # Check file size
    if file.size > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size allowed is {settings.max_upload_size_mb}MB."
        )
        
    # Persistent temp path for the worker to pick up
    temp_dir = "/tmp/ntier_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"{current_user.username}_{file.filename}")
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Track Document Metadata in PG
        user_res = await db_sql.execute(select(DBUser).filter(DBUser.username == current_user.username))
        user = user_res.scalars().first()
        
        doc_meta = DocumentMetadata(filename=file.filename, user_id=user.id if user else None, status="pending")
        db_sql.add(doc_meta)
        await db_sql.commit()
        await db_sql.refresh(doc_meta)

        # Trigger Celery Task instead of inline processing
        process_document_task.delay(temp_path, file.filename, user.id, ip_address=request.client.host)
        
        return {"message": "Document uploaded and queued for processing", "filename": file.filename}
        
    except Exception as e:
        logger.error(f"Error uploading and queuing PDF: {str(e)}", exc_info=True)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", response_model=List[dict], dependencies=[Depends(analyst_or_admin)])
async def get_ingestion_history(
    current_user: TokenData = Depends(get_current_user),
    db_sql: AsyncSession = Depends(get_db)
):
    """Retrieves history of uploaded documents for the current user."""
    user_res = await db_sql.execute(select(DBUser).filter(DBUser.username == current_user.username))
    user = user_res.scalars().first()
    
    if not user:
        return []
        
    res = await db_sql.execute(select(DocumentMetadata).filter(DocumentMetadata.user_id == user.id).order_by(DocumentMetadata.id.desc()))
    docs = res.scalars().all()
    
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "status": d.status,
            "created_at": d.created_at.isoformat() if d.created_at else None
        } for d in docs
    ]

@router.post("/analyze-raw-text", status_code=status.HTTP_200_OK)
async def analyze_raw_text(
    request: Request,
    payload: RawTextPayload, 
    current_user: TokenData = Depends(admin_only),
    db_sql: AsyncSession = Depends(get_db)
):
    """Parses raw text containing [TYPE: ...] tags."""
    raw_text = payload.text.strip()
    if raw_text.startswith("[TYPE: CONTRACT_PDF]"):
        extracted_data = await extract_contract_via_llm(raw_text)
        return await process_contract(extracted_data, current_user, db_sql, ip_address=request.client.host)
    elif raw_text.startswith("[TYPE: NEWS_FEED]"):
        extracted_data = await extract_news_risk_via_llm(raw_text)
        # Note: process_news also needs request for its inline audit log
        return await process_news(request, extracted_data, current_user=current_user, db_sql=db_sql)
    else:
        raise HTTPException(status_code=400, detail="Unknown input format. Use [TYPE: ...] tags.")

@router.post("/erp-bom", status_code=status.HTTP_201_CREATED)
async def map_erp_bom(
    request: Request,
    payload: ERPBOMPayload, 
    current_user: TokenData = Depends(admin_only),
    db_sql: AsyncSession = Depends(get_db)
):
    try:
        # Refactored: ingest_erp_bom now pushes to outbox
        result = await ingest_erp_bom(payload, db_sql=db_sql, current_user=current_user)
        
        # Audit Log in PostgreSQL
        user_res = await db_sql.execute(select(DBUser).filter(DBUser.username == current_user.username))
        user = user_res.scalars().first()
        if user:
            import json
            audit = AuditLog(
                user_id=user.id, 
                action="ingest_erp_bom", 
                target_node=payload.factory,
                new_value=json.dumps(payload.model_dump()),
                ip_address=request.client.host
            )
            db_sql.add(audit)
        
        # Commit both transactionally
        await db_sql.commit()
        return result
            
    except Exception as e:
        logger.error(f"Error queuing ERP BOM: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
