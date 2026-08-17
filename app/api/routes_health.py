"""
Health Check and System Diagnostics API
"""
from fastapi import APIRouter
from app.database.mongodb import get_database, is_mock_db
from app.services.ai_service import GEMINI_API_KEY

router = APIRouter(tags=["Health"])

@router.get("/health")
def health_check():
    db = get_database()
    collections_count = {
        "members": db.members.count_documents({}),
        "eligibility": db.eligibility.count_documents({}),
        "claims": db.claims.count_documents({}),
        "medications": db.medications.count_documents({}),
        "care_gaps": db.care_gaps.count_documents({}),
        "authorizations": db.authorizations.count_documents({}),
        "interactions": db.interactions.count_documents({})
    }
    return {
        "status": "healthy",
        "service": "Member 360 Health Intelligence Assistant",
        "database": {
            "name": db.name,
            "is_mock_in_memory": is_mock_db(),
            "collections": collections_count
        },
        "ai": {
            "gemini_configured": bool(GEMINI_API_KEY)
        }
    }
