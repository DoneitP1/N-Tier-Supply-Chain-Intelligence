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
