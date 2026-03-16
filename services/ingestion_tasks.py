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

            # Refactored: process_contract now uses push_to_outbox internally
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

@celery_app.task(name="services.ingestion_tasks.process_outbox_task")
def process_outbox_task():
    """
    Background task to process pending outbox events.
    """
    return asyncio.run(process_outbox_async())

async def process_outbox_async():
    from models.pg_models import OutboxEvent
    import json
    from datetime import datetime
    
    async with async_session() as db_sql:
        res = await db_sql.execute(select(OutboxEvent).filter(OutboxEvent.status == "pending").limit(50))
        events = res.scalars().all()
        
        for event in events:
            try:
                payload = json.loads(event.payload)
                if event.event_type == "sync_contract":
                    await _sync_contract_to_neo4j(payload)
                elif event.event_type == "sync_news":
                    await _sync_news_to_neo4j(payload)
                elif event.event_type == "sync_erp_bom":
                    # For complex ERP BOM, we can use the existing service logic
                    from services.erp_integration import db as neo4j_db
                    # (Implementation of query inside _sync_erp_bom_to_neo4j)
                    await _sync_erp_bom_to_neo4j(payload)
                
                event.status = "processed"
                event.processed_at = datetime.now()
            except Exception as e:
                logger.error(f"Failed to process outbox event {event.id}: {e}")
                event.retries += 1
                if event.retries > 5:
                    event.status = "failed"
            await db_sql.commit()

async def _sync_contract_to_neo4j(params: dict):
    query = """
    MERGE (s:Supplier {name: $supplier_name})
    SET s.location = $location
    WITH s
    UNWIND $parts as p_data
    MERGE (p:Part {part_code: p_data.part_code})
    MERGE (s)-[r:SUPPLIES]->(p)
    MERGE (u:User {username: $username})
    MERGE (s)-[:CREATED_BY]->(u)
    MERGE (p)-[:CREATED_BY]->(u)
    """
    await db.execute_query(query, params)

async def _sync_news_to_neo4j(params: dict):
    query = """
    MERGE (r:RiskEvent {type: $event_type})
    SET r.severity = $severity, r.summary = $summary
    WITH r
    UNWIND $impacted_entities as entity_name
    MERGE (ent:Supplier {name: entity_name})
    MERGE (ent)-[:IS_AFFECTED_BY]->(r)
    MERGE (usr:User {username: $username})
    MERGE (r)-[:CREATED_BY]->(usr)
    """
    await db.execute_query(query, params)

async def _sync_erp_bom_to_neo4j(params: dict):
    # This query matches the one in erp_integration.py
    cypher_query = """
    MERGE (u:User {username: $username})
    MERGE (f:Factory {name: $factory_name})
    ON CREATE SET f.last_updated = timestamp(), f.data_source = $source
    ON MATCH SET f.last_updated = timestamp()
    MERGE (f)-[:CREATED_BY]->(u)
    MERGE (p:Part {code: $part_code})
    ON CREATE SET p.last_updated = timestamp()
    ON MATCH SET p.last_updated = timestamp()
    MERGE (p)-[:CREATED_BY]->(u)
    MERGE (t1:Supplier {name: $t1_name})
    ON CREATE SET t1.location = $t1_location, t1.tier = 1, t1.last_updated = timestamp(), t1.data_source = $source
    ON MATCH SET t1.location = coalesce($t1_location, t1.location), t1.last_updated = timestamp()
    MERGE (t1)-[:CREATED_BY]->(u)
    MERGE (f)-[con:CONSUMES]->(p)
    ON CREATE SET con.daily_consumption = $daily_consumption, con.last_updated = timestamp()
    ON MATCH SET con.daily_consumption = coalesce($daily_consumption, con.daily_consumption), con.last_updated = timestamp()
    MERGE (t1)-[:SUPPLIES]->(p)
    FOREACH (ignoreMe IN CASE WHEN $t2_name IS NOT NULL THEN [1] ELSE [] END |
        MERGE (t2:Supplier {name: $t2_name})
        ON CREATE SET t2.location = coalesce($t2_location, t2.location), t2.tier = 2, t2.last_updated = timestamp(), t2.data_source = $source
        ON MATCH SET t2.location = coalesce($t2_location, t2.location), t2.last_updated = timestamp()
        MERGE (t2)-[:CREATED_BY]->(u)
        MERGE (t2)-[rel:SUPPLIES_MATERIAL]->(t1)
        ON CREATE SET rel.material = $t2_material, rel.last_updated = timestamp()
        ON MATCH SET rel.material = coalesce($t2_material, rel.material), rel.last_updated = timestamp()
    )
    """
    await db.execute_query(cypher_query, params)
