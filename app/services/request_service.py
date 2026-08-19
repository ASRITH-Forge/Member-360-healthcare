"""
Organization Request Service
Handles business logic, validation, CRUD operations, and ID generation for organization/hospital requests.
"""
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.database.mongodb import get_collection
from app.services.member_service import get_member_by_id
from app.schemas.request import ALLOWED_STATUSES, ALLOWED_PRIORITIES

def generate_request_id() -> str:
    """Generate the next sequential Request ID in format REQ10001."""
    coll = get_collection("requests")
    # Scan existing records to find max numeric ID
    max_num = 10000
    cursor = coll.find({}, {"request_id": 1, "_id": 0})
    for doc in cursor:
        rid = doc.get("request_id", "")
        match = re.search(r"REQ(\d+)", rid, re.IGNORECASE)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
    return f"REQ{max_num + 1}"

def create_organization_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates member existence and required fields, assigns sequential ID,
    and inserts the organization request record.
    """
    coll = get_collection("requests")
    member_id = str(data.get("member_id", "")).strip()
    if not member_id:
        raise ValueError("member_id is required.")

    # Verify target member exists in records
    member = get_member_by_id(member_id)
    if not member:
        raise ValueError(f"Target member with ID '{member_id}' was not found in the member registry.")

    actual_member_id = member["member_id"]

    org_id = str(data.get("organization_id", "")).strip()
    org_name = str(data.get("organization_name", "")).strip()
    req_type = str(data.get("request_type", "")).strip()
    service = str(data.get("service", "")).strip()

    if not org_name:
        raise ValueError("organization_name is required.")
    if not org_id:
        raise ValueError("organization_id is required.")
    if not req_type:
        raise ValueError("request_type is required.")
    if not service:
        raise ValueError("service is required.")

    priority = str(data.get("priority", "Medium")).strip().title()
    if priority not in ALLOWED_PRIORITIES:
        raise ValueError(f"Invalid priority '{priority}'. Allowed: {', '.join(ALLOWED_PRIORITIES)}")

    status = str(data.get("status", "Pending")).strip()
    matched_status = [s for s in ALLOWED_STATUSES if s.lower() == status.lower()]
    if not matched_status:
        raise ValueError(f"Invalid status '{status}'. Allowed: {', '.join(ALLOWED_STATUSES)}")
    status = matched_status[0]

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    req_id = data.get("request_id")
    if not req_id:
        req_id = generate_request_id()
    else:
        req_id = str(req_id).strip()
        # Verify uniqueness
        if coll.find_one({"request_id": req_id}):
            req_id = generate_request_id()

    request_doc = {
        "request_id": req_id,
        "member_id": actual_member_id,
        "organization_id": org_id,
        "organization_name": org_name,
        "request_type": req_type,
        "service": service,
        "priority": priority,
        "request_date": data.get("request_date") or today_str,
        "status": status,
        "description": data.get("description", "") or "",
        "requested_by": data.get("requested_by", "") or "",
        "assigned_to": data.get("assigned_to", "") or "",
        "due_date": data.get("due_date", "") or "",
        "resolution_notes": data.get("resolution_notes", "") or "",
        "created_at": now_iso,
        "updated_at": now_iso,
        "source": data.get("source", "Organization") or "Organization"
    }

    coll.insert_one(request_doc)
    # Remove internal _id for return
    request_doc.pop("_id", None)
    return request_doc

def get_request_by_id(request_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single organization request by request_id."""
    if not request_id:
        return None
    clean_id = str(request_id).strip()
    coll = get_collection("requests")
    doc = coll.find_one({"request_id": clean_id}, {"_id": 0})
    if not doc:
        doc = coll.find_one({"request_id": {"$regex": f"^{re.escape(clean_id)}$", "$options": "i"}}, {"_id": 0})
    return doc

def get_requests_by_member(member_id: str) -> List[Dict[str, Any]]:
    """Retrieve all organization requests associated with a member ID."""
    if not member_id:
        return []
    clean_id = str(member_id).strip()
    coll = get_collection("requests")
    cursor = coll.find({"member_id": clean_id}, {"_id": 0}).sort("request_date", -1)
    return list(cursor)

def search_requests(
    member_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    organization_name: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    request_type: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 25,
    skip: int = 0
) -> List[Dict[str, Any]]:
    """Search and filter organization requests with multi-criteria support."""
    coll = get_collection("requests")
    filter_query: Dict[str, Any] = {}

    if member_id:
        filter_query["member_id"] = str(member_id).strip()
    if organization_id:
        filter_query["organization_id"] = str(organization_id).strip()
    if organization_name:
        filter_query["organization_name"] = {"$regex": re.escape(organization_name.strip()), "$options": "i"}
    if status:
        filter_query["status"] = {"$regex": f"^{re.escape(status.strip())}$", "$options": "i"}
    if priority:
        filter_query["priority"] = {"$regex": f"^{re.escape(priority.strip())}$", "$options": "i"}
    if request_type:
        filter_query["request_type"] = {"$regex": re.escape(request_type.strip()), "$options": "i"}

    if query:
        q_clean = query.strip()
        q_regex = {"$regex": re.escape(q_clean), "$options": "i"}
        filter_query["$or"] = [
            {"request_id": q_regex},
            {"member_id": q_regex},
            {"organization_name": q_regex},
            {"service": q_regex},
            {"description": q_regex},
            {"requested_by": q_regex},
            {"assigned_to": q_regex}
        ]

    cursor = coll.find(filter_query, {"_id": 0}).sort([("request_date", -1), ("created_at", -1)]).skip(skip).limit(limit)
    return list(cursor)

def count_requests(
    member_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    organization_name: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    request_type: Optional[str] = None,
    query: Optional[str] = None
) -> int:
    """Get total matching count for requests."""
    coll = get_collection("requests")
    filter_query: Dict[str, Any] = {}

    if member_id:
        filter_query["member_id"] = str(member_id).strip()
    if organization_id:
        filter_query["organization_id"] = str(organization_id).strip()
    if organization_name:
        filter_query["organization_name"] = {"$regex": re.escape(organization_name.strip()), "$options": "i"}
    if status:
        filter_query["status"] = {"$regex": f"^{re.escape(status.strip())}$", "$options": "i"}
    if priority:
        filter_query["priority"] = {"$regex": f"^{re.escape(priority.strip())}$", "$options": "i"}
    if request_type:
        filter_query["request_type"] = {"$regex": re.escape(request_type.strip()), "$options": "i"}

    if query:
        q_clean = query.strip()
        q_regex = {"$regex": re.escape(q_clean), "$options": "i"}
        filter_query["$or"] = [
            {"request_id": q_regex},
            {"member_id": q_regex},
            {"organization_name": q_regex},
            {"service": q_regex},
            {"description": q_regex},
            {"requested_by": q_regex},
            {"assigned_to": q_regex}
        ]

    return coll.count_documents(filter_query)

def update_request_status(request_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Updates request status, coordinator assignment, resolution notes, and timestamp.
    """
    coll = get_collection("requests")
    clean_id = str(request_id).strip()
    existing = get_request_by_id(clean_id)
    if not existing:
        return None

    actual_id = existing["request_id"]
    set_fields: Dict[str, Any] = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    }

    if "status" in updates and updates["status"] is not None:
        status_val = str(updates["status"]).strip()
        matched = [s for s in ALLOWED_STATUSES if s.lower() == status_val.lower()]
        if not matched:
            raise ValueError(f"Invalid status '{status_val}'. Allowed: {', '.join(ALLOWED_STATUSES)}")
        set_fields["status"] = matched[0]

    if "priority" in updates and updates["priority"] is not None:
        prio_val = str(updates["priority"]).strip().title()
        if prio_val not in ALLOWED_PRIORITIES:
            raise ValueError(f"Invalid priority '{prio_val}'. Allowed: {', '.join(ALLOWED_PRIORITIES)}")
        set_fields["priority"] = prio_val

    for field in ["assigned_to", "resolution_notes", "due_date", "description", "service", "request_type"]:
        if field in updates and updates[field] is not None:
            set_fields[field] = str(updates[field]).strip()

    coll.update_one({"request_id": actual_id}, {"$set": set_fields})
    return get_request_by_id(actual_id)

def delete_request(request_id: str) -> bool:
    """Safe deletion of an organization request."""
    coll = get_collection("requests")
    clean_id = str(request_id).strip()
    result = coll.delete_one({"request_id": clean_id})
    return result.deleted_count > 0
