"""
Member 360° API Endpoints
"""
import math
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from app.services.member_service import get_member_by_id, search_members, count_members
from app.services.aggregation_service import get_member_360_profile
from app.services.auth import require_admin_api
from app.schemas.member import Member360Response

router = APIRouter(tags=["Members"])

def clean_nan_values(data):
    """
    Recursively replace NaN/Infinity values with None so they can be serialized as valid JSON.
    """
    if isinstance(data, dict):
        return {key: clean_nan_values(value) for key, value in data.items()}
    if isinstance(data, list):
        return [clean_nan_values(value) for value in data]
    if isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None
    return data

@router.get("/members", dependencies=[Depends(require_admin_api)])
def list_or_search_members(
    q: Optional[str] = Query(None, description="Search query for ID, name, city, or state"),
    limit: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1)
):
    """
    Search and paginate members (Admin Protected).
    """
    skip = (page - 1) * limit
    query_str = q or ""
    results = search_members(query=query_str, limit=limit, skip=skip)
    total = count_members(query=query_str)

    return clean_nan_values({
        "success": True,
        "total": total,
        "page": page,
        "limit": limit,
        "members": results
    })

@router.get("/member/{member_id}", dependencies=[Depends(require_admin_api)])
def get_member_360(member_id: str):
    """
    Central Member 360 endpoint (Admin Protected).
    Returns member demographics, eligibility, claims, medications,
    care gaps, authorizations, interactions, and deterministic open issues.
    """
    profile = get_member_360_profile(member_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "message": f"Member with ID '{member_id}' not found."
            }
        )
    return clean_nan_values(profile)
