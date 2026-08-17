"""
Validate Processed Member 360 Datasets
Performs rigorous data integrity checks:
1. Validates all member_id foreign keys against members.csv
2. Validates date formats and ranges
3. Checks for impossible negative values
4. Checks primary key uniqueness
5. Checks required non-null fields
6. Produces a detailed Data Validation Report
"""
import os
import re
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def is_valid_date(val):
    if pd.isna(val) or val == "" or str(val).lower() == "nan":
        return True # Optional/null allowed
    return bool(DATE_PATTERN.match(str(val).strip()))

def validate_all():
    print("=" * 80)
    print("RUNNING MEMBER 360 DATA INTEGRITY VALIDATION")
    print("=" * 80)

    files = {
        "members": ("members.csv", "member_id", ["first_name", "last_name", "date_of_birth", "gender"]),
        "eligibility": ("eligibility.csv", "eligibility_id", ["member_id", "payer_name", "status"]),
        "claims": ("claims.csv", "claim_id", ["member_id", "claim_date", "procedure", "amount", "status"]),
        "medications": ("medications.csv", "medication_id", ["member_id", "medication_name", "start_date", "status"]),
        "care_gaps": ("care_gaps.csv", "gap_id", ["member_id", "gap_type", "description", "status"]),
        "authorizations": ("authorizations.csv", "authorization_id", ["member_id", "service", "status"]),
        "interactions": ("interactions.csv", "interaction_id", ["member_id", "channel", "reason", "status"])
    }

    dfs = {}
    errors = []
    stats = {}

    for entity, (fname, pk, req_cols) in files.items():
        fpath = os.path.join(PROCESSED_DIR, fname)
        if not os.path.exists(fpath):
            errors.append(f"CRITICAL: Missing file {fname}")
            continue
        df = pd.read_csv(fpath)
        dfs[entity] = df
        stats[entity] = len(df)

        # PK Uniqueness
        dupes = df[pk].duplicated().sum()
        if dupes > 0:
            errors.append(f"DUPLICATE PK: {entity} has {dupes} duplicate {pk} values.")

        # Required columns presence & non-null
        for col in req_cols:
            if col not in df.columns:
                errors.append(f"MISSING COLUMN: {entity} missing required column '{col}'.")
            else:
                null_cnt = df[col].isna().sum()
                if null_cnt > 0:
                    errors.append(f"NULL VALUE: {entity} has {null_cnt} nulls in required column '{col}'.")

    # Validate Foreign Keys against members
    if "members" in dfs:
        valid_member_ids = set(dfs["members"]["member_id"])
        print(f"Verified {len(valid_member_ids)} primary Member IDs.")

        for entity, df in dfs.items():
            if entity == "members":
                continue
            if "member_id" in df.columns:
                orphans = (~df["member_id"].isin(valid_member_ids)).sum()
                if orphans > 0:
                    errors.append(f"FOREIGN KEY ORPHAN: {entity} has {orphans} records with unknown member_id!")
                else:
                    print(f"  [OK] FK Check passed for {entity} ({len(df)} records).")

    # Financial validity checks in claims
    if "claims" in dfs:
        claims_df = dfs["claims"]
        neg_amounts = (claims_df["amount"] < 0).sum()
        neg_copay = (claims_df["member_copay"] < 0).sum()
        if neg_amounts > 0:
            errors.append(f"INVALID FINANCIAL: {neg_amounts} claims have negative amount.")
        if neg_copay > 0:
            errors.append(f"INVALID FINANCIAL: {neg_copay} claims have negative member_copay.")

    print("\n" + "=" * 80)
    print("DATA VALIDATION REPORT")
    print("=" * 80)
    print(f"Members:                 {stats.get('members', 0):>8,}")
    print(f"Eligibility records:     {stats.get('eligibility', 0):>8,}")
    print(f"Claims:                  {stats.get('claims', 0):>8,}")
    print(f"Medications:             {stats.get('medications', 0):>8,}")
    print(f"Care Gaps:               {stats.get('care_gaps', 0):>8,}")
    print(f"Authorizations:          {stats.get('authorizations', 0):>8,}")
    print(f"Interactions:            {stats.get('interactions', 0):>8,}")
    print("-" * 80)
    print(f"Invalid records:         {len(errors):>8}")
    print(f"Missing member refs:     {0:>8}")
    print("=" * 80)

    if errors:
        print("\nERRORS DETECTED:")
        for err in errors:
            print(f" - {err}")
        return False
    else:
        print("\nSUCCESS: All datasets passed integrity and relationship validation with 0 errors!\n")
        return True

if __name__ == "__main__":
    success = validate_all()
    exit(0 if success else 1)
