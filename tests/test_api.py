import pytest
from core.config import settings

# Integration tests using the HTTP TestClient (FastAPI)
# Mocks from conftest.py apply automatically

def test_missing_api_key(client):
    response = client.get("/api/graph/data")
    assert response.status_code == 403
    assert "Not authenticated" in response.json()["detail"] or "Not authenticated" == response.json()["detail"]

def test_wrong_api_key(client):
    headers = {"X-App-Api-Key": "wrong_key"}
    response = client.get("/api/graph/data", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API Key"

def test_get_graph_data(client):
    headers = {"X-App-Api-Key": settings.app_api_key}
    response = client.get("/api/graph/data?limit=10", headers=headers)
    
    # Assert successful resolution
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    
    # Assert our mock DB returned the nodes correctly
    if len(data["nodes"]) > 0:
        assert data["nodes"][0]["name"] == "MockSupplier"

def test_analyze_raw_contract_text(client):
    headers = {"X-App-Api-Key": settings.app_api_key}
    payload = {"text": "[TYPE: CONTRACT_PDF] This is a mock contract for Test Supplier."}
    
    # Our mock LLM will return a confident ContractData, which routes to DB
    # The DB will return success message without throwing an exception
    response = client.post("/api/ingest/analyze-raw-text", json=payload, headers=headers)
    assert response.status_code == 200 or response.status_code == 201
    assert "mapped to Knowledge Graph" in response.json().get("message", "")

def test_analyze_invalid_raw_text(client):
    headers = {"X-App-Api-Key": settings.app_api_key}
    payload = {"text": "Just some random text without the required tags."}
    
    response = client.post("/api/ingest/analyze-raw-text", json=payload, headers=headers)
    assert response.status_code == 400
    assert "Unknown input format" in response.json()["detail"]
