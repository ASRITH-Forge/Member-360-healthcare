"""
AI Intelligence Service for Member 360°
Integrates with Google Gemini API using the official Google GenAI SDK.
Enforces strict clinical safety guardrails, structured JSON output, and backend source traceability validation.
"""
import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

from app.database.mongodb import get_collection
from app.schemas.ai import AISummaryResponse, FactItem, IssueItem, NextActionItem, ValidatedSource
from app.services.aggregation_service import get_member_360_profile

load_dotenv()
logger = logging.getLogger("member360.ai")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

SYSTEM_INSTRUCTION = """
You are a Member 360° Health Intelligence Assistant.
Your purpose is to help a healthcare service representative or care coordinator understand the operational information present in the supplied member records.

CRITICAL SAFETY & OPERATIONAL RULES:
1. Use ONLY the supplied member records and open issues context.
2. Do NOT invent facts or hallucinate record IDs.
3. Do NOT diagnose diseases or make unsupported clinical conclusions.
4. Do NOT recommend treatments, clinical protocols, or medication changes.
5. Do NOT infer diseases merely from medications (e.g. if Metformin is listed, state 'Medication record for Metformin is present', do NOT assert 'Member has diabetes' unless an explicit condition record says so).
6. Next operational actions must be strictly administrative and operational for a service coordinator (e.g. follow up on pending prior authorization, review claim adjudication status, review organization request documentation, verify eligibility, schedule annual wellness outreach).
7. Every fact, open issue, and action MUST reference an exact source_type and source_id from the supplied records.
8. When organization or hospital requests are present, highlight pending or high/urgent priority requests, approaching due dates, and recommend specific coordinator operational follow-ups.

You MUST return your response as a valid JSON object matching this exact schema:
{
  "key_facts": [
    {"text": "Fact description directly from record.", "source_type": "eligibility|claim|medication|authorization|interaction|member|request", "source_id": "EXACT_ID"}
  ],
  "open_issues": [
    {"text": "Documented operational or record issue.", "source_type": "authorization|claim|care_gap|interaction|eligibility|request", "source_id": "EXACT_ID", "urgency": "High|Medium|Operational"}
  ],
  "next_actions": [
    {"text": "Operational follow-up step.", "source_type": "authorization|claim|care_gap|interaction|request", "source_id": "EXACT_ID", "action_type": "Operational Follow-up|Documentation Request|Outreach"}
  ]
}
"""

def construct_ai_context(profile: Dict[str, Any]) -> str:
    """Build compact, structured, sanitized context for the LLM."""
    m = profile["member"]
    name = f"{m.get('first_name', '')} {m.get('last_name', '')}".strip()
    
    # 1. Member
    context_lines = [
        f"MEMBER IDENTIFIER: {m.get('member_id')}",
        f"NAME: {name} | DOB: {m.get('date_of_birth')} | GENDER: {m.get('gender')} | LOCATION: {m.get('city')}, {m.get('state')}",
        "",
        "ELIGIBILITY COVERAGE:"
    ]
    for e in profile.get("eligibility", []):
        context_lines.append(f"- ID: {e.get('eligibility_id')} | Payer: {e.get('payer_name')} | Plan: {e.get('plan_name')} | Status: {e.get('status')} | Period: {e.get('coverage_start')} to {e.get('coverage_end') or 'Present'}")

    context_lines.append("\nRECENT CLAIMS (Top 5):")
    for c in profile.get("claims", [])[:5]:
        context_lines.append(f"- ID: {c.get('claim_id')} | Date: {c.get('claim_date')} | Type: {c.get('claim_type')} | Procedure: {c.get('procedure')} | Cost: ${c.get('amount')} | Payer: ${c.get('payer_coverage')} | Copay: ${c.get('member_copay')} | Status: {c.get('status')}")

    context_lines.append("\nACTIVE / RECENT MEDICATIONS (Top 5):")
    for med in profile.get("medications", [])[:5]:
        context_lines.append(f"- ID: {med.get('medication_id')} | Medication: {med.get('medication_name')} | Start: {med.get('start_date')} | Status: {med.get('status')} | Reason: {med.get('reason')}")

    context_lines.append("\nDOCUMENTED CARE GAPS:")
    for gap in profile.get("care_gaps", []):
        context_lines.append(f"- ID: {gap.get('gap_id')} | Type: {gap.get('gap_type')} | Status: {gap.get('status')} | Audit Note: {gap.get('description')}")

    context_lines.append("\nPRIOR AUTHORIZATIONS:")
    for auth in profile.get("authorizations", []):
        context_lines.append(f"- ID: {auth.get('authorization_id')} | Service: {auth.get('service')} | Request Date: {auth.get('request_date')} | Status: {auth.get('status')} | Notes: {auth.get('notes')}")

    context_lines.append("\nORGANIZATION / HOSPITAL REQUESTS:")
    for req in profile.get("requests", []):
        context_lines.append(f"- ID: {req.get('request_id')} | Organization: {req.get('organization_name')} ({req.get('organization_id')}) | Type: {req.get('request_type')} | Service: {req.get('service')} | Priority: {req.get('priority')} | Status: {req.get('status')} | Request Date: {req.get('request_date')} | Due Date: {req.get('due_date') or 'None'} | Description: {req.get('description')} | Requested By: {req.get('requested_by')} | Assigned To: {req.get('assigned_to') or 'Unassigned'}")

    context_lines.append("\nRECENT SERVICE INTERACTIONS:")
    for inter in profile.get("interactions", [])[:5]:
        context_lines.append(f"- ID: {inter.get('interaction_id')} | Date: {inter.get('interaction_date')} | Channel: {inter.get('channel')} | Reason: {inter.get('reason')} | Status: {inter.get('status')} | Summary: {inter.get('summary')}")

    context_lines.append("\nDETERMINISTIC OPEN ISSUES (Pre-Calculated):")
    for iss in profile.get("deterministic_open_issues", []):
        context_lines.append(f"- Source: {iss.get('source_type')} [{iss.get('source_id')}] | {iss.get('issue_type')}: {iss.get('description')}")

    return "\n".join(context_lines)

def validate_and_fetch_source_record(source_type: str, source_id: str) -> Optional[Dict[str, Any]]:
    """
    Validates that a referenced source ID actually exists in the MongoDB database
    and returns the sanitized original record.
    """
    if not source_id or not source_type:
        return None

    clean_id = str(source_id).strip()
    type_coll_map = {
        "authorization": ("authorizations", "authorization_id"),
        "authorizations": ("authorizations", "authorization_id"),
        "claim": ("claims", "claim_id"),
        "claims": ("claims", "claim_id"),
        "eligibility": ("eligibility", "eligibility_id"),
        "medication": ("medications", "medication_id"),
        "medications": ("medications", "medication_id"),
        "care_gap": ("care_gaps", "gap_id"),
        "care_gaps": ("care_gaps", "gap_id"),
        "interaction": ("interactions", "interaction_id"),
        "interactions": ("interactions", "interaction_id"),
        "request": ("requests", "request_id"),
        "requests": ("requests", "request_id"),
        "member": ("members", "member_id")
    }

    if source_type.lower() in type_coll_map:
        coll_name, key_field = type_coll_map[source_type.lower()]
        doc = get_collection(coll_name).find_one({key_field: clean_id}, {"_id": 0})
        if doc:
            return doc
        # Also check source_id field if applicable
        doc = get_collection(coll_name).find_one({"source_id": clean_id}, {"_id": 0})
        if doc:
            return doc

    # Broad search across all collections as fallback
    for c_name, key_f in [
        ("authorizations", "authorization_id"),
        ("requests", "request_id"),
        ("claims", "claim_id"),
        ("eligibility", "eligibility_id"),
        ("medications", "medication_id"),
        ("care_gaps", "gap_id"),
        ("interactions", "interaction_id"),
        ("members", "member_id")
    ]:
        doc = get_collection(c_name).find_one({key_f: clean_id}, {"_id": 0})
        if doc:
            return doc

    return None

def generate_fallback_summary(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Grounded deterministic intelligence summary used when Gemini API key is not configured
    or when LLM network endpoint is unavailable.
    """
    m = profile["member"]
    name = f"{m.get('first_name', '')} {m.get('last_name', '')}".strip()
    
    key_facts = []
    open_issues = []
    next_actions = []

    # 1. Eligibility Fact
    active_elig = [e for e in profile.get("eligibility", []) if e.get("status") == "Active"]
    if active_elig:
        e = active_elig[0]
        key_facts.append({
            "text": f"Member has active health coverage with {e.get('payer_name')} under {e.get('plan_name')}.",
            "source_type": "eligibility",
            "source_id": e.get("eligibility_id")
        })
    elif profile.get("eligibility"):
        e = profile["eligibility"][0]
        key_facts.append({
            "text": f"Coverage record under {e.get('payer_name')} is currently {e.get('status')}.",
            "source_type": "eligibility",
            "source_id": e.get("eligibility_id")
        })

    # 2. Medications Fact
    active_meds = [med for med in profile.get("medications", []) if med.get("status") == "Active"]
    if active_meds:
        med = active_meds[0]
        key_facts.append({
            "text": f"Active medication record documented: {med.get('medication_name')} (Prescribed for {med.get('reason', 'Maintenance')}).",
            "source_type": "medication",
            "source_id": med.get("medication_id")
        })

    # 3. Claims Fact
    if profile.get("claims"):
        latest_claim = profile["claims"][0]
        key_facts.append({
            "text": f"Most recent claim on {latest_claim.get('claim_date')} for {latest_claim.get('procedure')} (${latest_claim.get('amount')}) is marked as {latest_claim.get('status')}.",
            "source_type": "claim",
            "source_id": latest_claim.get("claim_id")
        })

    # 4. Organization Requests Fact (if present)
    if profile.get("requests"):
        latest_req = profile["requests"][0]
        key_facts.append({
            "text": f"Organization request {latest_req.get('request_id')} ({latest_req.get('request_type')} - {latest_req.get('service')}) submitted by {latest_req.get('organization_name')} is currently {latest_req.get('status')}.",
            "source_type": "request",
            "source_id": latest_req.get("request_id")
        })

    # Open issues & next actions from deterministic issues
    for iss in profile.get("deterministic_open_issues", []):
        open_issues.append({
            "text": iss.get("description"),
            "source_type": iss.get("source_type"),
            "source_id": iss.get("source_id"),
            "urgency": iss.get("severity", "Operational")
        })
        next_actions.append({
            "text": iss.get("action_hint", f"Review outstanding {iss.get('issue_type')} record."),
            "source_type": iss.get("source_type"),
            "source_id": iss.get("source_id"),
            "action_type": "Operational Follow-up"
        })

    if not open_issues:
        open_issues.append({
            "text": "No critical pending authorizations or overdue claim adjudications identified.",
            "source_type": "member",
            "source_id": m.get("member_id"),
            "urgency": "Operational"
        })
        next_actions.append({
            "text": "Perform routine member check-in and verify demographic contact details.",
            "source_type": "member",
            "source_id": m.get("member_id"),
            "action_type": "Outreach"
        })

    return {
        "key_facts": key_facts,
        "open_issues": open_issues,
        "next_actions": next_actions
    }

async def generate_member_ai_summary(member_id: str) -> AISummaryResponse:
    """
    Orchestrates the Member 360 AI Summary:
    1. Fetch profile and context
    2. Calls Gemini API with structured prompt
    3. Parses and validates Pydantic response
    4. Validates source traceability against real MongoDB records
    """
    profile = get_member_360_profile(member_id)
    if not profile:
        raise ValueError(f"Member with ID '{member_id}' not found.")

    m = profile["member"]
    member_name = f"{m.get('first_name', '')} {m.get('last_name', '')}".strip()
    context_text = construct_ai_context(profile)

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    raw_ai_dict = None

    if api_key:
        try:
            # Official Google GenAI SDK
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            prompt_content = f"CONTEXT INFORMATION:\n{context_text}\n\nPlease generate the Member 360 Intelligence Summary in JSON according to system instructions."
            
            response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt_content,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )

            response_text = response.text.strip()
            # Clean possible markdown wrapping
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            raw_ai_dict = json.loads(response_text)
            logger.info(f"[AI Service] Successfully generated Gemini summary for member {member_id}")
        except Exception as e:
            logger.warning(f"[AI Service] Gemini API call note ({e}). Falling back to deterministic intelligence summary.")
            raw_ai_dict = generate_fallback_summary(profile)
    else:
        logger.info("[AI Service] No GEMINI_API_KEY configured. Utilizing deterministic intelligence pipeline.")
        raw_ai_dict = generate_fallback_summary(profile)

    # Validate with Pydantic
    parsed_facts = [FactItem(**item) for item in raw_ai_dict.get("key_facts", [])]
    parsed_issues = [IssueItem(**item) for item in raw_ai_dict.get("open_issues", [])]
    parsed_actions = [NextActionItem(**item) for item in raw_ai_dict.get("next_actions", [])]

    # Collect all unique source IDs mentioned
    referenced_sources = {}
    for item in parsed_facts + parsed_issues + parsed_actions:
        key = (item.source_type, item.source_id)
        if key not in referenced_sources:
            referenced_sources[key] = True

    # Validate each source against MongoDB
    validated_sources: List[ValidatedSource] = []
    for (stype, sid) in referenced_sources.keys():
        record_doc = validate_and_fetch_source_record(stype, sid)
        validated_sources.append(
            ValidatedSource(
                source_type=stype,
                source_id=sid,
                is_verified=record_doc is not None,
                record=record_doc
            )
        )

    return AISummaryResponse(
        success=True,
        member_id=m.get("member_id"),
        member_name=member_name,
        key_facts=parsed_facts,
        open_issues=parsed_issues,
        next_actions=parsed_actions,
        sources=validated_sources,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    )
