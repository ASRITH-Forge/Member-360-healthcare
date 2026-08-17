"""
AI Service, Deterministic Open Issue Rules, and Source Traceability Tests
"""
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.member_service import search_members
from app.services.aggregation_service import detect_deterministic_open_issues
from app.services.ai_service import validate_and_fetch_source_record

client = TestClient(app)

def get_authenticated_client():
    """Helper to return an authenticated TestClient instance."""
    auth_client = TestClient(app)
    admin_user = os.getenv("ADMIN_USERNAME", "admin")
    admin_pass = os.getenv("ADMIN_PASSWORD", "admin@health360")
    login_res = auth_client.post("/login", data={"username": admin_user, "password": admin_pass}, follow_redirects=False)
    assert login_res.status_code == 303
    return auth_client

def test_deterministic_issue_rules():
    # Test pending auth detection
    auths = [{"authorization_id": "AUTH-TEST1", "service": "Cardiac MRI", "status": "Pending"}]
    issues = detect_deterministic_open_issues(
        eligibility=[{"status": "Active"}],
        claims=[],
        care_gaps=[],
        authorizations=auths,
        interactions=[]
    )
    assert len(issues) == 1
    assert issues[0]["issue_type"] == "Pending Authorization"
    assert issues[0]["source_id"] == "AUTH-TEST1"

    # Test open care gap detection
    gaps = [{"gap_id": "GAP-TEST1", "gap_type": "Preventive Care", "description": "Wellness visit missing", "status": "Open"}]
    issues_gap = detect_deterministic_open_issues(
        eligibility=[{"status": "Active"}],
        claims=[],
        care_gaps=gaps,
        authorizations=[],
        interactions=[]
    )
    assert len(issues_gap) == 1
    assert issues_gap[0]["issue_type"] == "Open Care Gap"
    assert issues_gap[0]["source_id"] == "GAP-TEST1"

def test_unauthenticated_ai_endpoints_return_401():
    response_summary = client.post("/api/ai/member/M00001/summary")
    assert response_summary.status_code == 401
    
    response_source = client.get("/api/ai/source/authorization/AUTH10455")
    assert response_source.status_code == 401

def test_authenticated_ai_summary_endpoint():
    auth_client = get_authenticated_client()
    all_members = search_members(limit=1)
    target_id = all_members[0]["member_id"]

    response = auth_client.post(f"/api/ai/member/{target_id}/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["member_id"] == target_id
    assert "key_facts" in data
    assert "open_issues" in data
    assert "next_actions" in data
    assert "sources" in data
    assert "disclaimer" in data

def test_authenticated_source_traceability_endpoint_valid():
    auth_client = get_authenticated_client()
    # Find a real authorization in the database
    from app.database.mongodb import get_collection
    auth_doc = get_collection("authorizations").find_one()
    assert auth_doc is not None
    auth_id = auth_doc["authorization_id"]

    response = auth_client.get(f"/api/ai/source/authorization/{auth_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["source_id"] == auth_id
    assert data["is_verified"] is True
    assert "record" in data

def test_authenticated_source_traceability_endpoint_invalid_404():
    auth_client = get_authenticated_client()
    response = auth_client.get("/api/ai/source/authorization/FAKE_AUTH_999999")
    assert response.status_code == 404
