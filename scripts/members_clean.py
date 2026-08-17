import pandas as pd
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================

RAW_DIR = Path("data/raw/synthea")
PROCESSED_DIR = Path("data/processed")

PATIENTS_FILE = RAW_DIR / "patients.csv"
OUTPUT_FILE = PROCESSED_DIR / "members.csv"

# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# ============================================================
# LOAD PATIENTS
# ============================================================

print("Loading Synthea patients...")

patients = pd.read_csv(
    PATIENTS_FILE
)

print(
    f"Patients: {len(patients)}"
)

print("\nPatient columns:")

print(
    patients.columns.tolist()
)

# ============================================================
# CREATE MEMBER IDs
# ============================================================

patients = patients.reset_index(
    drop=True
)

patients["member_id"] = [
    f"M{index + 1:05d}"
    for index in range(len(patients))
]

# ============================================================
# MAP SYNTHEA PATIENT DATA
# ============================================================

clean_members = pd.DataFrame()

clean_members["member_id"] = (
    patients["member_id"]
)

clean_members["first_name"] = (
    patients["FIRST"]
    .fillna("")
    .astype(str)
    .str.strip()
)

clean_members["last_name"] = (
    patients["LAST"]
    .fillna("")
    .astype(str)
    .str.strip()
)

# ============================================================
# DATES
# ============================================================

clean_members["date_of_birth"] = (
    pd.to_datetime(
        patients["BIRTHDATE"],
        errors="coerce"
    )
    .dt.strftime("%Y-%m-%d")
    .fillna("")
)

clean_members["death_date"] = (
    pd.to_datetime(
        patients["DEATHDATE"],
        errors="coerce"
    )
    .dt.strftime("%Y-%m-%d")
    .fillna("")
)

# ============================================================
# DEMOGRAPHICS
# ============================================================

clean_members["gender"] = (
    patients["GENDER"]
    .fillna("")
    .astype(str)
    .str.strip()
)

clean_members["marital_status"] = (
    patients["MARITAL"]
    .fillna("")
    .astype(str)
    .str.strip()
)

clean_members["birthplace"] = (
    patients["BIRTHPLACE"]
    .fillna("")
    .astype(str)
    .str.strip()
)

# ============================================================
# ADDRESS
# ============================================================

clean_members["address"] = (
    patients["ADDRESS"]
    .fillna("")
    .astype(str)
    .str.strip()
)

clean_members["city"] = (
    patients["CITY"]
    .fillna("")
    .astype(str)
    .str.strip()
)

clean_members["state"] = (
    patients["STATE"]
    .fillna("")
    .astype(str)
    .str.strip()
)

clean_members["county"] = (
    patients["COUNTY"]
    .fillna("")
    .astype(str)
    .str.strip()
)

clean_members["postal_code"] = (
    patients["ZIP"]
    .fillna("")
    .astype(str)
    .str.strip()
)

# ============================================================
# HEALTHCARE FINANCIAL INFORMATION
# ============================================================

clean_members["healthcare_expenses"] = (
    pd.to_numeric(
        patients["HEALTHCARE_EXPENSES"],
        errors="coerce"
    )
    .fillna(0)
    .round(2)
)

clean_members["healthcare_coverage"] = (
    pd.to_numeric(
        patients["HEALTHCARE_COVERAGE"],
        errors="coerce"
    )
    .fillna(0)
    .round(2)
)

# ============================================================
# CONTACT
# ============================================================

# Not available in this Synthea patients.csv
clean_members["phone"] = ""
clean_members["email"] = ""



# ============================================================
# SOURCE
# ============================================================

clean_members["source"] = "Synthetic"
# ============================================================
# CLEAN EMPTY VALUES
# ============================================================

clean_members = clean_members.fillna("")

# ============================================================
# VALIDATION
# ============================================================

print("\nMember Validation")

print(
    "Total members:",
    len(clean_members)
)

print(
    "Unique member IDs:",
    clean_members[
        "member_id"
    ].nunique()
)

# ============================================================
# MEMBER ID CHECK
# ============================================================

if clean_members[
    "member_id"
].duplicated().any():

    raise ValueError(
        "Duplicate member IDs found."
    )

# ============================================================
# REQUIRED FIELD CHECK
# ============================================================

required_columns = [
    "member_id",
    "first_name",
    "last_name",
    "date_of_birth"
]

for column in required_columns:

    if column not in clean_members.columns:

        raise ValueError(
            f"Missing required column: {column}"
        )

# ============================================================
# SAVE
# ============================================================

clean_members.to_csv(
    OUTPUT_FILE,
    index=False
)

print(
    f"\nCreated: {OUTPUT_FILE}"
)

print("\nFirst 10 members:")

print(
    clean_members
    .head(10)
    .to_string(index=False)
)