import pytest

@pytest.fixture
def auth_client(client):
    # Register and login to get cookies set in TestClient
    client.post("/api/auth/register", json={
        "username": "statsuser",
        "password": "statspassword",
        "role": "analyst"
    })
    client.post("/api/auth/token", data={
        "username": "statsuser",
        "password": "statspassword"
    })
    return client

def test_get_stats_authorized(auth_client):
    response = auth_client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_suppliers" in data
    assert "total_parts" in data
    assert "active_risks" in data # Note: matched original file keys

def test_get_stats_unauthorized(client):
    # Ensure no cookies
    client.cookies.clear()
    response = client.get("/api/stats")
    assert response.status_code == 401
