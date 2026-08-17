import pandas as pd
import random
from pathlib import Path
from datetime import datetime, timedelta

# ============================================================
# CONFIGURATION
# ============================================================

RAW_DIR = Path("data/raw/synthea")
OUTPUT_DIR = Path("data/processed")

PATIENTS_FILE = RAW_DIR / "patients.csv"
PROCEDURES_FILE = RAW_DIR / "procedures.csv"
ENCOUNTERS_FILE = RAW_DIR / "encounters.csv"

OUTPUT_FILE = OUTPUT_DIR / "authorizations.csv"

# Fixed seed = reproducible results
SEED = 42
random.seed(SEED)

# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# LOAD DATA
# ============================================================

print("Loading Synthea data...")

patients = pd.read_csv(PATIENTS_FILE)
procedures = pd.read_csv(PROCEDURES_FILE)
encounters = pd.read_csv(ENCOUNTERS_FILE)

print(f"Patients: {len(patients)}")
print(f"Procedures: {len(procedures)}")
print(f"Encounters: {len(encounters)}")

# ============================================================
# CREATE MEMBER ID MAPPING
# ============================================================

# Synthea patient UUID -> clean M10001 style ID

patients = patients.reset_index(drop=True)

member_mapping = {}

for index, row in patients.iterrows():
    synthea_id = str(row["Id"])
    clean_member_id = f"M{index + 1:05d}"

    member_mapping[synthea_id] = clean_member_id

print("\nExample member ID mappings:")

for old_id, new_id in list(member_mapping.items())[:5]:
    print(f"{old_id} -> {new_id}")

# ============================================================
# CLEAN PROCEDURE DATA
# ============================================================

# Only use procedures that have a valid patient ID

procedures["PATIENT"] = procedures["PATIENT"].astype(str)

procedures = procedures[
    procedures["PATIENT"].isin(member_mapping.keys())
].copy()

# ============================================================
# SERVICE GENERATION
# ============================================================

def create_service(row):

    description = str(
        row.get("DESCRIPTION", "")
    ).strip()

    reason = str(
        row.get("REASONDESCRIPTION", "")
    ).strip()

    text = f"{description} {reason}".lower()

    if "mri" in text:
        return "MRI"

    if "ct" in text or "computed tomography" in text:
        return "CT Scan"

    if "physical therapy" in text:
        return "Physical Therapy"

    if "cardiology" in text:
        return "Specialist Consultation - Cardiology"

    if "orthopedic" in text:
        return "Specialist Consultation - Orthopedics"

    if "surgery" in text:
        return "Surgical Procedure"

    if "dental" in text:
        return "Dental Service"

    if description:
        return description[:100]

    return random.choice([
        "Specialist Consultation",
        "Diagnostic Imaging",
        "Physical Therapy",
        "Outpatient Procedure"
    ])


# ============================================================
# DATE GENERATION
# ============================================================

# Generate dates within the previous 6 months.
# This makes the demo data look current while remaining synthetic.

TODAY = datetime(2026, 8, 13)

def generate_request_date():

    days_ago = random.randint(1, 180)

    date = TODAY - timedelta(days=days_ago)

    return date.strftime("%Y-%m-%d")


# ============================================================
# STATUS GENERATION
# ============================================================

def generate_status():

    value = random.random()

    if value < 0.20:
        return "Pending"

    elif value < 0.85:
        return "Approved"

    elif value < 0.95:
        return "Denied"

    else:
        return "Cancelled"


# ============================================================
# DECISION DATE
# ============================================================

def generate_decision_date(request_date, status):

    # Pending authorizations have no decision date

    if status == "Pending":
        return ""

    request = datetime.strptime(
        request_date,
        "%Y-%m-%d"
    )

    decision = request + timedelta(
        days=random.randint(1, 14)
    )

    return decision.strftime("%Y-%m-%d")


# ============================================================
# NOTES
# ============================================================

def generate_notes(service, status):

    if status == "Pending":
        return (
            f"Prior authorization request for {service} "
            "is awaiting review."
        )

    if status == "Approved":
        return (
            f"Prior authorization for {service} "
            "has been approved."
        )

    if status == "Denied":
        return (
            f"Prior authorization for {service} "
            "was not approved."
        )

    return (
        f"Prior authorization for {service} "
        "was cancelled."
    )


# ============================================================
# CREATE AUTHORIZATION RECORDS
# ============================================================

records = []

# Sample a manageable number of procedures.
# We don't need 35,000 authorization records.

sample_size = min(
    len(procedures),
    1200
)

selected_procedures = procedures.sample(
    n=sample_size,
    random_state=SEED
)

for index, (_, row) in enumerate(
    selected_procedures.iterrows(),
    start=1
):

    synthea_patient_id = str(
        row["PATIENT"]
    )

    member_id = member_mapping[
        synthea_patient_id
    ]

    service = create_service(row)

    request_date = generate_request_date()

    status = generate_status()

    decision_date = generate_decision_date(
        request_date,
        status
    )

    records.append({

        "authorization_id":
            f"AUTH{10000 + index}",

        "member_id":
            member_id,

        "service":
            service,

        "request_date":
            request_date,

        "status":
            status,

        "decision_date":
            decision_date,

        "source":
            "Synthetic",

        "notes":
            generate_notes(
                service,
                status
            )
    })


# ============================================================
# CREATE DATAFRAME
# ============================================================

authorizations = pd.DataFrame(records)

# ============================================================
# VALIDATION
# ============================================================

print("\nAuthorization validation:")

print(
    "Total records:",
    len(authorizations)
)

print(
    "Unique members:",
    authorizations["member_id"].nunique()
)

print(
    "\nStatus distribution:"
)

print(
    authorizations["status"].value_counts()
)

# Check required columns

required_columns = [
    "authorization_id",
    "member_id",
    "service",
    "request_date",
    "status",
    "decision_date",
    "source",
    "notes"
]

missing_columns = [
    column
    for column in required_columns
    if column not in authorizations.columns
]

if missing_columns:

    raise ValueError(
        f"Missing columns: {missing_columns}"
    )

# Check member IDs

invalid_members = authorizations[
    ~authorizations["member_id"].isin(
        member_mapping.values()
    )
]

if len(invalid_members) > 0:

    raise ValueError(
        "Some authorization records contain "
        "invalid member IDs."
    )

# ============================================================
# SAVE
# ============================================================

authorizations.to_csv(
    OUTPUT_FILE,
    index=False
)

print(
    f"\nCreated: {OUTPUT_FILE}"
)

print("\nFirst 5 records:")

print(
    authorizations.head().to_string(
        index=False
    )
)