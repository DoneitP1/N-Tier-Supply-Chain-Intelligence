import os
import shutil
from typing import List
from core.database import db, logger
from models.schemas import ContractData, NewsRiskData, TokenData
from models.pg_models import AuditLog, DocumentMetadata, User as DBUser
from services.entity_resolution import resolve_supplier_name
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from core.telemetry import track_llm_performance
import pypdf

async def process_pdf_and_extract(file_path: str) -> str:
    """Uses pypdf for local extraction before sending to LLM."""
    text = ""
    try:
        reader = pypdf.PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise ValueError(f"Could not read PDF: {e}")

@track_llm_performance(provider="Gemini/Anthropic", task_type="ContractExtraction")
async def extract_contract_via_llm(contract_text: str):
    # This function's implementation would typically involve calling an LLM
    # to extract structured data from the contract_text.
    # For now, we'll leave it as a placeholder.
    raise NotImplementedError("LLM extraction logic not yet implemented.")

async def process_contract(
    contract: ContractData, 
    current_user: TokenData,
    db_sql: AsyncSession
):
    # Entity Resolution: Resolve supplier name against existing graph nodes
    resolved_name = await resolve_supplier_name(contract.supplier.name)
    contract.supplier.name = resolved_name

    # Instead of direct Neo4j update, push to Outbox
    from core.outbox import push_to_outbox
    
    outbox_params = {
        "supplier_name": contract.supplier.name,
        "location": contract.supplier.location,
        "parts": [p.model_dump() for p in contract.parts],
        "username": current_user.username
    }
    
    await push_to_outbox(db_sql, "sync_contract", outbox_params)
    
    # Audit Log in PostgreSQL
    user_res = await db_sql.execute(select(DBUser).filter(DBUser.username == current_user.username))
    user = user_res.scalars().first()
    if user:
        import json
        audit = AuditLog(
            user_id=user.id, 
            action="ingest_contract", 
            target_node=contract.supplier.name,
            new_value=json.dumps(contract.model_dump())
        )
        db_sql.add(audit)
    
    # Commit both Outbox and Audit Log in a single transaction
    await db_sql.commit()
    
    return {"message": f"Contract for {contract.supplier.name} queued for Knowledge Graph sync"}
