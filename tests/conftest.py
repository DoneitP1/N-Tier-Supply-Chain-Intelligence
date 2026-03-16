import pytest
import sys
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient

# 1. Prevent missing dependencies from being required during import
sys.modules["asyncpg"] = MagicMock()
sys.modules["prometheus_client"] = MagicMock()
sys.modules["prometheus_fastapi_instrumentator"] = MagicMock()

# 2. Mock the engine creation in core.postgres before main is imported
import sqlalchemy.ext.asyncio
sqlalchemy.ext.asyncio.create_async_engine = MagicMock()

# 3. Import app after mocking modules
from main import app
from core.database import db
from core.postgres import get_db, engine, Base
from models.pg_models import User as DBUser
from sqlalchemy.ext.asyncio import AsyncSession

# Mock Celery to run always eager (synchronous) during tests
import core.celery_app
core.celery_app.celery_app.conf.task_always_eager = True
core.celery_app.celery_app.conf.task_eager_propagates = True

# Provide a standard TestClient fixture
@pytest.fixture
def client(mock_sql_session):
    # Override get_db dependency
    app.dependency_overrides[get_db] = lambda: mock_sql_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def mock_sql_session():
    mock_session = AsyncMock(spec=AsyncSession)
    
    # Mock result for User query in Auth (PostgreSQL query)
    from core.security import get_password_hash
    mock_user = MagicMock(spec=DBUser)
    mock_user.id = 1
    mock_user.username = "testuser"
    mock_user.hashed_password = get_password_hash("testpassword")
    
    def get_role_mock():
        # This is a bit tricky with MagicMock, let's just make it dynamic
        return "analyst" if "analyst" in mock_user.username else "admin"
    
    # We can use PropertyMock for more control
    def mock_execute_impl(query_obj, *args, **kwargs):
        # Extract username from parameters if available
        try:
            # SQLAlchemy 1.4/2.0+ params extraction
            params = query_obj.compile().params
            for val in params.values():
                if isinstance(val, str):
                    if val == "testanalyst":
                        mock_user.username = "testanalyst"
                    elif val == "testadmin":
                        mock_user.username = "testadmin"
        except:
            # Fallback to checking string representation for test literal cases
            q_str = str(query_obj).lower()
            if "testanalyst" in q_str:
                mock_user.username = "testanalyst"
            elif "testadmin" in q_str:
                mock_user.username = "testadmin"
        return mock_result

    mock_result = MagicMock()
    mock_result._is_cursor = False
    mock_result.context = MagicMock()
    mock_result.context._is_server_side = False
    mock_result.scalars.return_value.first.side_effect = lambda: mock_user
    mock_result.scalars.return_value.all.return_value = [mock_user]
    mock_session.execute.side_effect = mock_execute_impl
    
    # To handle the role dynamically:
    type(mock_user).role = property(lambda self: "analyst" if "analyst" in self.username else "admin")
    
    return mock_session

# Mock the Neo4j Database Connection
class MockNeo4jConnection:
    async def execute_query(self, query, parameters=None):
        if "LIMIT" in query:
            return [{"n_id": 1, "n_label": "Supplier", "n_name": "MockSupplier", "m_id": 2, "m_label": "Part", "m_name": "P-123", "r_type": "SUPPLIES"}]
        elif "count(s) as impacted_suppliers" in query:
            return [{"impacted_suppliers": 1}]
        return []
        
    async def close(self):
        pass

@pytest.fixture(autouse=True)
def mock_db_connection(monkeypatch):
    mock_db = MockNeo4jConnection()
    monkeypatch.setattr("core.database.db", mock_db)
    monkeypatch.setattr("api.routes.ingestion.db", mock_db)
    monkeypatch.setattr("services.ingestion_core.db", mock_db)
    monkeypatch.setattr("services.news_monitor.db", mock_db)
    monkeypatch.setattr("api.routes.graph.db", mock_db)
    monkeypatch.setattr("api.routes.risk.db", mock_db)
    return mock_db

# Mock LLM calls
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
    import os
    import json
    path = os.path.join(os.path.dirname(__file__), "data", "golden_contract.json")
    with open(path, "r") as f:
        return json.load(f)
