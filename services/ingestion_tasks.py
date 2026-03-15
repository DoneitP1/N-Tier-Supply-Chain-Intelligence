import os
import asyncio
from core.celery_app import celery_app
from core.database import db, logger
from core.postgres import async_session
from models.pg_models import AuditLog, DocumentMetadata, User as DBUser
from services.news_monitor import extract_news_risk_via_llm
from services.ingestion_core import process_pdf_and_extract, process_contract
from sqlalchemy.future import select

@celery_app.task(name="services.ingestion_tasks.process_document_task")
def process_document_task(file_path: str, filename: str, user_id: int):
    """
    Celery task to process uploaded PDFs asynchronously.
    """
    return asyncio.run(process_document_async(file_path, filename, user_id))

async def process_document_async(file_path: str, filename: str, user_id: int):
    async with async_session() as db_sql:
        doc_meta = None
        try:
            # Get the existing metadata record created by the API
            res = await db_sql.execute(select(DocumentMetadata).filter(
                DocumentMetadata.filename == filename,
                DocumentMetadata.user_id == user_id,
                DocumentMetadata.status == "pending"
            ).order_by(DocumentMetadata.id.desc()))
            doc_meta = res.scalars().first()

            # Process PDF
            contract_text = await process_pdf_and_extract(file_path)
            
            # Note: We need extract_contract_via_llm here
            from api.routes.ingestion import extract_contract_via_llm
            extracted_data = await extract_contract_via_llm(contract_text)
            
            # Use TokenData dummy for process_contract
            from models.schemas import TokenData
            # Fetch username for Neo4j tracking
            user_res = await db_sql.execute(select(DBUser).filter(DBUser.id == user_id))
            user_obj = user_res.scalars().first()
            current_user = TokenData(username=user_obj.username, role=user_obj.role)

            await process_contract(extracted_data, current_user, db_sql)

            if doc_meta:
                doc_meta.status = "processed"
                await db_sql.commit()
            
            logger.info(f"Successfully processed document: {filename}")

        except Exception as e:
            logger.error(f"Failed to process document {filename} in worker: {e}", exc_info=True)
            if doc_meta:
                doc_meta.status = "failed"
                await db_sql.commit()
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
