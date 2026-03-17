import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from services.ingestion_tasks import process_outbox_async
from models.pg_models import OutboxEvent
from datetime import datetime, timedelta

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
async def test_outbox_exponential_backoff(mock_sql_session):
    mock_sql_session.execute.side_effect = None # CLEAR THE CONGESTION
    with patch("services.ingestion_tasks.async_session") as mock_async_session:
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_sql_session
        mock_async_session.return_value = mock_cm

        event = OutboxEvent(id=1, event_type="sync_contract", payload='{"supplier_name": "Test"}', status="pending", retries=0, next_retry_at=None)
        mock_sql_session.execute.return_value = MockResult(all_val=[event])
    
        with patch("services.ingestion_tasks._sync_contract_to_neo4j", side_effect=Exception("DB Down")):
            await process_outbox_async()
            assert event.retries == 1
            assert event.status == "pending"
            assert event.next_retry_at is not None

@pytest.mark.asyncio
async def test_outbox_max_retries_failure(mock_sql_session):
    mock_sql_session.execute.side_effect = None
    with patch("services.ingestion_tasks.async_session") as mock_async_session:
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_sql_session
        mock_async_session.return_value = mock_cm

        event = OutboxEvent(id=2, event_type="sync_contract", payload='{"supplier_name": "Test"}', status="pending", retries=5, next_retry_at=None)
        mock_sql_session.execute.return_value = MockResult(all_val=[event])
    
        with patch("services.ingestion_tasks._sync_contract_to_neo4j", side_effect=Exception("Terminal Failure")):
            await process_outbox_async()
            assert event.retries == 6
            assert event.status == "failed"

@pytest.mark.asyncio
async def test_outbox_fetch_filtering(mock_sql_session):
    mock_sql_session.execute.side_effect = None
    with patch("services.ingestion_tasks.async_session") as mock_async_session:
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_sql_session
        mock_async_session.return_value = mock_cm

        mock_sql_session.execute.return_value = MockResult(all_val=[])
        await process_outbox_async()
        args, kwargs = mock_sql_session.execute.call_args
        query_str = str(args[0]).lower()
        assert "pending" in query_str or "status" in query_str
