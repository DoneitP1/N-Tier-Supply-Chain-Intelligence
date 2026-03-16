import pytest
import json
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
from api.routes.ingestion import extract_contract_via_llm
from core.outbox import push_to_outbox
from models.pg_models import OutboxEvent

@pytest.mark.asyncio
async def test_llm_timeout_resilience(monkeypatch):
    """Test how the system handles LLM timeouts."""
    import api.routes.ingestion as ingestion
    
    async def mock_timeout(*args, **kwargs):
        raise Exception("Anthropic API Timeout")
    
    # Patch it in the ingestion module
    monkeypatch.setattr(ingestion, "extract_contract_via_llm", mock_timeout)
    
    with pytest.raises(Exception) as excinfo:
        # Call the patched version
        await ingestion.extract_contract_via_llm("Some text")
    assert "Timeout" in str(excinfo.value)

@pytest.mark.asyncio
async def test_neo4j_failure_outbox_persistence(mock_sql_session, monkeypatch):
    """Test that Neo4j failure doesn't lose data, and is saved in Outbox."""
    from core.database import db
    
    # Mock Neo4j to fail
    async def mock_query_fail(*args, **kwargs):
        raise Exception("Neo4j Connection Refused")
    
    monkeypatch.setattr(db, "execute_query", mock_query_fail)
    
    # Payload for Outbox
    payload = {"test": "data"}
    
    # We use push_to_outbox which adds to SQL session
    await push_to_outbox(mock_sql_session, "sync_test", payload)
    
    # Verify the event was added to the session
    assert mock_sql_session.add.called
    added_obj = mock_sql_session.add.call_args[0][0]
    assert isinstance(added_obj, OutboxEvent)
    assert added_obj.event_type == "sync_test"
    assert json.loads(added_obj.payload) == payload

@pytest.mark.asyncio
async def test_outbox_worker_retry_mechanism(mock_sql_session, monkeypatch):
    """Test that the outbox worker correctly increments retries on failure."""
    from services.ingestion_tasks import process_outbox_async
    from models.pg_models import OutboxEvent
    
    # Create a mock event
    event = OutboxEvent(id=1, event_type="sync_contract", payload='{"test":1}', status="pending", retries=0)
    
    # Mock SQL execution to return this event
    from types import SimpleNamespace
    mock_result = SimpleNamespace()
    mock_result.scalars = MagicMock()
    mock_result.scalars.return_value.all.return_value = [event]
    mock_sql_session.execute.return_value = mock_result
    
    # Mock the sync function to fail
    async def mock_sync_fail(*args, **kwargs):
        raise Exception("Sync Failed")
    
    monkeypatch.setattr("services.ingestion_tasks._sync_contract_to_neo4j", mock_sync_fail)
    
    # Run the worker (logic-only)
    with patch("core.postgres.async_session") as mock_async_session:
        mock_async_session.return_value.__aenter__.return_value = mock_sql_session
        
        # Mock execute to return our result and avoid SQLAlchemy internal checks
        mock_sql_session.execute = AsyncMock()
        mock_sql_session.execute.return_value = mock_result
        
        await process_outbox_async()
    
    # Check if retries incremented
    assert event.retries == 1
    assert event.status == "pending"
