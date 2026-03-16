import json
import logging
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from models.pg_models import OutboxEvent
from sqlalchemy import select
from datetime import datetime

logger = logging.getLogger("ntier_outbox")

async def push_to_outbox(db_sql: AsyncSession, event_type: str, payload: Dict[str, Any]):
    """
    Saves an event to the outbox table within the current transaction.
    """
    event = OutboxEvent(
        event_type=event_type,
        payload=json.dumps(payload),
        status="pending"
    )
    db_sql.add(event)
    logger.info(f"Pushed {event_type} to outbox.")

# The worker task itself usually goes into a tasks file, 
# but we define the processing logic here or in ingestion_tasks.py.
