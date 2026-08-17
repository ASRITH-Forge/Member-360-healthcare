import pandas as pd
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================

RAW_DIR = Path("data/raw/synthea")
PROCESSED_DIR = Path("data/processed")

PATIENTS_FILE = RAW_DIR / "patients.csv"
MEDICATIONS_FILE = RAW_DIR / "medications.csv"

OUTPUT_FILE = PROCESSED_DIR / "medications.csv"

AS_OF_DATE = pd.Timestamp("2026-08-13", tz="UTC")

# ============================================================
# LOAD DATA
# ============================================================

print("Loading Synthea medication data...")

patients = pd.read_csv(PATIENTS_FILE)
medications = pd.read_csv(MEDICATIONS_FILE)

print(f"Patients: {len(patients)}")
print(f"Medications: {len(medications)}")

print("\nMedication columns:")
print(medications.columns.tolist())

# ============================================================
# CREATE MEMBER ID MAPPING
# ============================================================

patients = patients.reset_index(drop=True)

member_mapping = {}

for index, row in patients.iterrows():

    synthea_id = str(row["Id"])

    member_id = f"M{index + 1:05d}"

    member_mapping[synthea_id] = member_id

print("\nExample member ID mappings:")

for synthea_id, member_id in list(
    member_mapping.items()
)[:5]:

    print(
        f"{synthea_id} -> {member_id}"
    )

# ============================================================
# NORMALIZE PATIENT ID
# ============================================================

medications["PATIENT"] = (
    medications["PATIENT"]
    .astype(str)
    .str.strip()
)

# ============================================================
# DATE NORMALIZATION
# ============================================================

medications["START"] = pd.to_datetime(
    medications["START"],
    errors="coerce",
    utc=True
)

medications["STOP"] = pd.to_datetime(
    medications["STOP"],
    errors="coerce",
    utc=True
)

# ============================================================
# REMOVE INVALID RECORDS
# ============================================================

medications = medications[
    medications["PATIENT"].isin(
        member_mapping.keys()
    )
].copy()

medications = medications[
    medications["START"].notna()
].copy()

print(
    f"\nValid medication records: "
    f"{len(medications)}"
)

# ============================================================
# CREATE MEMBER ID
# ============================================================

medications["member_id"] = (
    medications["PATIENT"]
    .map(member_mapping)
)

# ============================================================
# MEDICATION STATUS
# ============================================================

def determine_status(row):

    stop_date = row["STOP"]

    # No stop date = currently active
    if pd.isna(stop_date):

        return "Active"

    # Future stop date = still active
    if stop_date >= AS_OF_DATE:

        return "Active"

    # Historical medication
    return "Completed"


medications["status"] = (
    medications.apply(
        determine_status,
        axis=1
    )
)

# ============================================================
# MEDICATION ID
# ============================================================

medications = medications.reset_index(
    drop=True
)

medications.insert(
    0,
    "medication_id",
    [
        f"MED{10000 + i}"
        for i in range(
            1,
            len(medications) + 1
        )
    ]
)

# ============================================================
# CLEAN REASON
# ============================================================

medications["reason"] = (
    medications["REASONDESCRIPTION"]
    .fillna("")
    .astype(str)
    .str.strip()
)

# If reason is missing
medications.loc[
    medications["reason"].isin(
        ["", "nan", "None"]
    ),
    "reason"
] = "Maintenance Therapy"

# ============================================================
# DISPENSES
# ============================================================

medications["dispenses"] = (
    pd.to_numeric(
        medications["DISPENSES"],
        errors="coerce"
    )
    .fillna(0)
)

# ============================================================
# TOTAL COST
# ============================================================

medications["total_cost"] = (
    pd.to_numeric(
        medications["TOTALCOST"],
        errors="coerce"
    )
    .fillna(0)
)

# ============================================================
# CODE
# ============================================================

medications["code"] = (
    medications["CODE"]
    .fillna("")
    .astype(str)
    .str.strip()
)

# ============================================================
# MEDICATION NAME
# ============================================================

medications["medication_name"] = (
    medications["DESCRIPTION"]
    .fillna("")
    .astype(str)
    .str.strip()
)

# Remove empty medication names

medications = medications[
    medications["medication_name"]
    .ne("")
].copy()

# ============================================================
# DATE FORMAT
# ============================================================

medications["start_date"] = (
    medications["START"]
    .dt.strftime("%Y-%m-%d")
)

medications["end_date"] = (
    medications["STOP"]
    .dt.strftime("%Y-%m-%d")
)

medications["end_date"] = (
    medications["end_date"]
    .fillna("")
)

# ============================================================
# SOURCE TRACEABILITY
# ============================================================

medications["source_type"] = "medication"

# Prefer encounter ID for traceability
medications["source_id"] = (
    medications["ENCOUNTER"]
    .fillna("")
    .astype(str)
    .str.strip()
)

# If encounter is missing, use medication index
missing_source = (
    medications["source_id"]
    .isin(["", "nan", "None"])
)

medications.loc[
    missing_source,
    "source_id"
] = medications.loc[
    missing_source,
    "medication_id"
]

# ============================================================
# FINAL COLUMNS
# ============================================================

clean_medications = medications[
    [
        "medication_id",
        "member_id",
        "medication_name",
        "code",
        "start_date",
        "end_date",
        "reason",
        "dispenses",
        "total_cost",
        "status",
        "source_type",
        "source_id"
    ]
].copy()

# ============================================================
# CLEAN TEXT
# ============================================================

text_columns = [
    "medication_id",
    "member_id",
    "medication_name",
    "code",
    "start_date",
    "end_date",
    "reason",
    "status",
    "source_type",
    "source_id"
]

for column in text_columns:

    clean_medications[column] = (
        clean_medications[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

# ============================================================
# ROUND COST
# ============================================================

clean_medications["total_cost"] = (
    pd.to_numeric(
        clean_medications["total_cost"],
        errors="coerce"
    )
    .fillna(0)
    .round(2)
)

# ============================================================
# VALIDATION
# ============================================================

print("\nMedication Validation")

print(
    "Total records:",
    len(clean_medications)
)

print(
    "Unique members:",
    clean_medications[
        "member_id"
    ].nunique()
)

print("\nStatus distribution:")

print(
    clean_medications[
        "status"
    ].value_counts()
)

print("\nActive medications:")

print(
    (
        clean_medications["status"]
        == "Active"
    ).sum()
)

# ============================================================
# MEMBER VALIDATION
# ============================================================

valid_member_ids = set(
    member_mapping.values()
)

invalid_members = clean_medications[
    ~clean_medications["member_id"]
    .isin(valid_member_ids)
]

if len(invalid_members) > 0:

    raise ValueError(
        "Invalid member IDs found."
    )

# ============================================================
# DUPLICATE ID VALIDATION
# ============================================================

if clean_medications[
    "medication_id"
].duplicated().any():

    raise ValueError(
        "Duplicate medication IDs found."
    )

# ============================================================
# SAVE
# ============================================================

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)

clean_medications.to_csv(
    OUTPUT_FILE,
    index=False
)

print(
    f"\nCreated: {OUTPUT_FILE}"
)

print("\nFirst 10 records:")

print(
    clean_medications
    .head(10)
    .to_string(index=False)
)