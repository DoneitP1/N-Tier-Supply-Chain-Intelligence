import pytest
from core.config import settings

# Integration tests using the HTTP TestClient (FastAPI)
# Mocks from conftest.py apply automatically

import pytest
from core.config import settings

# Integration tests using the HTTP TestClient (FastAPI)
# Mocks from conftest.py apply automatically

@pytest.fixture
def admin_token(client):
    # Register an admin
    client.post("/api/auth/register", json={
        "username": "testadmin",
        "password": "testpassword",
        "role": "admin"
    })
    # Login to get token
    response = client.post("/api/auth/token", data={
        "username": "testadmin",
        "password": "testpassword"
    })
    return response.json()["access_token"]

@pytest.fixture
def analyst_token(client):
    # Register an analyst
    client.post("/api/auth/register", json={
        "username": "testanalyst",
        "password": "testpassword",
        "role": "analyst"
    })
    # Login to get token
    response = client.post("/api/auth/token", data={
        "username": "testanalyst",
        "password": "testpassword"
    })
    return response.json()["access_token"]

def test_missing_token(client):
    response = client.get("/api/graph/data")
    assert response.status_code == 401 # Fastapi security returns 401 for missing token usually

def test_get_graph_data_analyst(client, analyst_token):
    headers = {"Authorization": f"Bearer {analyst_token}"}
    response = client.get("/api/graph/data?limit=10", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data

def test_admin_only_access_denied_for_analyst(client, analyst_token):
    headers = {"Authorization": f"Bearer {analyst_token}"}
    payload = {"text": "[TYPE: CONTRACT_PDF] Admin only action."}
    response = client.post("/api/ingest/analyze-raw-text", json=payload, headers=headers)
    assert response.status_code == 403
    assert "not have enough permissions" in response.json()["detail"]

def test_admin_access_allowed(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {"text": "[TYPE: CONTRACT_PDF] This is a mock contract for Test Supplier."}
    response = client.post("/api/ingest/analyze-raw-text", json=payload, headers=headers)
    assert response.status_code == 200 or response.status_code == 201

def test_get_nodes_analyst(client, analyst_token):
    headers = {"Authorization": f"Bearer {analyst_token}"}
    # Test without label
    response = client.get("/api/graph/nodes", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    
    # Test with label
    response = client.get("/api/graph/nodes?label=Supplier", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_risk_simulation_analyst(client, analyst_token):
    headers = {"Authorization": f"Bearer {analyst_token}"}
    payload = {
        "supplier_name": "Test Supplier",
        "duration_days": 30,
        "severity": "medium"
    }
    # Note: This might return 404 if the mock DB doesn't have "Test Supplier"
    # But conftest typically mocks the execute_query to return something.
    response = client.post("/api/risk/simulate", json=payload, headers=headers)
    
    # We expect 200 (if found) or 404 (if not found in graph)
    # The important part is that the request schema validation passes.
    assert response.status_code in [200, 404]
    
    if response.status_code == 200:
        data = response.json()
        assert "cascading_impact_depth" in data
        assert "impacted_factories" in data
        assert "total_impacted_nodes" in data
        assert "bottlenecks" in data
        assert "weakest_links" in data

def test_auth_me_analyst(client, analyst_token):
    headers = {"Authorization": f"Bearer {analyst_token}"}
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testanalyst"
    assert data["role"] == "analyst"

def test_auth_me_admin(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testadmin"
    assert data["role"] == "admin"
