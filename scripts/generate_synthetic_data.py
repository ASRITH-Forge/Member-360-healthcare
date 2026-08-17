"""
Generate Project-Specific Synthetic Data
Creates:
1. authorizations.csv (deterministic prior authorization records)
2. interactions.csv (deterministic service representative contact logs)
Uses fixed random seed (SEED=42) for 100% reproducibility.
"""
import os
import random
import pandas as pd
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

def generate_authorizations_and_interactions():
    print("=" * 80)
    print("GENERATING SYNTHETIC AUTHORIZATIONS AND INTERACTIONS (SEED=42)")
    print("=" * 80)

    # Set fixed seed
    random.seed(42)

    members_file = os.path.join(PROCESSED_DIR, "members.csv")
    claims_file = os.path.join(PROCESSED_DIR, "claims.csv")
    gaps_file = os.path.join(PROCESSED_DIR, "care_gaps.csv")

    members_df = pd.read_csv(members_file)
    member_ids = list(members_df["member_id"])
    print(f"Loaded {len(member_ids)} members for synthetic generation.")

    services_pool = [
        "Specialist Consultation - Cardiology",
        "Outpatient MRI Lumbar Spine with Contrast",
        "Physical Therapy (12 Rehabilitative Sessions)",
        "Durable Medical Equipment - CPAP Machine & Supplies",
        "Outpatient Endoscopy & Diagnostic Biopsy",
        "Specialist Consultation - Orthopedic Surgery",
        "Home Health Aide (4-Week Post-Acute Support)",
        "CT Angiography Chest with IV Contrast",
        "Specialist Consultation - Neurology",
        "Cardiac Rehabilitation Phase II (36 Sessions)",
        "Outpatient Sleep Study Polysomnography",
        "Comprehensive Diabetic Foot Exam & Custom Orthotics"
    ]

    auth_records = []
    auth_counter = 1001
    member_auth_map = {}

    base_date = datetime(2026, 2, 1)

    for m_id in member_ids:
        # 65% of members have 1-3 authorization requests
        if random.random() < 0.65:
            num_auths = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
            for _ in range(num_auths):
                auth_id = f"AUTH-{auth_counter}"
                auth_counter += 1
                service = random.choice(services_pool)
                days_ago = random.randint(3, 120)
                req_date = (base_date - timedelta(days=days_ago)).strftime("%Y-%m-%d")

                # Distribution: Pending (22%), Approved (63%), Denied (10%), Cancelled (5%)
                status = random.choices(
                    ["Pending", "Approved", "Denied", "Cancelled"],
                    weights=[0.22, 0.63, 0.10, 0.05]
                )[0]

                if status == "Pending":
                    dec_date = ""
                    notes = f"Prior authorization request for {service} is currently under clinical review. Awaiting additional clinical documentation from provider."
                elif status == "Approved":
                    dec_days = random.randint(2, min(days_ago, 7))
                    dec_date = (datetime.strptime(req_date, "%Y-%m-%d") + timedelta(days=dec_days)).strftime("%Y-%m-%d")
                    notes = f"Approved for standard medical necessity. Valid for 180 days from decision date."
                elif status == "Denied":
                    dec_days = random.randint(2, min(days_ago, 7))
                    dec_date = (datetime.strptime(req_date, "%Y-%m-%d") + timedelta(days=dec_days)).strftime("%Y-%m-%d")
                    notes = f"Service does not meet conservative medical management criteria. Provider notified of appeal rights."
                else: # Cancelled
                    dec_days = random.randint(1, min(days_ago, 5))
                    dec_date = (datetime.strptime(req_date, "%Y-%m-%d") + timedelta(days=dec_days)).strftime("%Y-%m-%d")
                    notes = f"Request withdrawn by ordering provider."

                auth_item = {
                    "authorization_id": auth_id,
                    "member_id": m_id,
                    "service": service,
                    "request_date": req_date,
                    "status": status,
                    "decision_date": dec_date,
                    "source": "synthetic_authorization_engine",
                    "notes": notes
                }
                auth_records.append(auth_item)
                member_auth_map.setdefault(m_id, []).append(auth_item)

    auth_df = pd.DataFrame(auth_records)
    auth_out = os.path.join(PROCESSED_DIR, "authorizations.csv")
    auth_df.to_csv(auth_out, index=False)
    print(f"[1/2] Created {len(auth_df)} authorization records -> {auth_out}")

    # Interactions generation
    channels = ["Phone", "Portal", "Email", "In-Person"]
    reasons = [
        "Authorization Follow-up",
        "Claim Question",
        "Eligibility Question",
        "General Support",
        "Care Gap Outreach"
    ]

    interaction_records = []
    int_counter = 2001

    for m_id in member_ids:
        # Every member has 1 to 4 customer service interactions
        num_ints = random.choices([1, 2, 3, 4], weights=[0.4, 0.35, 0.15, 0.1])[0]
        
        # Check if member has pending auth or open care gap to create contextually linked notes
        m_auths = member_auth_map.get(m_id, [])
        pending_auths = [a for a in m_auths if a["status"] == "Pending"]

        for i in range(num_ints):
            int_id = f"INT-{int_counter}"
            int_counter += 1
            days_ago = random.randint(1, 90)
            int_date = (base_date - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            channel = random.choices(channels, weights=[0.55, 0.25, 0.15, 0.05])[0]

            if pending_auths and i == 0:
                reason = "Authorization Follow-up"
                p_auth = pending_auths[0]
                summary = f"Member contacted service center inquiring on status of pending authorization {p_auth['authorization_id']} for {p_auth['service']}. Representative informed member that clinical documentation review is in progress."
                status = random.choices(["Open", "In Progress", "Resolved"], weights=[0.4, 0.3, 0.3])[0]
            elif m_auths and i == 1:
                reason = "Authorization Follow-up"
                p_auth = m_auths[0]
                summary = f"Inquiry regarding authorization {p_auth['authorization_id']} ({p_auth['service']}). Status verified as {p_auth['status']}."
                status = "Resolved"
            else:
                reason = random.choice(reasons)
                if reason == "Claim Question":
                    summary = f"Member inquired about recent claim reimbursement, copayment obligation, and deductible progress. Explained EOB breakdown."
                elif reason == "Eligibility Question":
                    summary = f"Member verified active coverage dates, network provider directory access, and ID card replacement procedure."
                elif reason == "Care Gap Outreach":
                    summary = f"Care coordinator reached out to member regarding recommended annual wellness visit and preventive health screening reminders."
                else: # General Support
                    summary = f"Member requested assistance updating mailing address and updating preferred notification preferences."

                status = random.choices(["Resolved", "In Progress", "Open"], weights=[0.75, 0.15, 0.10])[0]

            interaction_records.append({
                "interaction_id": int_id,
                "member_id": m_id,
                "interaction_date": int_date,
                "channel": channel,
                "reason": reason,
                "summary": summary,
                "status": status,
                "source_type": "synthetic_service_log",
                "source_id": int_id
            })

    int_df = pd.DataFrame(interaction_records)
    int_out = os.path.join(PROCESSED_DIR, "interactions.csv")
    int_df.to_csv(int_out, index=False)
    print(f"[2/2] Created {len(int_df)} interaction records -> {int_out}")
    print("=" * 80)
    print("SYNTHETIC DATA GENERATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    generate_authorizations_and_interactions()
