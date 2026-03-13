import pytest
from fastapi.testclient import TestClient
from main import app
from core.database import db

# Provide a standard TestClient fixture
@pytest.fixture
def client():
    # Setup - we could override dependencies here if needed (e.g. app.dependency_overrides)
    with TestClient(app) as test_client:
        yield test_client

# Mock the Neo4j Database Connection so tests don't hit the real DB
class MockNeo4jConnection:
    async def execute_query(self, query, parameters=None):
        # A mocked execute_query always returns some mock data
        # Check query content to route mock responses
        if "LIMIT" in query:
            return [{"n_id": 1, "n_label": "Supplier", "n_name": "MockSupplier", "m_id": 2, "m_label": "Part", "m_name": "P-123", "r_type": "SUPPLIES"}]
        elif "count(s) as impacted_suppliers" in query:
            return [{"impacted_suppliers": 1}]
        return []

@pytest.fixture(autouse=True)
def mock_db_connection(monkeypatch):
    """
    Automatically mock the global database connection across all tests.
    """
    mock_db = MockNeo4jConnection()
    monkeypatch.setattr("core.database.db", mock_db)
    # Also patch it in specific routers if they imported it directly
    monkeypatch.setattr("api.routes.ingestion.db", mock_db)
    monkeypatch.setattr("api.routes.graph.db", mock_db)
    monkeypatch.setattr("api.routes.risk.db", mock_db)
    return mock_db

# Mock LLM calls so we don't spend API tokens during tests
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
    # Mocking the actual LLM instance or the extract functions directly
    async def mock_extract_contract(*args, **kwargs):
        return await MockLLMChain().ainvoke({"raw_text": "CONTRACT"})
        
    async def mock_extract_news(*args, **kwargs):
        return await MockLLMChain().ainvoke({"raw_text": "NEWS"})
        
    monkeypatch.setattr("api.routes.ingestion.extract_contract_via_llm", mock_extract_contract)
    monkeypatch.setattr("api.routes.ingestion.extract_news_risk_via_llm", mock_extract_news)
