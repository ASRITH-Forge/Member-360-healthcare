"""
Pydantic Schemas for Organization / Hospital Request Management
"""
from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel, Field, field_validator

ALLOWED_STATUSES = ["Pending", "In Review", "Approved", "Rejected", "Completed", "Cancelled"]
ALLOWED_PRIORITIES = ["Low", "Medium", "High", "Urgent"]

class OrganizationRequestBase(BaseModel):
    member_id: str = Field(..., description="Target member identifier, e.g. M00004")
    organization_id: str = Field(..., description="Unique organization code, e.g. ORG1001")
    organization_name: str = Field(..., description="Hospital or healthcare organization name")
    request_type: str = Field(..., description="Type of request, e.g. Authorization Request, Care Coordination")
    service: str = Field(..., description="Specific procedure or service requested, e.g. MRI, Cardiology Consultation")
    priority: str = Field("Medium", description="Request priority: Low, Medium, High, Urgent")
    request_date: Optional[str] = Field(None, description="Date of request (YYYY-MM-DD)")
    due_date: Optional[str] = Field("", description="Target due date for completion (YYYY-MM-DD)")
    status: Optional[str] = Field("Pending", description="Lifecycle status")
    description: Optional[str] = Field("", description="Clinical or operational description of request")
    requested_by: Optional[str] = Field("", description="Submitting provider or hospital coordinator name")
    assigned_to: Optional[str] = Field("", description="Care coordinator or reviewer assigned to process request")
    resolution_notes: Optional[str] = Field("", description="Coordinator notes or disposition rationale")
    source: Optional[str] = Field("Organization", description="Data origin channel")

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        v_title = v.strip().title() if v else "Medium"
        if v_title not in ALLOWED_PRIORITIES:
            raise ValueError(f"Invalid priority '{v}'. Allowed values are: {', '.join(ALLOWED_PRIORITIES)}")
        return v_title

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> str:
        if not v:
            return "Pending"
        v_clean = v.strip()
        matched = [s for s in ALLOWED_STATUSES if s.lower() == v_clean.lower()]
        if not matched:
            raise ValueError(f"Invalid status '{v}'. Allowed values are: {', '.join(ALLOWED_STATUSES)}")
        return matched[0]

class OrganizationRequestCreate(OrganizationRequestBase):
    pass

class OrganizationRequestUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Updated lifecycle status")
    assigned_to: Optional[str] = Field(None, description="Assigned care coordinator")
    resolution_notes: Optional[str] = Field(None, description="Operational disposition or review notes")
    priority: Optional[str] = Field(None, description="Updated priority")
    due_date: Optional[str] = Field(None, description="Updated due date")
    description: Optional[str] = Field(None, description="Updated description")
    service: Optional[str] = Field(None, description="Updated service")
    request_type: Optional[str] = Field(None, description="Updated request type")

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_title = v.strip().title()
        if v_title not in ALLOWED_PRIORITIES:
            raise ValueError(f"Invalid priority '{v}'. Allowed values are: {', '.join(ALLOWED_PRIORITIES)}")
        return v_title

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_clean = v.strip()
        matched = [s for s in ALLOWED_STATUSES if s.lower() == v_clean.lower()]
        if not matched:
            raise ValueError(f"Invalid status '{v}'. Allowed values are: {', '.join(ALLOWED_STATUSES)}")
        return matched[0]

class OrganizationRequestModel(BaseModel):
    request_id: str
    member_id: str
    organization_id: str
    organization_name: str
    request_type: str
    service: str
    priority: str
    request_date: str
    status: str
    description: Optional[str] = ""
    requested_by: Optional[str] = ""
    assigned_to: Optional[str] = ""
    due_date: Optional[str] = ""
    resolution_notes: Optional[str] = ""
    created_at: Optional[str] = ""
    updated_at: Optional[str] = ""
    source: Optional[str] = "Organization"
