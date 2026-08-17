"""
AI Intelligence & Source Traceability Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
import math
from app.schemas.ai import AISummaryResponse
from app.services.ai_service import generate_member_ai_summary, validate_and_fetch_source_record
from app.services.auth import require_admin_api

router = APIRouter(tags=["AI Intelligence"])

def clean_nan_values(data):
    """
    Recursively replace NaN/Infinity values
    with None so they can be returned as valid JSON.
    """
    if isinstance(data, dict):
        return {
            key: clean_nan_values(value)
            for key, value in data.items()
        }

    if isinstance(data, list):
        return [
            clean_nan_values(value)
            for value in data
        ]

    if isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None

    return data

@router.post("/member/{member_id}/summary", response_model=AISummaryResponse, dependencies=[Depends(require_admin_api)])
async def get_member_ai_summary(member_id: str):
    """
    Primary AI Feature: Generates grounded Member 360 Healthcare Intelligence Summary (Admin Protected).
    Produces Key Facts, Open Issues, Next Operational Actions, and Traceable Sources.
    """
    try:
        summary = await generate_member_ai_summary(member_id)
        return summary
    except ValueError as ve:
        raise HTTPException(
            status_code=404,
            detail={"success": False, "message": str(ve)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": f"Unable to generate AI summary: {str(e)}"}
        )

@router.get("/source/{source_type}/{source_id}", dependencies=[Depends(require_admin_api)])
def inspect_source_record(source_type: str, source_id: str):
    """
    Source Traceability Endpoint (Admin Protected):
    Returns the exact original database record for any referenced source_id.
    """
    record = validate_and_fetch_source_record(source_type, source_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "message": f"Source record '{source_id}' of type '{source_type}' not found in database."
            }
        )
    return clean_nan_values({
        "success": True,
        "source_type": source_type,
        "source_id": source_id,
        "is_verified": True,
        "record": record
    })