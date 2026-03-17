import os
import shutil
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Depends, Request, Query
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
from fastapi.responses import StreamingResponse
import asyncio
import json
import redis.asyncio as redis

from core.prompt_loader import load_prompt

router = APIRouter(prefix="/api/ingest", tags=["Ingestion"])

# RBAC Dependencies
admin_only = RoleChecker(["admin"])
analyst_or_admin = RoleChecker(["analyst", "admin"])


@router.post("/process-contract", status_code=status.HTTP_201_CREATED, summary="Process contract from extraction data", description="Takes extracted contract data (Supplier, Parts, Clauses) and maps it to the Neo4j Knowledge Graph.")
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

@router.post("/process-news", status_code=status.HTTP_201_CREATED, summary="Process news risk event", description="Queues a news risk event for ingestion into the Knowledge Graph via the Outbox pattern.")
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

@router.post("/upload-contract", status_code=status.HTTP_201_CREATED, summary="Upload and process PDF contract", description="Uploads a PDF, extracts text via vision/OCR, and triggers an asynchronous task to ingestion the contract into the graph.")
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

@router.get("/history", response_model=Dict[str, Any], dependencies=[Depends(analyst_or_admin)], summary="Get ingestion history", description="Retrieves a paginated list of document ingestion events for the currently logged-in user.")
async def get_ingestion_history(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: TokenData = Depends(get_current_user),
    db_sql: AsyncSession = Depends(get_db)
):
    """Retrieves history of uploaded documents for the current user with pagination."""
    user_res = await db_sql.execute(select(DBUser).filter(DBUser.username == current_user.username))
    user = user_res.scalars().first()
    
    if not user:
        return {"items": [], "total": 0}
        
    # Get total count
    from sqlalchemy import func
    count_res = await db_sql.execute(select(func.count()).select_from(DocumentMetadata).filter(DocumentMetadata.user_id == user.id))
    total = count_res.scalar()

    # Get paginated records
    res = await db_sql.execute(
        select(DocumentMetadata)
        .filter(DocumentMetadata.user_id == user.id)
        .order_by(DocumentMetadata.id.desc())
        .limit(limit)
        .offset(offset)
    )
    docs = res.scalars().all()
    
    return {
        "items": [
            {
                "id": d.id,
                "filename": d.filename,
                "status": d.status,
                "created_at": d.created_at.isoformat() if d.created_at else None
            } for d in docs
        ],
        "total": total
    }

@router.get("/events", summary="Stream ingestion events", description="Server-Sent Events (SSE) endpoint to receive real-time notifications about ongoing ingestion tasks.")
async def ingestion_events(
    request: Request,
    current_user: TokenData = Depends(analyst_or_admin),
    db_sql: AsyncSession = Depends(get_db)
):
    """
    SSE endpoint to stream ingestion status updates.
    """
    # Fetch user ID for the channel name
    user_res = await db_sql.execute(select(DBUser).filter(DBUser.username == current_user.username))
    user = user_res.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    async def event_generator():
        redis_client = redis.from_url(settings.redis_url)
        pubsub = redis_client.pubsub()
        channel = f"ingestion_updates:{user.id}"
        await pubsub.subscribe(channel)
        
        try:
            # Yield initial connection event
            yield {
                "event": "connected",
                "data": json.dumps({"message": "Connected to ingestion updates"})
            }

            while True:
                if await request.is_disconnected():
                    break
                
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    yield {
                        "event": "update",
                        "data": message["data"].decode("utf-8")
                    }
                await asyncio.sleep(0.1) # Small sleep to prevent CPU spinning
        finally:
            await pubsub.unsubscribe(channel)
            await redis_client.close()

    async def sse_wrapper():
        async for event in event_generator():
            yield f"event: {event['event']}\ndata: {event['data']}\n\n"

    return StreamingResponse(sse_wrapper(), media_type="text/event-stream")

@router.post("/analyze-raw-text", status_code=status.HTTP_200_OK, summary="Analyze tagged raw text", description="Analyzes raw text input containing [TYPE: ...] tags to automatically route to contract or news extraction logic.")
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

@router.post("/erp-bom", status_code=status.HTTP_201_CREATED, summary="Import ERP Bill of Materials", description="Imports structured BOM data from ERP systems to build the N-Tier supply chain relationships in the Knowledge Graph.")
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
