"""
Pydantic Schemas for Structured AI Summary & Traceability
Strictly enforces operational focus, source references, and clinical safety.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class FactItem(BaseModel):
    text: str = Field(..., description="Fact stated directly from supplied records.")
    source_type: str = Field(..., description="Category of record, e.g. eligibility, claims, medication, authorization")
    source_id: str = Field(..., description="Specific ID of the record, e.g. AUTH-1001, CLM-d0c40d10")

class IssueItem(BaseModel):
    text: str = Field(..., description="Documented operational or record issue.")
    source_type: str = Field(..., description="Category of record")
    source_id: str = Field(..., description="ID of source record")
    urgency: Optional[str] = Field("Operational", description="Urgency: High, Medium, Operational")

class NextActionItem(BaseModel):
    text: str = Field(..., description="Suggested operational representative action (non-clinical).")
    source_type: str = Field(..., description="Category of record")
    source_id: str = Field(..., description="ID of source record")
    action_type: Optional[str] = Field("Operational Follow-up", description="Category of task")

class ValidatedSource(BaseModel):
    source_type: str
    source_id: str
    is_verified: bool
    record: Optional[Dict[str, Any]] = None

class AISummaryResponse(BaseModel):
    success: bool = True
    member_id: str
    member_name: str
    key_facts: List[FactItem] = []
    open_issues: List[IssueItem] = []
    next_actions: List[NextActionItem] = []
    sources: List[ValidatedSource] = []
    disclaimer: str = (
        "Notice: This summary is generated for operational assistance and coordination purposes only. "
        "It is derived exclusively from synthetic Synthea member records. It does not provide medical "
        "diagnoses or clinical treatment recommendations."
    )
    generated_at: str = ""
