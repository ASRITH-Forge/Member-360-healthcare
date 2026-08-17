"""
API, Authentication, and Member 360 Aggregation Tests
"""
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.member_service import search_members, get_member_by_id
from app.services.aggregation_service import get_member_360_profile

client = TestClient(app)

def get_authenticated_client():
    """Helper to return an authenticated TestClient instance."""
    auth_client = TestClient(app)
    admin_user = os.getenv("ADMIN_USERNAME", "admin")
    admin_pass = os.getenv("ADMIN_PASSWORD", "admin@health360")
    login_res = auth_client.post("/login", data={"username": admin_user, "password": admin_pass}, follow_redirects=False)
    assert login_res.status_code == 303
    return auth_client

def test_health_endpoint_public():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data

def test_login_page_public():
    response = client.get("/login")
    assert response.status_code == 200
    assert "Sign In" in response.text

def test_unauthenticated_web_routes_redirect_to_login():
    for path in ["/", "/search", "/member/M00001"]:
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/login"

def test_unauthenticated_api_routes_return_401():
    for path in ["/api/members", "/api/member/M00001"]:
        response = client.get(path)
        assert response.status_code == 401
        data = response.json()
        assert data.get("detail", {}).get("success") is False

def test_failed_login():
    response = client.post("/login", data={"username": "admin", "password": "WRONG_PASSWORD"})
    assert response.status_code == 401
    assert "Invalid administrator credentials" in response.text

def test_successful_login_and_logout():
    auth_client = TestClient(app)
    admin_user = os.getenv("ADMIN_USERNAME", "admin")
    admin_pass = os.getenv("ADMIN_PASSWORD", "admin@health360")
    
    # 1. Login
    res = auth_client.post("/login", data={"username": admin_user, "password": admin_pass}, follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == "/"

    # 2. Access dashboard authenticated
    res_dash = auth_client.get("/")
    assert res_dash.status_code == 200
    assert "Operations Dashboard" in res_dash.text

    # 3. Logout
    res_logout = auth_client.post("/logout", follow_redirects=False)
    assert res_logout.status_code == 303
    assert res_logout.headers["location"] == "/login"

    # 4. Attempt to access dashboard again -> should redirect to login
    res_dash_after = auth_client.get("/", follow_redirects=False)
    assert res_dash_after.status_code == 303
    assert res_dash_after.headers["location"] == "/login"

def test_authenticated_list_members_api():
    auth_client = get_authenticated_client()
    response = auth_client.get("/api/members?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["members"]) <= 5
    assert data["total"] > 0

def test_authenticated_search_members_filter():
    auth_client = get_authenticated_client()
    all_members = search_members(limit=1)
    assert len(all_members) > 0
    first_member = all_members[0]
    
    response = auth_client.get(f"/api/members?q={first_member['first_name']}")
    assert response.status_code == 200
    data = response.json()
    assert any(m["member_id"] == first_member["member_id"] for m in data["members"])

def test_authenticated_get_valid_member_360():
    auth_client = get_authenticated_client()
    all_members = search_members(limit=1)
    target_id = all_members[0]["member_id"]

    response = auth_client.get(f"/api/member/{target_id}")
    assert response.status_code == 200
    data = response.json()
    
    # Verify core 360 structure
    assert "member" in data
    assert data["member"]["member_id"] == target_id
    assert "eligibility" in data
    assert "claims" in data
    assert "medications" in data
    assert "care_gaps" in data
    assert "authorizations" in data
    assert "interactions" in data
    assert "deterministic_open_issues" in data
    assert "stats" in data

def test_authenticated_get_invalid_member_404():
    auth_client = get_authenticated_client()
    response = auth_client.get("/api/member/NON_EXISTENT_UUID_99999")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
