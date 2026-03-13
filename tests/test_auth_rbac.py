import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from unittest.mock import AsyncMock, patch
import json
from core.database import db

@pytest.fixture(scope="module")
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.fixture(scope="module", autouse=True)
async def mock_db_global():
    # Patch the singleton db instance's execute_query method globally in core.database
    with patch("core.database.db.execute_query", new_callable=AsyncMock) as mock_query:
        
        # Store users in a local dict for mocking
        test_users = {}

        async def side_effect(query, params=None):
            # Normalizing query and params
            q = query.strip()
            p = params or {}
            
            if "CREATE (u:User" in q:
                test_users[p["username"]] = p
                return [p]
            if "MATCH (u:User" in q:
                user = test_users.get(p.get("username"))
                return [user] if user else []
            return []

        mock_query.side_effect = side_effect
        yield

@pytest.mark.asyncio
async def test_auth_flow(client):
    # 1. Register Admin
    reg_response = await client.post("/api/auth/register", json={
        "username": "test_admin",
        "password": "testpassword",
        "role": "admin"
    })
    assert reg_response.status_code == 201
    assert reg_response.json()["username"] == "test_admin"

    # 2. Register Analyst
    reg_response = await client.post("/api/auth/register", json={
        "username": "test_analyst",
        "password": "testpassword",
        "role": "analyst"
    })
    assert reg_response.status_code == 201

    # 3. Login Admin
    login_response = await client.post("/api/auth/token", data={
        "username": "test_admin",
        "password": "testpassword"
    })
    assert login_response.status_code == 200
    admin_token = login_response.json()["access_token"]

    # 4. Login Analyst
    login_response = await client.post("/api/auth/token", data={
        "username": "test_analyst",
        "password": "testpassword"
    })
    assert login_response.status_code == 200
    analyst_token = login_response.json()["access_token"]

    # 5. Test Access: Analyst accessing Health (Allowed)
    health_response = await client.get("/api/health")
    assert health_response.status_code == 200

    # 6. Test Access: Analyst accessing Protected Graph (Allowed)
    graph_response = await client.get("/api/graph/data", headers={"Authorization": f"Bearer {analyst_token}"})
    assert graph_response.status_code == 200

    # 7. Test Access: Analyst accessing Admin Ingest (Forbidden)
    ingest_response = await client.post("/api/ingest/process-contract", 
        json={"supplier": {"name": "Test", "location": "Test", "confidence_score": 1.0}, "parts": [], "clauses": {"force_majeure_present": False, "alternative_supplier_allowed": False}, "overall_extraction_confidence": 1.0},
        headers={"Authorization": f"Bearer {analyst_token}"}
    )
    assert ingest_response.status_code == 403

    # 8. Test Access: Unauthorized access (401)
    unauth_response = await client.get("/api/graph/data")
    assert unauth_response.status_code == 401
