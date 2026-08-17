import pandas as pd
import random
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================

RAW_DIR = Path("data/raw/synthea")
PROCESSED_DIR = Path("data/processed")

PATIENTS_FILE = RAW_DIR / "patients.csv"
ENCOUNTERS_FILE = RAW_DIR / "encounters.csv"
PROCEDURES_FILE = RAW_DIR / "procedures.csv"

# Optional Synthea organization file
ORGANIZATIONS_FILE = RAW_DIR / "organizations.csv"

OUTPUT_FILE = PROCESSED_DIR / "claims.csv"

# Reproducible data generation
SEED = 42
random.seed(SEED)

# Maximum number of claims
MAX_CLAIMS = 8000

# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# ============================================================
# LOAD DATA
# ============================================================

print("Loading Synthea data...")

patients = pd.read_csv(
    PATIENTS_FILE
)

encounters = pd.read_csv(
    ENCOUNTERS_FILE
)

procedures = pd.read_csv(
    PROCEDURES_FILE
)

print(f"Patients: {len(patients)}")
print(f"Encounters: {len(encounters)}")
print(f"Procedures: {len(procedures)}")

# ============================================================
# OPTIONAL ORGANIZATIONS
# ============================================================

organizations = None

if ORGANIZATIONS_FILE.exists():

    organizations = pd.read_csv(
        ORGANIZATIONS_FILE
    )

    print(
        f"Organizations: {len(organizations)}"
    )

else:

    print(
        "organizations.csv not found. "
        "Provider names will be generated."
    )

# ============================================================
# CREATE COMMON MEMBER ID MAPPING
# ============================================================

patients = patients.reset_index(
    drop=True
)

member_mapping = {}

for index, row in patients.iterrows():

    synthea_id = str(
        row["Id"]
    )

    member_id = f"M{index + 1:05d}"

    member_mapping[
        synthea_id
    ] = member_id

print("\nExample member mappings:")

for old_id, new_id in list(
    member_mapping.items()
)[:5]:

    print(
        f"{old_id} -> {new_id}"
    )

# ============================================================
# NORMALIZE PATIENT IDs
# ============================================================

encounters["PATIENT"] = (
    encounters["PATIENT"]
    .astype(str)
)

procedures["PATIENT"] = (
    procedures["PATIENT"]
    .astype(str)
)

# ============================================================
# NORMALIZE DATES
# ============================================================

encounters["START"] = pd.to_datetime(
    encounters["START"],
    errors="coerce",
    utc=True
)

procedures["DATE"] = pd.to_datetime(
    procedures["DATE"],
    errors="coerce",
    utc=True
)

# Remove invalid dates

encounters = encounters[
    encounters["START"].notna()
].copy()

procedures = procedures[
    procedures["DATE"].notna()
].copy()

# ============================================================
# CREATE SERVICE NAME
# ============================================================

def classify_service(description):

    text = str(
        description
    ).strip().lower()

    if not text or text == "nan":
        return "General Medical Service"

    if any(
        word in text
        for word in [
            "mri",
            "magnetic resonance"
        ]
    ):
        return "MRI"

    if any(
        word in text
        for word in [
            "ct scan",
            "computed tomography"
        ]
    ):
        return "CT Scan"

    if any(
        word in text
        for word in [
            "x-ray",
            "xray",
            "radiograph"
        ]
    ):
        return "X-Ray"

    if any(
        word in text
        for word in [
            "ultrasound",
            "sonography"
        ]
    ):
        return "Ultrasound"

    if any(
        word in text
        for word in [
            "physical therapy",
            "physiotherapy"
        ]
    ):
        return "Physical Therapy"

    if any(
        word in text
        for word in [
            "surgery",
            "surgical"
        ]
    ):
        return "Surgical Procedure"

    if any(
        word in text
        for word in [
            "consultation",
            "consult"
        ]
    ):
        return "Specialist Consultation"

    if any(
        word in text
        for word in [
            "examination",
            "exam"
        ]
    ):
        return "Clinical Examination"

    if any(
        word in text
        for word in [
            "blood",
            "hemoglobin",
            "hematocrit",
            "platelet",
            "culture",
            "antibody",
            "laboratory"
        ]
    ):
        return "Laboratory Test"

    if any(
        word in text
        for word in [
            "medication",
            "drug",
            "prescription"
        ]
    ):
        return "Medication Service"

    if any(
        word in text
        for word in [
            "dental",
            "tooth"
        ]
    ):
        return "Dental Service"

    return "Outpatient Procedure"


# ============================================================
# CLAIM TYPE
# ============================================================

def classify_claim_type(
    encounter_class
):

    value = str(
        encounter_class
    ).strip().lower()

    mapping = {

        "inpatient":
            "Inpatient",

        "outpatient":
            "Outpatient",

        "ambulatory":
            "Outpatient",

        "emergency":
            "Emergency",

        "urgentcare":
            "Urgent Care",

        "urgent care":
            "Urgent Care",

        "wellness":
            "Preventive Care",

        "home":
            "Home Care",

        "hospice":
            "Hospice",

        "virtual":
            "Telehealth"
    }

    return mapping.get(
        value,
        "Outpatient"
    )


# ============================================================
# ESTIMATE CLAIM AMOUNT
# ============================================================

def estimate_amount(
    claim_type,
    service
):

    # Base ranges are synthetic demo values.
    # They are NOT real healthcare prices.

    service_lower = str(
        service
    ).lower()

    if service_lower == "mri":
        return round(
            random.uniform(
                700,
                1800
            ),
            2
        )

    if service_lower == "ct scan":
        return round(
            random.uniform(
                500,
                1400
            ),
            2
        )

    if service_lower == "x-ray":
        return round(
            random.uniform(
                80,
                350
            ),
            2
        )

    if service_lower == "ultrasound":
        return round(
            random.uniform(
                150,
                600
            ),
            2
        )

    if service_lower == "surgical procedure":
        return round(
            random.uniform(
                2000,
                10000
            ),
            2
        )

    if service_lower == "laboratory test":
        return round(
            random.uniform(
                30,
                300
            ),
            2
        )

    if service_lower == "physical therapy":
        return round(
            random.uniform(
                100,
                400
            ),
            2
        )

    if claim_type == "Emergency":
        return round(
            random.uniform(
                500,
                5000
            ),
            2
        )

    if claim_type == "Inpatient":
        return round(
            random.uniform(
                1500,
                8000
            ),
            2
        )

    if claim_type == "Telehealth":
        return round(
            random.uniform(
                50,
                200
            ),
            2
        )

    return round(
        random.uniform(
            100,
            800
        ),
        2
    )


# ============================================================
# CLAIM STATUS
# ============================================================

def generate_status():

    value = random.random()

    if value < 0.78:
        return "Approved"

    if value < 0.90:
        return "Pending"

    if value < 0.97:
        return "Denied"

    return "Rejected"


# ============================================================
# PROVIDER NAME
# ============================================================

provider_names = [
    "City Medical Center",
    "Community Health Clinic",
    "Central Hospital",
    "Metro Healthcare",
    "Riverside Medical Center",
    "Family Care Clinic",
    "Northside Health Center",
    "Regional Medical Group",
    "Downtown Medical Center",
    "Lakeside Healthcare"
]


def get_provider_name(
    encounter_row
):

    # Try to use organization information
    # when available.

    if (
        organizations is not None
        and "ORGANIZATION" in encounter_row.index
    ):

        organization_id = str(
            encounter_row["ORGANIZATION"]
        )

        if organization_id != "nan":

            if "Id" in organizations.columns:

                matches = organizations[
                    organizations["Id"].astype(str)
                    == organization_id
                ]

                if len(matches) > 0:

                    if "NAME" in matches.columns:

                        name = str(
                            matches.iloc[0]["NAME"]
                        )

                        if (
                            name
                            and name.lower()
                            != "nan"
                        ):
                            return name

    return random.choice(
        provider_names
    )


# ============================================================
# CREATE PROCEDURE LOOKUP
# ============================================================

# One or more procedures can belong to
# the same encounter.

procedure_lookup = {}

for _, row in procedures.iterrows():

    encounter_id = str(
        row.get(
            "ENCOUNTER",
            ""
        )
    )

    if not encounter_id:
        continue

    description = str(
        row.get(
            "DESCRIPTION",
            ""
        )
    )

    if description == "nan":
        continue

    procedure_lookup.setdefault(
        encounter_id,
        []
    ).append(
        description
    )

# ============================================================
# CREATE CLAIM CANDIDATES
# ============================================================

claim_candidates = []

for _, encounter in encounters.iterrows():

    patient_uuid = str(
        encounter["PATIENT"]
    )

    # Only process patients that
    # exist in our mapping.

    if patient_uuid not in member_mapping:
        continue

    encounter_id = str(
        encounter.get(
            "Id",
            ""
        )
    )

    encounter_class = encounter.get(
        "ENCOUNTERCLASS",
        "outpatient"
    )

    claim_type = classify_claim_type(
        encounter_class
    )

    # Get procedures for this encounter

    encounter_procedures = (
        procedure_lookup.get(
            encounter_id,
            []
        )
    )

    if encounter_procedures:

        # Create one claim per procedure

        for procedure_description in encounter_procedures:

            service = classify_service(
                procedure_description
            )

            claim_candidates.append({
                "patient_uuid":
                    patient_uuid,

                "claim_date":
                    encounter["START"],

                "claim_type":
                    claim_type,

                "service":
                    service,

                "provider":
                    get_provider_name(
                        encounter
                    ),

                "amount":
                    estimate_amount(
                        claim_type,
                        service
                    )
            })

    else:

        # Encounters without procedures
        # still produce a general claim.

        service_map = {

            "Emergency":
                "Emergency Visit",

            "Inpatient":
                "Inpatient Care",

            "Urgent Care":
                "Urgent Care Visit",

            "Preventive Care":
                "Wellness Visit",

            "Telehealth":
                "Telehealth Consultation",

            "Home Care":
                "Home Healthcare",

            "Hospice":
                "Hospice Care"
        }

        service = service_map.get(
            claim_type,
            "General Medical Service"
        )

        claim_candidates.append({
            "patient_uuid":
                patient_uuid,

            "claim_date":
                encounter["START"],

            "claim_type":
                claim_type,

            "service":
                service,

            "provider":
                get_provider_name(
                    encounter
                ),

            "amount":
                estimate_amount(
                    claim_type,
                    service
                )
        })


# ============================================================
# CREATE DATAFRAME
# ============================================================

claims = pd.DataFrame(
    claim_candidates
)

print(
    f"\nClaim candidates generated: "
    f"{len(claims)}"
)

# ============================================================
# LIMIT CLAIM COUNT
# ============================================================

if len(claims) > MAX_CLAIMS:

    claims = claims.sample(
        n=MAX_CLAIMS,
        random_state=SEED
    ).copy()

print(
    f"Claims selected: {len(claims)}"
)

# ============================================================
# CONVERT MEMBER IDs
# ============================================================

claims["member_id"] = (
    claims["patient_uuid"]
    .map(member_mapping)
)

# ============================================================
# GENERATE CLAIM IDs
# ============================================================

claims = claims.reset_index(
    drop=True
)

claims.insert(
    0,
    "claim_id",
    [
        f"CLM{10000 + i}"
        for i in range(
            1,
            len(claims) + 1
        )
    ]
)

# ============================================================
# CLAIM DATE
# ============================================================

claims["claim_date"] = (
    claims["claim_date"]
    .dt.strftime(
        "%Y-%m-%d"
    )
)

# ============================================================
# GENERATE STATUS
# ============================================================

claims["status"] = [
    generate_status()
    for _ in range(
        len(claims)
    )
]

# ============================================================
# SOURCE
# ============================================================

claims["source"] = "Synthetic"


# ============================================================
# CLEAN VALUES
# ============================================================

claims["member_id"] = (
    claims["member_id"]
    .astype(str)
    .str.strip()
)

claims["provider"] = (
    claims["provider"]
    .astype(str)
    .str.strip()
)

claims["service"] = (
    claims["service"]
    .astype(str)
    .str.strip()
)

claims["amount"] = (
    pd.to_numeric(
        claims["amount"],
        errors="coerce"
    )
    .fillna(0)
    .round(2)
)
# ============================================================
# PAYER COVERAGE
# ============================================================

claims["payer_coverage"] = (
    claims["amount"]
    * pd.Series(
        [
            random.uniform(0.70, 0.95)
            for _ in range(len(claims))
        ],
        index=claims.index
    )
).round(2)

# ============================================================
# MEMBER COPAY
# ============================================================

claims["member_copay"] = (
    claims["amount"]
    - claims["payer_coverage"]
).clip(lower=0).round(2)
# ============================================================
# SELECT FINAL COLUMNS
# ============================================================

claims = claims[
    [
        "claim_id",
        "member_id",
        "claim_date",
        "claim_type",
        "provider",
        "service",
        "amount",
        "payer_coverage",
        "member_copay",
        "status",
        "source"
    ]
]
# ============================================================
# VALIDATION
# ============================================================

print("\nClaim Validation")
print(
    "Total claims:",
    len(claims)
)

print(
    "Unique members:",
    claims["member_id"].nunique()
)

print(
    "\nClaim types:"
)

print(
    claims["claim_type"]
    .value_counts()
)

print(
    "\nClaim statuses:"
)

print(
    claims["status"]
    .value_counts()
)

# ============================================================
# VALIDATE MEMBER IDs
# ============================================================

valid_member_ids = set(
    member_mapping.values()
)

invalid_members = claims[
    ~claims["member_id"].isin(
        valid_member_ids
    )
]

if len(invalid_members) > 0:

    raise ValueError(
        "Invalid member IDs found in claims."
    )

# ============================================================
# CHECK DUPLICATE CLAIM IDs
# ============================================================

if claims["claim_id"].duplicated().any():

    raise ValueError(
        "Duplicate claim IDs found."
    )

# ============================================================
# SAVE
# ============================================================

claims.to_csv(
    OUTPUT_FILE,
    index=False
)

print(
    f"\nCreated: {OUTPUT_FILE}"
)

print(
    "\nFirst 10 claims:"
)

print(
    claims.head(10).to_string(
        index=False
    )
)