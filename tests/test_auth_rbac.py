import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def rbac_client(client):
    # Register "rbacuser"
    client.post("/api/auth/register", json={
        "username": "rbacuser",
        "password": "rbacpassword",
        "role": "analyst"
    })
    # Login
    client.post("/api/auth/token", data={
        "username": "rbacuser",
        "password": "rbacpassword"
    })
    return client

def test_auth_flow(client):
    """
    Test the full authentication flow including Refresh Tokens.
    """
    # 1. Register
    reg_resp = client.post("/api/auth/register", json={
        "username": "flowuser",
        "password": "flowpassword",
        "role": "analyst"
    })
    assert reg_resp.status_code == 201
    
    # 2. Login
    login_resp = client.post("/api/auth/token", data={
        "username": "flowuser",
        "password": "flowpassword"
    })
    assert login_resp.status_code == 200
    assert client.cookies.get("access_token") is not None
    
    # 3. Access /me
    me_resp = client.get("/api/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "flowuser"
    
    # 4. Refresh Token
    # Temporarily remove access token to prove refresh works
    client.cookies.delete("access_token")
    refresh_resp = client.post("/api/auth/refresh")
    assert refresh_resp.status_code == 200
    assert client.cookies.get("access_token") is not None
    
    # 5. Logout
    logout_resp = client.post("/api/auth/logout")
    assert logout_resp.status_code == 200
    assert client.cookies.get("access_token") is None

def test_register_invalid_role(client):
    """
    Test that registering with an invalid role returns 422 Unprocessable Entity.
    """
    resp = client.post("/api/auth/register", json={
        "username": "invaliduser",
        "password": "invalidpassword",
        "role": "hacker" # Invalid role
    })
    assert resp.status_code == 422
