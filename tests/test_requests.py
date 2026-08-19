"""
Tests for Organization / Hospital Request Management
Covers API creation, validation, filtering, status updates, Member 360 profile integration,
source traceability, and AI context integration.
"""
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.member_service import search_members
from app.services.request_service import (
    create_organization_request,
    get_request_by_id,
    get_requests_by_member,
    search_requests
)
from app.services.aggregation_service import get_member_360_profile, detect_deterministic_open_issues

client = TestClient(app)

def get_authenticated_client():
    """Helper to return an authenticated TestClient instance."""
    auth_client = TestClient(app)
    admin_user = os.getenv("ADMIN_USERNAME", "admin")
    admin_pass = os.getenv("ADMIN_PASSWORD", "admin@health360")
    login_res = auth_client.post("/login", data={"username": admin_user, "password": admin_pass}, follow_redirects=False)
    assert login_res.status_code == 303
    return auth_client

def test_unauthenticated_requests_endpoints_security():
    # API endpoints return 401
    res_post = client.post("/api/requests", json={})
    assert res_post.status_code == 401

    res_get = client.get("/api/requests")
    assert res_get.status_code == 401

    res_single = client.get("/api/requests/REQ10001")
    assert res_single.status_code == 401

    res_patch = client.patch("/api/requests/REQ10001", json={"status": "Approved"})
    assert res_patch.status_code == 401

    # Web page redirects to /login
    res_web = client.get("/requests", follow_redirects=False)
    assert res_web.status_code == 303
    assert res_web.headers["location"] == "/login"

def test_create_organization_request_success():
    auth_client = get_authenticated_client()
    payload = {
        "member_id": "M00004",
        "organization_id": "ORG1001",
        "organization_name": "CityCare Hospital",
        "request_type": "Authorization Request",
        "service": "Diagnostic Brain MRI",
        "priority": "High",
        "request_date": "2026-08-19",
        "due_date": "2026-08-22",
        "status": "Pending",
        "description": "Brain MRI requested for neurological evaluation.",
        "requested_by": "Dr. Sarah Jenkins"
    }
    response = auth_client.post("/api/requests", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["request_id"].startswith("REQ")
    assert "submitted successfully" in data["message"]
    req = data["request"]
    assert req["member_id"] == "M00004"
    assert req["organization_name"] == "CityCare Hospital"
    assert req["priority"] == "High"
    assert req["status"] == "Pending"
    assert req["created_at"] != ""

def test_create_organization_request_invalid_member_400():
    auth_client = get_authenticated_client()
    payload = {
        "member_id": "M_NON_EXISTENT_99999",
        "organization_id": "ORG1001",
        "organization_name": "CityCare Hospital",
        "request_type": "Authorization Request",
        "service": "MRI",
        "priority": "High"
    }
    response = auth_client.post("/api/requests", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["success"] is False
    assert "not found" in data["detail"]["message"].lower()

def test_create_organization_request_invalid_priority_422():
    auth_client = get_authenticated_client()
    payload = {
        "member_id": "M00004",
        "organization_id": "ORG1001",
        "organization_name": "CityCare Hospital",
        "request_type": "Authorization Request",
        "service": "MRI",
        "priority": "SuperUrgentExtra"
    }
    response = auth_client.post("/api/requests", json=payload)
    assert response.status_code == 422  # Pydantic validation error

def test_list_and_filter_requests():
    auth_client = get_authenticated_client()
    
    # 1. List all
    res = auth_client.get("/api/requests?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["requests"]) > 0
    assert data["total"] > 0

    # 2. Filter by member_id
    res_mem = auth_client.get("/api/requests?member_id=M00004")
    assert res_mem.status_code == 200
    data_mem = res_mem.json()
    for r in data_mem["requests"]:
        assert r["member_id"] == "M00004"

    # 3. Filter by priority
    res_prio = auth_client.get("/api/requests?priority=High")
    assert res_prio.status_code == 200
    data_prio = res_prio.json()
    for r in data_prio["requests"]:
        assert r["priority"] == "High"

def test_get_single_request_and_404():
    auth_client = get_authenticated_client()
    all_reqs = search_requests(limit=1)
    assert len(all_reqs) > 0
    target_id = all_reqs[0]["request_id"]

    # Valid ID
    res = auth_client.get(f"/api/requests/{target_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["request"]["request_id"] == target_id

    # Invalid ID
    res_fake = auth_client.get("/api/requests/REQ_FAKE_99999")
    assert res_fake.status_code == 404

def test_get_member_requests_endpoint():
    auth_client = get_authenticated_client()
    res = auth_client.get("/api/requests/member/M00004")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["member_id"] == "M00004"
    assert isinstance(data["requests"], list)

def test_patch_request_status_and_notes():
    auth_client = get_authenticated_client()
    all_reqs = search_requests(limit=1)
    target_id = all_reqs[0]["request_id"]

    patch_payload = {
        "status": "In Review",
        "assigned_to": "Coordinator Jane Doe",
        "resolution_notes": "Clinical records requested from hospital."
    }
    res = auth_client.patch(f"/api/requests/{target_id}", json=patch_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["request"]["status"] == "In Review"
    assert data["request"]["assigned_to"] == "Coordinator Jane Doe"
    assert data["request"]["resolution_notes"] == "Clinical records requested from hospital."

def test_source_traceability_for_request():
    auth_client = get_authenticated_client()
    all_reqs = search_requests(limit=1)
    target_id = all_reqs[0]["request_id"]

    res = auth_client.get(f"/api/ai/source/request/{target_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["source_type"] == "request"
    assert data["source_id"] == target_id
    assert data["is_verified"] is True
    assert "record" in data
    assert data["record"]["request_id"] == target_id

def test_member_360_profile_includes_requests():
    auth_client = get_authenticated_client()
    profile = get_member_360_profile("M00004")
    assert profile is not None
    assert "requests" in profile
    assert isinstance(profile["requests"], list)
    assert "requests_count" in profile["stats"]
    assert "pending_requests_count" in profile["stats"]

    # Verify deterministic open issue rule for requests
    issues = profile.get("deterministic_open_issues", [])
    has_org_request_issue = any(iss.get("source_type") == "request" for iss in issues)
    # If M00004 has a pending request, an issue is present
    pending_reqs = [r for r in profile["requests"] if r.get("status") in ["Pending", "In Review"]]
    if pending_reqs:
        assert has_org_request_issue is True

def test_requests_web_page_authenticated():
    auth_client = get_authenticated_client()
    res = auth_client.get("/requests")
    assert res.status_code == 200
    assert "Organization &amp; Hospital Requests" in res.text or "Organization Requests" in res.text
    assert "Submit Organization Request" in res.text
