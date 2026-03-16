import pytest

@pytest.fixture
def admin_token(client):
    # Register an admin
    client.post("/api/auth/register", json={
        "username": "statsadmin",
        "password": "testpassword",
        "role": "admin"
    })
    # Login to get token
    response = client.post("/api/auth/token", data={
        "username": "statsadmin",
        "password": "testpassword"
    })
    return response.json()["access_token"]

def test_get_stats_authorized(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get("/api/stats/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_suppliers" in data
    assert "total_parts" in data
    assert "active_risks" in data
    assert "supply_health" in data
    assert "trends" in data
    assert isinstance(data["total_suppliers"], int)
    assert isinstance(data["total_parts"], int)
    assert isinstance(data["active_risks"], int)
    assert isinstance(data["supply_health"], (int, float))

def test_get_stats_unauthorized(client):
    response = client.get("/api/stats/")
    assert response.status_code == 401
