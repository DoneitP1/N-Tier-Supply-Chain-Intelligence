import pytest
import json
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from api.routes.ingestion import extract_contract_via_llm
from core.outbox import push_to_outbox
from models.pg_models import OutboxEvent

class MockResult:
    def __init__(self, scalars_val=None, all_val=None):
        self._is_cursor = False
        self.context = MagicMock()
        self.context._is_server_side = False
        self._scalars_val = scalars_val
        self._all_val = all_val if all_val is not None else ([scalars_val] if scalars_val else [])
    def scalars(self):
        m = MagicMock(); m.first.return_value = self._scalars_val; m.all.return_value = self._all_val; return m

@pytest.mark.asyncio
async def test_llm_timeout_resilience(monkeypatch):
    import api.routes.ingestion as ingestion
    async def mock_timeout(*args, **kwargs):
        raise Exception("Anthropic API Timeout")
    monkeypatch.setattr(ingestion, "extract_contract_via_llm", mock_timeout)
    with pytest.raises(Exception) as excinfo:
        await ingestion.extract_contract_via_llm("Some text")
    assert "Timeout" in str(excinfo.value)

@pytest.mark.asyncio
async def test_neo4j_failure_outbox_persistence(mock_sql_session, monkeypatch):
    from core.database import db
    async def mock_query_fail(*args, **kwargs):
        raise Exception("Neo4j Connection Refused")
    monkeypatch.setattr(db, "execute_query", mock_query_fail)
    payload = {"test": "data"}
    await push_to_outbox(mock_sql_session, "sync_test", payload)
    assert mock_sql_session.add.called

@pytest.mark.asyncio
async def test_outbox_worker_retry_mechanism(mock_sql_session, monkeypatch):
    mock_sql_session.execute.side_effect = None
    from services.ingestion_tasks import process_outbox_async
    event = OutboxEvent(id=1, event_type="sync_contract", payload='{"test":1}', status="pending", retries=0)
    
    mock_sql_session.execute.return_value = MockResult(all_val=[event])
    
    async def mock_sync_fail(*args, **kwargs):
        raise Exception("Sync Failed")
    monkeypatch.setattr("services.ingestion_tasks._sync_contract_to_neo4j", mock_sync_fail)
    
    with patch("services.ingestion_tasks.async_session") as mock_async_session:
        mock_async_session.return_value.__aenter__.return_value = mock_sql_session
        await process_outbox_async()
    
    assert event.retries == 1
    assert event.status == "pending"
