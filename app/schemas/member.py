"""
Pydantic Schemas for Member 360 Core Entities
"""
from typing import Optional, List, Any
from pydantic import BaseModel, Field

class MemberModel(BaseModel):
    member_id: str
    first_name: str
    last_name: str
    date_of_birth: Optional[str] = ""
    death_date: Optional[str] = ""
    gender: Optional[str] = "U"
    race: Optional[str] = ""
    ethnicity: Optional[str] = ""
    marital_status: Optional[str] = ""
    address: Optional[str] = ""
    city: Optional[str] = ""
    state: Optional[str] = ""
    zip: Optional[str] = ""
    healthcare_expenses: Optional[float] = 0.0
    healthcare_coverage: Optional[float] = 0.0
    is_alive: Optional[bool] = True

class EligibilityModel(BaseModel):
    eligibility_id: str
    member_id: str
    payer_id: Optional[str] = ""
    payer_name: str
    plan_name: str
    ownership: Optional[str] = "Individual"
    coverage_start: Optional[str] = ""
    coverage_end: Optional[str] = ""
    status: str
    source_type: Optional[str] = "payer_transition"
    source_id: Optional[str] = ""

class ClaimModel(BaseModel):
    claim_id: str
    member_id: str
    claim_date: str
    claim_type: str
    provider: str
    procedure: str
    amount: float
    payer_coverage: Optional[float] = 0.0
    member_copay: Optional[float] = 0.0
    status: str
    source_type: Optional[str] = "encounter"
    source_id: Optional[str] = ""

class MedicationModel(BaseModel):
    medication_id: str
    member_id: str
    medication_name: str
    code: Optional[str] = ""
    start_date: str
    end_date: Optional[str] = ""
    reason: Optional[str] = ""
    dispenses: Optional[int] = 1
    total_cost: Optional[float] = 0.0
    status: str
    source_type: Optional[str] = "medication"
    source_id: Optional[str] = ""

class CareGapModel(BaseModel):
    gap_id: str
    member_id: str
    gap_type: str
    description: str
    status: str
    source_type: Optional[str] = "dataset_audit"
    source_id: Optional[str] = ""
    detected_date: Optional[str] = ""

class AuthorizationModel(BaseModel):
    authorization_id: str
    member_id: str
    service: str
    request_date: str
    status: str
    decision_date: Optional[str] = ""
    source: Optional[str] = "synthetic_authorization_engine"
    notes: Optional[str] = ""

class InteractionModel(BaseModel):
    interaction_id: str
    member_id: str
    interaction_date: str
    channel: str
    reason: str
    summary: str
    status: str
    source_type: Optional[str] = "synthetic_service_log"
    source_id: Optional[str] = ""

class Member360Response(BaseModel):
    member: MemberModel
    eligibility: List[EligibilityModel] = []
    claims: List[ClaimModel] = []
    medications: List[MedicationModel] = []
    care_gaps: List[CareGapModel] = []
    authorizations: List[AuthorizationModel] = []
    interactions: List[InteractionModel] = []
    open_issues_count: int = 0
    deterministic_open_issues: List[dict] = []
