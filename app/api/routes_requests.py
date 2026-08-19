"""
Organization / Hospital Request Management API Endpoints
"""
import math
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends, status
from app.schemas.request import OrganizationRequestCreate, OrganizationRequestUpdate, OrganizationRequestModel
from app.services.request_service import (
    create_organization_request,
    get_request_by_id,
    get_requests_by_member,
    search_requests,
    count_requests,
    update_request_status,
    delete_request
)
from app.services.auth import require_admin_api

router = APIRouter(tags=["Organization Requests"])

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

@router.post("/requests", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin_api)])
def submit_organization_request(payload: OrganizationRequestCreate):
    """
    Create a new organization/hospital operational request for a member (Admin Protected).
    Validates member existence, assigns sequential request_id, and records timestamps.
    """
    try:
        created_doc = create_organization_request(payload.model_dump())
        return clean_nan_values({
            "success": True,
            "message": f"Request {created_doc['request_id']} submitted successfully.",
            "request_id": created_doc["request_id"],
            "request": created_doc
        })
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": str(ve)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": f"Failed to create organization request: {str(e)}"
            }
        )

@router.get("/requests", dependencies=[Depends(require_admin_api)])
def list_or_search_requests(
    member_id: Optional[str] = Query(None, description="Filter by Member ID"),
    organization_id: Optional[str] = Query(None, description="Filter by Organization ID"),
    organization_name: Optional[str] = Query(None, description="Filter by Organization Name"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by Lifecycle Status"),
    priority: Optional[str] = Query(None, description="Filter by Priority"),
    request_type: Optional[str] = Query(None, description="Filter by Request Type"),
    q: Optional[str] = Query(None, description="Broad search query"),
    limit: int = Query(25, ge=1, le=100),
    page: int = Query(1, ge=1)
):
    """
    List and filter organization requests with pagination (Admin Protected).
    """
    skip = (page - 1) * limit
    results = search_requests(
        member_id=member_id,
        organization_id=organization_id,
        organization_name=organization_name,
        status=status_filter,
        priority=priority,
        request_type=request_type,
        query=q,
        limit=limit,
        skip=skip
    )
    total = count_requests(
        member_id=member_id,
        organization_id=organization_id,
        organization_name=organization_name,
        status=status_filter,
        priority=priority,
        request_type=request_type,
        query=q
    )

    return clean_nan_values({
        "success": True,
        "total": total,
        "page": page,
        "limit": limit,
        "requests": results
    })

@router.get("/requests/{request_id}", dependencies=[Depends(require_admin_api)])
def get_single_request(request_id: str):
    """
    Retrieve details for a specific organization request by ID (Admin Protected).
    """
    doc = get_request_by_id(request_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "message": f"Organization request with ID '{request_id}' not found."
            }
        )
    return clean_nan_values({
        "success": True,
        "request": doc
    })

@router.get("/requests/member/{member_id}", dependencies=[Depends(require_admin_api)])
def get_member_requests(member_id: str):
    """
    Retrieve all organization requests associated with a specific member (Admin Protected).
    """
    requests_list = get_requests_by_member(member_id)
    return clean_nan_values({
        "success": True,
        "member_id": member_id,
        "count": len(requests_list),
        "requests": requests_list
    })

@router.patch("/requests/{request_id}", dependencies=[Depends(require_admin_api)])
def modify_request_status_or_details(request_id: str, payload: OrganizationRequestUpdate):
    """
    Update request status, coordinator assignment, resolution notes, or details (Admin Protected).
    """
    try:
        updated_doc = update_request_status(request_id, payload.model_dump(exclude_unset=True))
        if not updated_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "message": f"Organization request with ID '{request_id}' not found."
                }
            )
        return clean_nan_values({
            "success": True,
            "message": f"Request {request_id} updated successfully.",
            "request": updated_doc
        })
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": str(ve)
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": f"Failed to update request: {str(e)}"
            }
        )

@router.delete("/requests/{request_id}", dependencies=[Depends(require_admin_api)])
def remove_organization_request(request_id: str):
    """
    Delete an organization request by ID (Admin Protected).
    """
    deleted = delete_request(request_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "message": f"Organization request with ID '{request_id}' not found."
            }
        )
    return {
        "success": True,
        "message": f"Request {request_id} deleted successfully."
    }
