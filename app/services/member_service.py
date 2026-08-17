"""
Member Service
Handles member search, listing, and direct retrieval from MongoDB.
"""
import re
from typing import List, Optional, Dict, Any
from app.database.mongodb import get_collection

def get_member_by_id(member_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single member document by member_id."""
    coll = get_collection("members")
    # Clean ID
    clean_id = member_id.strip()
    doc = coll.find_one({"member_id": clean_id}, {"_id": 0})
    if not doc:
        # Case-insensitive or partial prefix search fallback
        doc = coll.find_one({"member_id": {"$regex": f"^{re.escape(clean_id)}", "$options": "i"}}, {"_id": 0})
    return doc

def search_members(query: str = "", limit: int = 25, skip: int = 0) -> List[Dict[str, Any]]:
    """
    Search members by Member ID, First Name, Last Name, City, or State.
    """
    coll = get_collection("members")
    query_str = query.strip()
    
    if not query_str:
        cursor = coll.find({}, {"_id": 0}).skip(skip).limit(limit)
        return list(cursor)

    # Multi-field regex match
    regex = {"$regex": re.escape(query_str), "$options": "i"}
    filter_query = {
        "$or": [
            {"member_id": regex},
            {"first_name": regex},
            {"last_name": regex},
            {"city": regex},
            {"state": regex}
        ]
    }

    cursor = coll.find(filter_query, {"_id": 0}).skip(skip).limit(limit)
    return list(cursor)

def count_members(query: str = "") -> int:
    """Get total matching members count."""
    coll = get_collection("members")
    query_str = query.strip()
    if not query_str:
        return coll.count_documents({})
    regex = {"$regex": re.escape(query_str), "$options": "i"}
    filter_query = {
        "$or": [
            {"member_id": regex},
            {"first_name": regex},
            {"last_name": regex},
            {"city": regex},
            {"state": regex}
        ]
    }
    return coll.count_documents(filter_query)
