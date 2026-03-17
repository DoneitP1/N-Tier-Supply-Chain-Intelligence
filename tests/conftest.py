import pytest
import sys
from unittest.mock import MagicMock, AsyncMock

# 1. Prevent missing dependencies
sys.modules["asyncpg"] = MagicMock()
sys.modules["prometheus_client"] = MagicMock()
sys.modules["prometheus_fastapi_instrumentator"] = MagicMock()

# 2. Mock early
import sqlalchemy.ext.asyncio
sqlalchemy.ext.asyncio.create_async_engine = MagicMock()

# Global mock for password verification
import core.security
core.security.verify_password = lambda p, h: True

# Disable rate limit
from core.config import settings
settings.rate_limit_enabled = False

# 3. Import app
from main import app
from core.database import db
from core.postgres import get_db, engine, Base
from models.pg_models import User as DBUser, OutboxEvent, AuditLog
from fastapi.testclient import TestClient

# Mock Celery
import core.celery_app
core.celery_app.celery_app.conf.task_always_eager = True
core.celery_app.celery_app.conf.task_eager_propagates = True

class MockResult:
    def __init__(self, scalars_val=None, all_val=None):
        self._is_cursor = False
        self.context = MagicMock()
        self.context._is_server_side = False
        self._scalars_val = scalars_val
        self._all_val = all_val if all_val is not None else ([scalars_val] if scalars_val else [])
    def scalars(self):
        m = MagicMock()
        m.first.return_value = self._scalars_val
        m.all.return_value = self._all_val
        return m

@pytest.fixture
def client(mock_sql_session):
    async def mock_get_db():
        yield mock_sql_session
    app.dependency_overrides[get_db] = mock_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def mock_sql_session():
    mock_session = MagicMock()
    mock_session.add = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.delete = AsyncMock()
    mock_session.close = AsyncMock()
    
    mock_session.begin = MagicMock()
    mock_session.begin.return_value.__aenter__ = AsyncMock()
    mock_session.begin.return_value.__aexit__ = AsyncMock()
    
    # State to track what has been "registered" in this session
    session_state = {"registered": set()}
    
    default_users = {
        "testanalyst": DBUser(id=1, username="testanalyst", hashed_password="h", role="analyst"),
        "testadmin": DBUser(id=2, username="testadmin", hashed_password="h", role="admin"),
        "testuser": DBUser(id=3, username="testuser", hashed_password="h", role="admin")
    }

    async def mock_execute_impl(query_obj, *args, **kwargs):
        q_str = str(query_obj).lower()
        params = {}
        try: params = query_obj.compile().params
        except: pass
        if args and isinstance(args[0], dict): params.update(args[0])
        params.update(kwargs)
        
        if "users" in q_str:
            username = params.get("username_1") or params.get("username")
            # For debugging
            # print(f"DEBUG: user_query username={username} registered={session_state['registered']}")
            
            if not username: return MockResult(None)
            
            # If it's a known default user, return it
            bit = default_users.get(username)
            if bit: return MockResult(bit)
            
            # For registration/login flow tests
            # If we see it for the first time, return None (NOT registered)
            if username not in session_state["registered"]:
                 # If this query looks like a fetch (not just existence check),
                 # OR if we want to BE REALISTIC, we should only mark as registered on COMMIT.
                 # But since we don't track commit, we mark on first "exists?" check.
                 session_state["registered"].add(username)
                 return MockResult(None)
            else:
                 # It's registered, so return the user for login
                 return MockResult(DBUser(id=99, username=username, hashed_password="h", role="analyst"))

        elif "outbox" in q_str:
            event = OutboxEvent(id=77, event_type="sync_contract", payload='{"test":1}', status="pending", retries=0)
            return MockResult(event)
        return MockResult(None)

    mock_session.execute.side_effect = mock_execute_impl
    return mock_session

@pytest.fixture(autouse=True)
def mock_db_connection(monkeypatch):
    mock_db = MagicMock()
    mock_db.execute_query = AsyncMock(return_value=[])
    async def side_effect(query, parameters=None):
        if "LIMIT" in query:
            return [{"n_id": 1, "n_label": "Supplier", "n_name": "MockSupplier", "m_id": 2, "m_label": "Part", "m_name": "P-123", "r_type": "SUPPLIES"}]
        elif "count(s) as impacted_suppliers" in query:
            return [{"impacted_suppliers": 1}]
        return []
    mock_db.execute_query.side_effect = side_effect
    mock_db.close = AsyncMock()
    monkeypatch.setattr("core.database.db", mock_db)
    
    # Patch in all routes and services that might have imported 'db' already
    modules_to_patch = [
        "api.routes.stats", "api.routes.graph", "api.routes.ingestion", 
        "api.routes.risk", "services.risk_engine", "services.ingestion_core",
        "services.news_monitor", "services.entity_resolution",
        "core.security" # Just in case
    ]
    for mod_name in modules_to_patch:
        if mod_name in sys.modules:
            mod = sys.modules[mod_name]
            if hasattr(mod, "db"):
                monkeypatch.setattr(f"{mod_name}.db", mock_db)
    
    return mock_db

class MockLLMChain:
    async def ainvoke(self, inputs):
        from models.schemas import ContractData, SupplierInfo, PartInfo, ClauseInfo, NewsRiskData, EventClassification, ImpactDetails
        raw_text = inputs.get("raw_text", "")
        if "CONTRACT" in raw_text or "supplier" in raw_text.lower():
            return ContractData(
                supplier=SupplierInfo(name="Test Supplier", location="Test City", confidence_score=0.9),
                parts=[PartInfo(part_code="TEST-01", confidence_score=0.9)],
                clauses=ClauseInfo(force_majeure_present=True, alternative_supplier_allowed=False, confidence_score=0.9),
                overall_extraction_confidence=0.95
            )
        else:
            return NewsRiskData(
                event_classification=EventClassification(is_supply_chain_risk=True, event_type="Test Event", severity="High", confidence_score=0.9),
                impact_details=ImpactDetails(locations_affected=["Test City"], entities_affected=["Test Supplier"], confidence_score=0.9),
                summary="A test risk event.",
                overall_assessment_confidence=0.9
            )

@pytest.fixture(autouse=True)
def mock_llm_chains(monkeypatch):
    async def mock_extract_contract(*args, **kwargs):
        return await MockLLMChain().ainvoke({"raw_text": "CONTRACT"})
    async def mock_extract_news(*args, **kwargs):
        return await MockLLMChain().ainvoke({"raw_text": "NEWS"})
    monkeypatch.setattr("api.routes.ingestion.extract_contract_via_llm", mock_extract_contract)
    monkeypatch.setattr("api.routes.ingestion.extract_news_risk_via_llm", mock_extract_news)
    monkeypatch.setattr("services.ingestion_tasks.extract_news_risk_via_llm", mock_extract_news)
    monkeypatch.setattr("services.news_monitor.extract_news_risk_via_llm", mock_extract_news)

@pytest.fixture
def golden_contract():
    import os, json
    path = os.path.join(os.path.dirname(__file__), "data", "golden_contract.json")
    if os.path.exists(path):
        with open(path, "r") as f: return json.load(f)
    return {}
