"""
Aggregation Service & Deterministic Open Issue Detector
Assembles full 360° view of a member across all 7 collections and evaluates
deterministic operational rules prior to any AI processing.
"""
import math
from typing import Dict, Any, List, Optional
from app.database.mongodb import get_collection
from app.services.member_service import get_member_by_id

def safe_float(val: Any) -> float:
    """
    Safely converts arbitrary values to float, gracefully handling None, NaN,
    strings like 'N/A', 'None', '', etc. by returning 0.0 for aggregation.
    """
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        if math.isnan(val) or math.isinf(val):
            return 0.0
        return float(val)
    try:
        s = str(val).strip().replace(",", "").replace("$", "").replace("₹", "")
        if s.lower() in ["", "none", "null", "nan", "undefined", "not recorded", "not available", "unknown", "n/a", "na"]:
            return 0.0
        parsed = float(s)
        if math.isnan(parsed) or math.isinf(parsed):
            return 0.0
        return parsed
    except (ValueError, TypeError):
        return 0.0

def detect_deterministic_open_issues(
    eligibility: List[Dict[str, Any]],
    claims: List[Dict[str, Any]],
    care_gaps: List[Dict[str, Any]],
    authorizations: List[Dict[str, Any]],
    interactions: List[Dict[str, Any]],
    requests: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Evaluates strict deterministic rules for operational open issues.
    AI must NOT be responsible for basic status checks.
    """
    open_issues = []

    # Rule 1: Pending Authorizations
    for auth in authorizations:
        if auth.get("status") == "Pending":
            open_issues.append({
                "issue_type": "Pending Authorization",
                "severity": "High",
                "description": f"Prior authorization request for '{auth.get('service')}' is pending decision.",
                "source_type": "authorization",
                "source_id": auth.get("authorization_id", ""),
                "action_hint": "Follow up with clinical review team or provider for documentation."
            })

    # Rule 2: Pending Claims
    for clm in claims:
        if clm.get("status") == "Pending":
            open_issues.append({
                "issue_type": "Pending Claim",
                "severity": "Medium",
                "description": f"Claim {clm.get('claim_id')} ({clm.get('procedure')}, ${clm.get('amount')}) is pending adjudication.",
                "source_type": "claim",
                "source_id": clm.get("claim_id", ""),
                "action_hint": "Review billing status and payer adjudication queue."
            })

    # Rule 3: Open Care Gaps
    for gap in care_gaps:
        if gap.get("status") == "Open":
            open_issues.append({
                "issue_type": "Open Care Gap",
                "severity": "Medium",
                "description": f"{gap.get('gap_type')}: {gap.get('description')}",
                "source_type": "care_gap",
                "source_id": gap.get("gap_id", ""),
                "action_hint": "Coordinate outreach or check recent health system records."
            })

    # Rule 4: Unresolved Interactions
    for inter in interactions:
        if inter.get("status") in ["Open", "In Progress"]:
            open_issues.append({
                "issue_type": "Unresolved Member Contact",
                "severity": "High" if inter.get("status") == "Open" else "Medium",
                "description": f"Interaction {inter.get('interaction_id')} ({inter.get('channel')} - {inter.get('reason')}): {inter.get('summary')}",
                "source_type": "interaction",
                "source_id": inter.get("interaction_id", ""),
                "action_hint": "Complete representative follow-up on outstanding member inquiry."
            })

    # Rule 5: Non-active Eligibility
    if eligibility:
        active_count = sum(1 for e in eligibility if e.get("status") == "Active")
        if active_count == 0:
            open_issues.append({
                "issue_type": "Coverage Inactive",
                "severity": "High",
                "description": f"No active health plan coverage record found in current eligibility profile.",
                "source_type": "eligibility",
                "source_id": eligibility[0].get("eligibility_id", ""),
                "action_hint": "Verify member re-enrollment or transition status."
            })

    # Rule 6: Pending or In-Review Organization Requests
    if requests:
        for req in requests:
            req_status = str(req.get("status", "")).strip()
            if req_status in ["Pending", "In Review"]:
                priority = str(req.get("priority", "Medium")).strip()
                is_high = priority in ["High", "Urgent"]
                open_issues.append({
                    "issue_type": "Pending Organization Request",
                    "severity": "High" if is_high else "Medium",
                    "description": f"{priority} priority {req.get('request_type')} for '{req.get('service')}' from {req.get('organization_name')} is {req_status}.",
                    "source_type": "request",
                    "source_id": req.get("request_id", ""),
                    "action_hint": "Review organization request details, verify member clinical records, and coordinate operational determination."
                })

    return open_issues

def get_member_360_profile(member_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch comprehensive Member 360 profile across all 8 MongoDB collections.
    """
    member = get_member_by_id(member_id)
    if not member:
        return None

    actual_id = member["member_id"]

    # Retrieve all related documents sorted chronologically where applicable
    eligibility = list(get_collection("eligibility").find({"member_id": actual_id}, {"_id": 0}))
    claims = list(get_collection("claims").find({"member_id": actual_id}, {"_id": 0}).sort("claim_date", -1))
    medications = list(get_collection("medications").find({"member_id": actual_id}, {"_id": 0}).sort("start_date", -1))
    care_gaps = list(get_collection("care_gaps").find({"member_id": actual_id}, {"_id": 0}))
    authorizations = list(get_collection("authorizations").find({"member_id": actual_id}, {"_id": 0}).sort("request_date", -1))
    interactions = list(get_collection("interactions").find({"member_id": actual_id}, {"_id": 0}).sort("interaction_date", -1))
    requests = list(get_collection("requests").find({"member_id": actual_id}, {"_id": 0}).sort("request_date", -1))

    # Detect open issues deterministically
    open_issues = detect_deterministic_open_issues(
        eligibility=eligibility,
        claims=claims,
        care_gaps=care_gaps,
        authorizations=authorizations,
        interactions=interactions,
        requests=requests
    )

    # Compute summary metrics
    active_meds_count = sum(1 for m in medications if m.get("status") == "Active")
    pending_auth_count = sum(1 for a in authorizations if a.get("status") == "Pending")
    pending_requests_count = sum(1 for r in requests if r.get("status") in ["Pending", "In Review"])
    
    # Authoritative claim financial metrics derived directly from member's claims
    total_claims = len(claims)
    total_claim_amount = round(sum(safe_float(c.get("amount")) for c in claims), 2)
    plan_coverage_paid = round(sum(safe_float(c.get("payer_coverage")) for c in claims), 2)
    member_responsibility = round(sum(safe_float(c.get("member_copay")) for c in claims), 2)

    return {
        "member": member,
        "eligibility": eligibility,
        "claims": claims,
        "medications": medications,
        "care_gaps": care_gaps,
        "authorizations": authorizations,
        "interactions": interactions,
        "requests": requests,
        "open_issues_count": len(open_issues),
        "deterministic_open_issues": open_issues,
        "stats": {
            "claims_count": total_claims,
            "total_claims": total_claims,
            "total_claim_amount": total_claim_amount,
            "total_claims_amount": total_claim_amount,
            "plan_coverage_paid": plan_coverage_paid,
            "member_responsibility": member_responsibility,
            "total_expenses": total_claim_amount,
            "medications_count": len(medications),
            "active_medications_count": active_meds_count,
            "care_gaps_count": len(care_gaps),
            "authorizations_count": len(authorizations),
            "pending_authorizations_count": pending_auth_count,
            "interactions_count": len(interactions),
            "requests_count": len(requests),
            "pending_requests_count": pending_requests_count
        }
    }
