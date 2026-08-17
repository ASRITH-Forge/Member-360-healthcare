import pandas as pd
import random
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================

RAW_DIR = Path("data/raw/synthea")
PROCESSED_DIR = Path("data/processed")

PATIENTS_FILE = RAW_DIR / "patients.csv"
PAYERS_FILE = RAW_DIR / "payers.csv"

OUTPUT_FILE = PROCESSED_DIR / "eligibility.csv"

SEED = 42
random.seed(SEED)

AS_OF_DATE = pd.Timestamp("2026-08-13")

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

print(
    f"Patients: {len(patients)}"
)

# ============================================================
# LOAD PAYERS IF AVAILABLE
# ============================================================

if PAYERS_FILE.exists():

    payers = pd.read_csv(
        PAYERS_FILE
    )

    print(
        f"Payers: {len(payers)}"
    )

else:

    payers = None

    print(
        "payers.csv not found. "
        "Using synthetic payer names."
    )

# ============================================================
# MEMBER ID MAPPING
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
# PAYER NAMES
# ============================================================

synthetic_payers = [
    "HealthPlus",
    "CareFirst",
    "United Health Services",
    "Community Health Plan",
    "MediCare Plus",
    "Wellness Health",
    "Prime Health",
    "National Health Plan"
]

plan_types = [
    "Commercial",
    "Medicare",
    "Medicaid"
]

commercial_plans = [
    "HealthPlus Gold",
    "HealthPlus Silver",
    "CareFirst Standard",
    "Community Health Plan",
    "Prime Health Plus"
]

medicare_plans = [
    "Medicare Advantage",
    "Medicare Basic",
    "SeniorCare Advantage"
]

medicaid_plans = [
    "Medicaid Standard",
    "Medicaid Plus",
    "Community Medicaid"
]

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def choose_plan():

    plan_type = random.choices(
        plan_types,
        weights=[
            70,
            20,
            10
        ],
        k=1
    )[0]

    if plan_type == "Commercial":

        plan_name = random.choice(
            commercial_plans
        )

    elif plan_type == "Medicare":

        plan_name = random.choice(
            medicare_plans
        )

    else:

        plan_name = random.choice(
            medicaid_plans
        )

    return plan_type, plan_name


def choose_payer():

    if payers is not None:

        if "NAME" in payers.columns:

            available = (
                payers["NAME"]
                .dropna()
                .astype(str)
                .tolist()
            )

            if available:

                return random.choice(
                    available
                )

    return random.choice(
        synthetic_payers
    )


# ============================================================
# CREATE ELIGIBILITY RECORDS
# ============================================================

eligibility_records = []

for index, row in patients.iterrows():

    synthea_id = str(
        row["Id"]
    )

    member_id = member_mapping[
        synthea_id
    ]

    plan_type, plan_name = choose_plan()

    payer = choose_payer()

    # Generate coverage start
    effective_date = pd.Timestamp(
        "2026-01-01"
    )

    # Most members remain active
    # Some are terminated.

    status_roll = random.random()

    if status_roll < 0.82:

        status = "Active"

        termination_date = ""

    elif status_roll < 0.92:

        status = "Terminated"

        termination_date = (
            effective_date
            + pd.Timedelta(
                days=random.randint(
                    90,
                    210
                )
            )
        ).strftime(
            "%Y-%m-%d"
        )

    else:

        status = "Pending"

        termination_date = ""

    eligibility_records.append({

    "eligibility_id":
        f"ELG{10000 + index + 1}",

    "member_id":
        member_id,

    "payer_name":
        payer,

    "plan_name":
        plan_name,

    "plan_type":
        plan_type,

    "ownership":
        plan_type,

    "effective_date":
        effective_date.strftime(
            "%Y-%m-%d"
        ),

    "termination_date":
        termination_date,

    "status":
        status,

    "source":
        "Synthetic"
})

# ============================================================
# DATAFRAME
# ============================================================

eligibility = pd.DataFrame(
    eligibility_records
)

# ============================================================
# VALIDATION
# ============================================================

print("\nEligibility Validation")

print(
    "Total records:",
    len(eligibility)
)

print(
    "Unique members:",
    eligibility["member_id"].nunique()
)

print(
    "\nStatus distribution:"
)

print(
    eligibility["status"].value_counts()
)

print(
    "\nPlan type distribution:"
)

print(
    eligibility["plan_type"].value_counts()
)

# ============================================================
# MEMBER ID VALIDATION
# ============================================================

valid_member_ids = set(
    member_mapping.values()
)

invalid_members = eligibility[
    ~eligibility["member_id"].isin(
        valid_member_ids
    )
]

if len(invalid_members) > 0:

    raise ValueError(
        "Invalid member IDs found."
    )

# ============================================================
# DUPLICATE CHECK
# ============================================================

if eligibility[
    "eligibility_id"
].duplicated().any():

    raise ValueError(
        "Duplicate eligibility IDs found."
    )

# ============================================================
# SAVE
# ============================================================

eligibility.to_csv(
    OUTPUT_FILE,
    index=False
)

print(
    f"\nCreated: {OUTPUT_FILE}"
)

print(
    "\nFirst 10 records:"
)

print(
    eligibility.head(10)
    .to_string(index=False)
)