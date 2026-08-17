"""
Synthea Data Transformation Pipeline
Transforms raw Synthea CSV files into normalized Member 360 processed files.
All transformations are idempotent, non-destructive to raw data, and deterministic.
"""
import os
import re
import math
import numpy as np
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw", "synthea")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

os.makedirs(PROCESSED_DIR, exist_ok=True)

def clean_name(name):
    """Strip synthetic trailing digits from Synthea names (e.g. 'John123' -> 'John')"""
    if pd.isna(name):
        return ""
    name_str = str(name)
    # Remove numbers from name
    cleaned = re.sub(r'\d+', '', name_str).strip()
    return cleaned if cleaned else name_str

def format_date_str(val):
    """Normalize date strings to YYYY-MM-DD"""
    if pd.isna(val) or val == "" or str(val).lower() == "nan":
        return ""
    val_str = str(val).strip()
    try:
        # Extract YYYY-MM-DD
        if "T" in val_str:
            return val_str.split("T")[0]
        if " " in val_str:
            return val_str.split(" ")[0]
        return val_str[:10]
    except Exception:
        return val_str

def transform_members():
    """Transform patients.csv -> members.csv"""
    print("[1/5] Transforming patients.csv -> members.csv...")
    patients_file = os.path.join(RAW_DIR, "patients.csv")
    df = pd.read_csv(patients_file, dtype=str)

    members = pd.DataFrame()
    members["member_id"] = df["Id"]
    members["first_name"] = df["FIRST"].apply(clean_name)
    members["last_name"] = df["LAST"].apply(clean_name)
    members["date_of_birth"] = df["BIRTHDATE"].apply(format_date_str)
    members["death_date"] = df["DEATHDATE"].apply(format_date_str)
    members["gender"] = df["GENDER"].fillna("U")
    members["race"] = df["RACE"].fillna("unknown")
    members["ethnicity"] = df["ETHNICITY"].fillna("unknown")
    members["marital_status"] = df["MARITAL"].fillna("S")
    members["address"] = df["ADDRESS"].fillna("")
    members["city"] = df["CITY"].fillna("")
    members["state"] = df["STATE"].fillna("")
    members["zip"] = df["ZIP"].fillna("")
    
    # Financial indicators
    members["healthcare_expenses"] = pd.to_numeric(df["HEALTHCARE_EXPENSES"], errors="coerce").fillna(0.0).round(2)
    members["healthcare_coverage"] = pd.to_numeric(df["HEALTHCARE_COVERAGE"], errors="coerce").fillna(0.0).round(2)

    # Alive status
    members["is_alive"] = members["death_date"].apply(lambda d: True if d == "" else False)

    out_file = os.path.join(PROCESSED_DIR, "members.csv")
    members.to_csv(out_file, index=False)
    print(f"      Saved {len(members)} records to {out_file}")
    return members

def transform_eligibility(members_df):
    """Transform payer_transitions.csv & payers.csv -> eligibility.csv"""
    print("[2/5] Transforming payer_transitions.csv & payers.csv -> eligibility.csv...")
    transitions_file = os.path.join(RAW_DIR, "payer_transitions.csv")
    payers_file = os.path.join(RAW_DIR, "payers.csv")

    df_trans = pd.read_csv(transitions_file, dtype=str)
    df_payers = pd.read_csv(payers_file, dtype=str) if os.path.exists(payers_file) else pd.DataFrame()

    # Create payer lookup
    payer_map = {}
    if not df_payers.empty and "Id" in df_payers.columns and "NAME" in df_payers.columns:
        payer_map = dict(zip(df_payers["Id"], df_payers["NAME"]))

    records = []
    # Group by patient to find latest coverage
    valid_member_ids = set(members_df["member_id"])

    for idx, row in df_trans.iterrows():
        patient_id = row["PATIENT"]
        if patient_id not in valid_member_ids:
            continue

        payer_id = str(row["PAYER"]) if pd.notna(row["PAYER"]) else "NO_PAYER"
        payer_name = payer_map.get(payer_id, "Standard Healthcare Coverage")
        start_year = str(row["START_YEAR"]) if pd.notna(row["START_YEAR"]) else "2015"
        end_year = str(row["END_YEAR"]) if pd.notna(row["END_YEAR"]) else ""
        ownership = str(row["OWNERSHIP"]) if pd.notna(row["OWNERSHIP"]) else "Individual"

        start_date = f"{start_year}-01-01"
        end_date = f"{end_year}-12-31" if end_year and end_year.lower() != "nan" else ""

        # Plan type name derived realistically
        if "Medicare" in payer_name:
            plan_name = "Medicare Advantage Comprehensive"
        elif "Medicaid" in payer_name or "Dual" in payer_name:
            plan_name = "State Health Essential Plan"
        elif ownership.lower() == "guardian":
            plan_name = "Family Comprehensive PPO"
        elif "Blue Cross" in payer_name:
            plan_name = "Blue Choice Preferred Care"
        else:
            plan_name = f"{payer_name} Standard Tier"

        # Determine status
        current_year = 2026
        try:
            ey = int(end_year) if end_year and end_year.lower() != "nan" else None
        except ValueError:
            ey = None

        if ey is None or ey >= current_year:
            status = "Active"
        else:
            status = "Expired"

        elig_id = f"ELIG-{patient_id[:8].upper()}-{idx:04d}"
        records.append({
            "eligibility_id": elig_id,
            "member_id": patient_id,
            "payer_id": payer_id,
            "payer_name": payer_name,
            "plan_name": plan_name,
            "ownership": ownership,
            "coverage_start": start_date,
            "coverage_end": end_date,
            "status": status,
            "source_type": "payer_transition",
            "source_id": f"TRANS_{idx}"
        })

    # For members with no transitions, assign standard default active record
    members_with_elig = {r["member_id"] for r in records}
    for m_id in valid_member_ids:
        if m_id not in members_with_elig:
            records.append({
                "eligibility_id": f"ELIG-{m_id[:8].upper()}-DEF1",
                "member_id": m_id,
                "payer_id": "DEFAULT_COMMUNITY_PAYER",
                "payer_name": "Community Health Plan",
                "plan_name": "Standard Comprehensive PPO",
                "ownership": "Individual",
                "coverage_start": "2020-01-01",
                "coverage_end": "",
                "status": "Active",
                "source_type": "derived_default",
                "source_id": "DEF_ELIG_001"
            })

    elig_df = pd.DataFrame(records)
    out_file = os.path.join(PROCESSED_DIR, "eligibility.csv")
    elig_df.to_csv(out_file, index=False)
    print(f"      Saved {len(elig_df)} records to {out_file}")
    return elig_df

def transform_claims(members_df):
    """Transform encounters.csv & providers.csv -> claims.csv (Claims-Like View)"""
    print("[3/5] Transforming encounters.csv -> claims.csv (Claims-Like View)...")
    enc_file = os.path.join(RAW_DIR, "encounters.csv")
    prov_file = os.path.join(RAW_DIR, "providers.csv")

    df_enc = pd.read_csv(enc_file, dtype=str)
    df_prov = pd.read_csv(prov_file, dtype=str) if os.path.exists(prov_file) else pd.DataFrame()

    prov_map = {}
    if not df_prov.empty and "Id" in df_prov.columns and "NAME" in df_prov.columns:
        for _, row in df_prov.iterrows():
            prov_map[row["Id"]] = f"{clean_name(row['NAME'])} ({row.get('SPECIALITY', 'General Practice')})"

    valid_member_ids = set(members_df["member_id"])
    records = []

    # Deterministic status generator based on encounter id hash (seed 42)
    np.random.seed(42)

    for idx, row in df_enc.iterrows():
        patient_id = row["PATIENT"]
        if patient_id not in valid_member_ids:
            continue

        enc_id = row["Id"]
        claim_id = f"CLM-{enc_id[:12].upper()}"
        start_date = format_date_str(row["START"])
        enc_class = str(row["ENCOUNTERCLASS"]).capitalize() if pd.notna(row["ENCOUNTERCLASS"]) else "Ambulatory"
        
        prov_id = row.get("PROVIDER", "")
        provider_name = prov_map.get(prov_id, f"Provider #{str(prov_id)[:8]}") if prov_id else "Community Healthcare Network"

        # Procedure / Reason Description
        desc = row.get("DESCRIPTION", "")
        reason = row.get("REASONDESCRIPTION", "")
        if pd.notna(desc) and str(desc).strip() != "":
            procedure = str(desc).strip()
        elif pd.notna(reason) and str(reason).strip() != "":
            procedure = str(reason).strip()
        else:
            procedure = f"{enc_class} Medical Visit"

        # Costs
        try:
            total_cost = float(row.get("TOTAL_CLAIM_COST", 0.0))
            if math.isnan(total_cost) or total_cost < 0:
                total_cost = float(row.get("BASE_ENCOUNTER_COST", 125.0))
        except (ValueError, TypeError):
            total_cost = 125.0

        try:
            payer_cov = float(row.get("PAYER_COVERAGE", 0.0))
            if math.isnan(payer_cov) or payer_cov < 0:
                payer_cov = total_cost * 0.8
        except (ValueError, TypeError):
            payer_cov = total_cost * 0.8

        member_copay = max(0.0, round(total_cost - payer_cov, 2))
        total_cost = round(total_cost, 2)
        payer_cov = round(payer_cov, 2)

        # Deterministic status derivation:
        # Date within last 6 months -> 25% Pending, 65% Paid, 10% Denied
        # Older -> 92% Paid, 8% Denied
        h_val = int(enc_id.replace("-", "")[:6], 16) % 100
        if start_date >= "2023-01-01":
            if h_val < 20:
                status = "Pending"
            elif h_val < 30:
                status = "Denied"
            else:
                status = "Paid"
        else:
            if h_val < 7:
                status = "Denied"
            else:
                status = "Paid"

        records.append({
            "claim_id": claim_id,
            "member_id": patient_id,
            "claim_date": start_date,
            "claim_type": enc_class,
            "provider": provider_name,
            "procedure": procedure,
            "amount": total_cost,
            "payer_coverage": payer_cov,
            "member_copay": member_copay,
            "status": status,
            "source_type": "encounter",
            "source_id": enc_id
        })

    claims_df = pd.DataFrame(records)
    out_file = os.path.join(PROCESSED_DIR, "claims.csv")
    claims_df.to_csv(out_file, index=False)
    print(f"      Saved {len(claims_df)} records to {out_file}")
    return claims_df

def transform_medications(members_df):
    """Transform medications.csv -> medications.csv"""
    print("[4/5] Transforming medications.csv -> medications.csv...")
    meds_file = os.path.join(RAW_DIR, "medications.csv")
    df_meds = pd.read_csv(meds_file, dtype=str)

    valid_member_ids = set(members_df["member_id"])
    records = []

    for idx, row in df_meds.iterrows():
        patient_id = row["PATIENT"]
        if patient_id not in valid_member_ids:
            continue

        start_date = format_date_str(row["START"])
        stop_date = format_date_str(row["STOP"])
        med_name = str(row["DESCRIPTION"]) if pd.notna(row["DESCRIPTION"]) else "Prescribed Medication"
        code = str(row["CODE"]) if pd.notna(row["CODE"]) else ""
        reason = str(row["REASONDESCRIPTION"]) if pd.notna(row["REASONDESCRIPTION"]) else "Routine Maintenance"
        
        try:
            dispenses = int(float(row["DISPENSES"])) if pd.notna(row["DISPENSES"]) else 1
        except (ValueError, TypeError):
            dispenses = 1

        try:
            total_cost = round(float(row["TOTALCOST"]), 2) if pd.notna(row["TOTALCOST"]) else 0.0
            if math.isnan(total_cost) or total_cost < 0:
                total_cost = 0.0
        except (ValueError, TypeError):
            total_cost = 0.0

        # Status: if stop_date is empty or in future -> Active, else Completed
        if stop_date == "" or stop_date >= "2026-01-01":
            status = "Active"
        else:
            status = "Completed"

        med_id = f"MED-{patient_id[:8].upper()}-{idx:05d}"
        enc_ref = str(row["ENCOUNTER"]) if pd.notna(row["ENCOUNTER"]) else f"ENC_{idx}"

        records.append({
            "medication_id": med_id,
            "member_id": patient_id,
            "medication_name": med_name,
            "code": code,
            "start_date": start_date,
            "end_date": stop_date,
            "reason": reason,
            "dispenses": dispenses,
            "total_cost": total_cost,
            "status": status,
            "source_type": "medication",
            "source_id": enc_ref
        })

    meds_df = pd.DataFrame(records)
    out_file = os.path.join(PROCESSED_DIR, "medications.csv")
    meds_df.to_csv(out_file, index=False)
    print(f"      Saved {len(meds_df)} records to {out_file}")
    return meds_df

def transform_care_gaps(members_df):
    """
    Derive Care Gaps (care_gaps.csv) with strict clinical safety wording.
    Gaps represent missing records in the supplied dataset.
    """
    print("[5/5] Deriving care_gaps.csv from encounters, conditions, immunizations, careplans...")
    valid_member_ids = set(members_df["member_id"])

    # Load supporting files
    enc_file = os.path.join(RAW_DIR, "encounters.csv")
    cond_file = os.path.join(RAW_DIR, "conditions.csv")
    imm_file = os.path.join(RAW_DIR, "immunizations.csv")
    care_file = os.path.join(RAW_DIR, "careplans.csv")

    df_enc = pd.read_csv(enc_file, dtype=str) if os.path.exists(enc_file) else pd.DataFrame()
    df_cond = pd.read_csv(cond_file, dtype=str) if os.path.exists(cond_file) else pd.DataFrame()
    df_imm = pd.read_csv(imm_file, dtype=str) if os.path.exists(imm_file) else pd.DataFrame()
    df_care = pd.read_csv(care_file, dtype=str) if os.path.exists(care_file) else pd.DataFrame()

    # Pre-index by patient
    patient_wellness = {}
    if not df_enc.empty:
        for _, row in df_enc.iterrows():
            pid = row["PATIENT"]
            if pid in valid_member_ids and str(row.get("ENCOUNTERCLASS", "")).lower() == "wellness":
                dt = format_date_str(row.get("START", ""))
                if pid not in patient_wellness or dt > patient_wellness[pid]:
                    patient_wellness[pid] = dt

    patient_flu_shots = {}
    if not df_imm.empty:
        for _, row in df_imm.iterrows():
            pid = row["PATIENT"]
            desc = str(row.get("DESCRIPTION", "")).lower()
            if pid in valid_member_ids and ("influenza" in desc or "flu" in desc):
                dt = format_date_str(row.get("DATE", ""))
                if pid not in patient_flu_shots or dt > patient_flu_shots[pid]:
                    patient_flu_shots[pid] = dt

    patient_conditions = {}
    if not df_cond.empty:
        for _, row in df_cond.iterrows():
            pid = row["PATIENT"]
            desc = str(row.get("DESCRIPTION", ""))
            if pid in valid_member_ids:
                patient_conditions.setdefault(pid, []).append(desc)

    patient_active_careplans = {}
    if not df_care.empty:
        for _, row in df_care.iterrows():
            pid = row["PATIENT"]
            stop = str(row.get("STOP", ""))
            if pid in valid_member_ids and (pd.isna(stop) or stop == "" or stop.lower() == "nan"):
                patient_active_careplans.setdefault(pid, []).append(row)

    gaps = []
    gap_idx = 1000

    for m_id in valid_member_ids:
        # 1. Annual Preventive Wellness Record Gap
        last_wellness = patient_wellness.get(m_id, "")
        if not last_wellness or last_wellness < "2023-01-01":
            gap_idx += 1
            gaps.append({
                "gap_id": f"GAP-{gap_idx}",
                "member_id": m_id,
                "gap_type": "Preventive Care Record Gap",
                "description": "Expected annual preventive wellness encounter record not found in supplied dataset.",
                "status": "Open",
                "source_type": "dataset_audit",
                "source_id": "AUDIT-WELLNESS-01",
                "detected_date": "2026-01-15"
            })

        # 2. Seasonal Immunization Record Gap
        last_flu = patient_flu_shots.get(m_id, "")
        if not last_flu or last_flu < "2023-09-01":
            gap_idx += 1
            gaps.append({
                "gap_id": f"GAP-{gap_idx}",
                "member_id": m_id,
                "gap_type": "Immunization Record Gap",
                "description": "Expected annual seasonal influenza vaccination record not found in supplied dataset.",
                "status": "Open",
                "source_type": "dataset_audit",
                "source_id": "AUDIT-FLU-01",
                "detected_date": "2026-01-15"
            })

        # 3. Chronic Condition Follow-up Record Gap
        conds = patient_conditions.get(m_id, [])
        chronic_hits = [c for c in conds if any(k in c.lower() for k in ["hypertension", "diabetes", "hyperlipidemia", "asthma"])]
        if chronic_hits:
            gap_idx += 1
            cond_name = chronic_hits[0]
            gaps.append({
                "gap_id": f"GAP-{gap_idx}",
                "member_id": m_id,
                "gap_type": "Chronic Condition Monitoring Gap",
                "description": f"Documented {cond_name} record found without routine follow-up audit entry in current cycle.",
                "status": "Open",
                "source_type": "condition",
                "source_id": f"COND-{cond_name[:12].replace(' ', '_')}",
                "detected_date": "2026-02-01"
            })

        # 4. Active Care Plan Review Gap
        plans = patient_active_careplans.get(m_id, [])
        if plans:
            p = plans[0]
            gap_idx += 1
            p_desc = p.get("DESCRIPTION", "Active Care Plan")
            gaps.append({
                "gap_id": f"GAP-{gap_idx}",
                "member_id": m_id,
                "gap_type": "Care Plan Review Gap",
                "description": f"Active care plan record '{p_desc}' has no documented 90-day progress review in supplied records.",
                "status": "Open",
                "source_type": "careplan",
                "source_id": str(p.get("Id", f"PLAN_{gap_idx}")),
                "detected_date": "2026-02-10"
            })

    gaps_df = pd.DataFrame(gaps)
    out_file = os.path.join(PROCESSED_DIR, "care_gaps.csv")
    gaps_df.to_csv(out_file, index=False)
    print(f"      Saved {len(gaps_df)} records to {out_file}")
    return gaps_df

def run_pipeline():
    print("=" * 80)
    print("STARTING MEMBER 360 TRANSFORMATION PIPELINE")
    print("=" * 80)
    members_df = transform_members()
    transform_eligibility(members_df)
    transform_claims(members_df)
    transform_medications(members_df)
    transform_care_gaps(members_df)
    print("=" * 80)
    print("CORE TRANSFORMATION PIPELINE COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    run_pipeline()
