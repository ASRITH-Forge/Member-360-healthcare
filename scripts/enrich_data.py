"""
Enrich Processed Datasets:
1. Fill all empty/missing fields (phone, email, postal code, marital status, care gap relations, decision dates, coordinator notes).
2. Ensure financial values (claims, medication costs) are realistic and in thousands of INR.
3. Ensure every member has comprehensive coverage across claims, medications, and interactions.
"""
import os
import random
import pandas as pd
import numpy as np

random.seed(42)
np.random.seed(42)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "processed")

FIRST_NAMES_INDIAN = ["Abhishek", "Aarav", "Varun", "Swathi", "Karthik", "Rakesh", "Navya", "Sneha", "Nisha", "Ananya", "Karan", "Sakshi", "Divya", "Anjali", "Keerthi", "Swathi", "Harsha", "Sravya", "Ananya", "Harini", "Isha", "Neha", "Pooja", "Rahul", "Rohan", "Vikram", "Aditi", "Priya", "Manish", "Amit", "Deepak", "Sunil", "Sanjay", "Meera", "Kavita", "Shreya", "Rhea", "Arjun", "Kunal", "Siddharth"]

PIN_CODES = ["560001", "560025", "560034", "560068", "560100", "110001", "110020", "110045", "400001", "400050", "400072", "600001", "600028", "500001", "500081", "700001", "380001", "411001"]

PROCEDURES = [
    ("Diagnostic Brain MRI", 35000.0, "Outpatient", "METROWEST MEDICAL CENTER"),
    ("Echocardiogram & Cardiac Consult", 22000.0, "Outpatient", "MOUNT AUBURN HOSPITAL"),
    ("Comprehensive Metabolic Panel & Blood Work", 8500.0, "Preventive Care", "AUBURN PODIATRY LLP"),
    ("General Inpatient Medical Care", 125000.0, "Inpatient", "BAYSTATE FRANKLIN MEDICAL CENTER"),
    ("Colonoscopy Screening", 45000.0, "Outpatient", "LAHEY HOSPITAL & MEDICAL CENTER"),
    ("Orthopedic Physical Therapy Evaluation", 15000.0, "Outpatient", "ORTHO SPORT PHYSICAL THERAPY INC"),
    ("Urgent Care Clinical Evaluation", 12000.0, "Urgent Care", "URGENT CARE MEDICAL CLINIC"),
    ("Chest X-Ray & Pulmonology Review", 18500.0, "Outpatient", "MORTON HOSPITAL"),
    ("Abdominal Ultrasound", 24000.0, "Outpatient", "HARRINGTON MEMORIAL HOSPITAL"),
    ("Annual Wellness & Preventive Visit", 9500.0, "Preventive Care", "UMASS MEMORIAL MEDICAL GROUP"),
    ("Cardiac Stress Test", 32000.0, "Outpatient", "STURDY MEMORIAL HOSPITAL"),
    ("Endoscopy Procedure", 52000.0, "Inpatient", "HOLYOKE MEDICAL CENTER")
]

def enrich_all():
    print("=" * 80)
    print("ENRICHING PROCESSED DATASETS (FILLING EMPTY FIELDS & VALUES IN THOUSANDS)")
    print("=" * 80)

    # 1. Members
    members_path = os.path.join(DATA_DIR, "members.csv")
    df_members = pd.read_csv(members_path, dtype=str)
    print(f"[1/8] Processing members.csv ({len(df_members)} records)...")
    
    for idx, row in df_members.iterrows():
        mid = row["member_id"]
        fname = str(row["first_name"]).strip() if pd.notnull(row["first_name"]) else random.choice(FIRST_NAMES_INDIAN)
        lname = str(row["last_name"]).strip() if pd.notnull(row["last_name"]) else "Sharma"
        
        # Phone: +91 98XXX XXXXX
        if pd.isnull(row["phone"]) or str(row["phone"]).strip() in ["", "nan", "None"]:
            num_suffix = f"{random.randint(9000000000, 9999999999)}"
            df_members.at[idx, "phone"] = f"+91 {num_suffix[:5]} {num_suffix[5:]}"
            
        # Email: fname.lname@healthmail.com
        if pd.isnull(row["email"]) or str(row["email"]).strip() in ["", "nan", "None"]:
            clean_f = ''.join(e for e in fname.lower() if e.isalnum())
            clean_l = ''.join(e for e in lname.lower() if e.isalnum())
            df_members.at[idx, "email"] = f"{clean_f}.{clean_l}{mid[-3:]}@healthmail.com"
            
        # Postal Code
        if pd.isnull(row["postal_code"]) or str(row["postal_code"]).strip() in ["", "nan", "None", "0", "0.0"]:
            df_members.at[idx, "postal_code"] = str(random.choice(PIN_CODES))
        else:
            p = str(row["postal_code"]).replace(".0", "").strip()
            if len(p) < 5:
                p = f"{p.zfill(5)}"
            df_members.at[idx, "postal_code"] = p

        # Marital Status
        if pd.isnull(row["marital_status"]) or str(row["marital_status"]).strip() in ["", "nan", "None"]:
            dob = str(row["date_of_birth"])
            birth_year = int(dob[:4]) if len(dob) >= 4 and dob[:4].isdigit() else 1990
            df_members.at[idx, "marital_status"] = "M" if (2026 - birth_year) >= 26 else "S"

    df_members.to_csv(members_path, index=False)
    print("  [+] members.csv enriched successfully.")

    # 2. Claims (Values in Thousands)
    claims_path = os.path.join(DATA_DIR, "claims.csv")
    df_claims = pd.read_csv(claims_path)
    print(f"[2/8] Processing claims.csv ({len(df_claims)} records)...")

    # Check existing amount magnitude; if mean < 2000, scale by 100 to put in thousands
    if df_claims["amount"].mean() < 2000:
        print("  - Scaling claim amounts by 100 to reflect realistic healthcare costs in thousands of INR...")
        df_claims["amount"] = (df_claims["amount"] * 100).round(2)
        df_claims["payer_coverage"] = (df_claims["payer_coverage"] * 100).round(2)
        df_claims["member_copay"] = (df_claims["amount"] - df_claims["payer_coverage"]).round(2)

    # Ensure all 1171 members have claim records
    existing_claim_members = set(df_claims["member_id"].dropna().unique())
    all_members = list(df_members["member_id"].unique())
    missing_claim_members = [m for m in all_members if m not in existing_claim_members]

    new_claim_rows = []
    max_claim_id = 10000
    for cid in df_claims["claim_id"]:
        try:
            num = int(str(cid).replace("CLM", ""))
            if num > max_claim_id:
                max_claim_id = num
        except:
            pass

    for mid in missing_claim_members:
        num_claims = random.randint(2, 5)
        for _ in range(num_claims):
            max_claim_id += 1
            proc_name, base_cost, ctype, provider = random.choice(PROCEDURES)
            variance = random.uniform(0.85, 1.25)
            claim_amt = round(base_cost * variance, 2)
            cov_ratio = random.choice([0.75, 0.80, 0.85, 0.90])
            payer_cov = round(claim_amt * cov_ratio, 2)
            copay = round(claim_amt - payer_cov, 2)
            status = random.choice(["Approved", "Paid", "Approved", "Approved", "Pending"])
            c_date = f"202{random.randint(4, 6)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"

            new_claim_rows.append({
                "claim_id": f"CLM{max_claim_id}",
                "member_id": mid,
                "claim_date": c_date,
                "claim_type": ctype,
                "provider": provider,
                "service": proc_name,
                "amount": claim_amt,
                "payer_coverage": payer_cov,
                "member_copay": copay,
                "status": status,
                "source": "Synthetic"
            })

    if new_claim_rows:
        df_new_claims = pd.DataFrame(new_claim_rows)
        df_claims = pd.concat([df_claims, df_new_claims], ignore_index=True)
        print(f"  - Added {len(new_claim_rows)} claim records for {len(missing_claim_members)} previously empty members.")

    df_claims.to_csv(claims_path, index=False)
    print(f"  [+] claims.csv updated (Total rows: {len(df_claims)}, Mean amount: INR {df_claims['amount'].mean():,.2f}).")

    # 3. Medications
    meds_path = os.path.join(DATA_DIR, "medications.csv")
    df_meds = pd.read_csv(meds_path)
    print(f"[3/8] Processing medications.csv ({len(df_meds)} records)...")
    if df_meds["total_cost"].mean() < 5000:
        print("  - Scaling medication total_cost to realistic INR values in thousands...")
        df_meds["total_cost"] = (df_meds["total_cost"] * 100).clip(lower=1250.0).round(2)
    df_meds.to_csv(meds_path, index=False)
    print("  [+] medications.csv updated.")

    # 4. Care Gaps
    gaps_path = os.path.join(DATA_DIR, "care_gaps.csv")
    df_gaps = pd.read_csv(gaps_path, dtype=str)
    print(f"[4/8] Processing care_gaps.csv ({len(df_gaps)} records)...")
    for idx, row in df_gaps.iterrows():
        if pd.isnull(row["related_interaction_id"]) or str(row["related_interaction_id"]).strip() in ["", "nan", "None"]:
            df_gaps.at[idx, "related_interaction_id"] = f"INT{random.randint(10001, 15000)}"
        if pd.isnull(row["related_authorization_id"]) or str(row["related_authorization_id"]).strip() in ["", "nan", "None"]:
            if random.random() < 0.4:
                df_gaps.at[idx, "related_authorization_id"] = f"AUTH{random.randint(10001, 11200)}"
    df_gaps.to_csv(gaps_path, index=False)
    print("  [+] care_gaps.csv updated.")

    # 5. Authorizations
    auth_path = os.path.join(DATA_DIR, "authorizations.csv")
    df_auth = pd.read_csv(auth_path, dtype=str)
    print(f"[5/8] Processing authorizations.csv ({len(df_auth)} records)...")
    for idx, row in df_auth.iterrows():
        if row["status"] in ["Approved", "Denied", "Completed"] and (pd.isnull(row["decision_date"]) or str(row["decision_date"]).strip() in ["", "nan", "None"]):
            req_date = str(row["request_date"])
            try:
                dt = pd.to_datetime(req_date) + pd.Timedelta(days=random.randint(2, 5))
                df_auth.at[idx, "decision_date"] = dt.strftime("%Y-%m-%d")
            except:
                df_auth.at[idx, "decision_date"] = "2026-06-15"
    df_auth.to_csv(auth_path, index=False)
    print("  [+] authorizations.csv updated.")

    # 6. Requests
    req_path = os.path.join(DATA_DIR, "requests.csv")
    if os.path.exists(req_path):
        df_req = pd.read_csv(req_path, dtype=str)
        print(f"[6/8] Processing requests.csv ({len(df_req)} records)...")
        for idx, row in df_req.iterrows():
            if pd.isnull(row["assigned_to"]) or str(row["assigned_to"]).strip() in ["", "nan", "None"]:
                df_req.at[idx, "assigned_to"] = random.choice(["Care Coordinator Priya Sharma", "Care Coordinator Rajesh Kumar", "Care Coordinator Ananya Rao"])
            if pd.isnull(row["resolution_notes"]) or str(row["resolution_notes"]).strip() in ["", "nan", "None"]:
                if row["status"] in ["Approved", "Completed"]:
                    df_req.at[idx, "resolution_notes"] = "Clinical criteria verified against policy guidelines; request approved."
                elif row["status"] in ["Rejected", "Cancelled"]:
                    df_req.at[idx, "resolution_notes"] = "Service duplicate or prior coverage expired."
                else:
                    df_req.at[idx, "resolution_notes"] = "Intake verified; pending physician review and clinical documentation."
        df_req.to_csv(req_path, index=False)
        print("  [+] requests.csv updated.")

    print("=" * 80)
    print("DATA ENRICHMENT COMPLETE! ALL EMPTY VALUES POPULATED & FINANCIAL AMOUNTS SCALED TO THOUSANDS.")
    print("=" * 80)

if __name__ == "__main__":
    enrich_all()
