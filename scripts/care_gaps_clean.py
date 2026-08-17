import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# ============================================================
# CONFIG
# ============================================================

RAW_DIR = Path("data/raw/synthea")
PROCESSED_DIR = Path("data/processed")

PATIENTS_FILE = RAW_DIR / "patients.csv"
ENCOUNTERS_FILE = RAW_DIR / "encounters.csv"
CONDITIONS_FILE = RAW_DIR / "conditions.csv"
OBSERVATIONS_FILE = RAW_DIR / "observations.csv"
IMMUNIZATIONS_FILE = RAW_DIR / "immunizations.csv"
CAREPLANS_FILE = RAW_DIR / "careplans.csv"

AUTHORIZATIONS_FILE = PROCESSED_DIR / "authorizations.csv"
INTERACTIONS_FILE = PROCESSED_DIR / "interactions.csv"

OUTPUT_FILE = PROCESSED_DIR / "care_gaps.csv"

# Use the same date as your current synthetic project data.
AS_OF_DATE = pd.Timestamp("2026-08-13", tz="UTC")
# ============================================================
# LOAD DATA
# ============================================================

print("Loading Synthea data...")

patients = pd.read_csv(PATIENTS_FILE)
encounters = pd.read_csv(ENCOUNTERS_FILE)
conditions = pd.read_csv(CONDITIONS_FILE)
observations = pd.read_csv(OBSERVATIONS_FILE)
immunizations = pd.read_csv(IMMUNIZATIONS_FILE)
careplans = pd.read_csv(CAREPLANS_FILE)

# Optional project-specific datasets
authorizations = pd.read_csv(AUTHORIZATIONS_FILE)
interactions = pd.read_csv(INTERACTIONS_FILE)

print("\nAuthorizations columns:")
print(authorizations.columns.tolist())

print("\nInteractions columns:")
print(interactions.columns.tolist())

print("\nDuplicate authorization columns:")
print(
    authorizations.columns[
        authorizations.columns.duplicated()
    ].tolist()
)

print("\nDuplicate interaction columns:")
print(
    interactions.columns[
        interactions.columns.duplicated()
    ].tolist()
)

print(f"Patients: {len(patients)}")
print(f"Encounters: {len(encounters)}")
print(f"Conditions: {len(conditions)}")
print(f"Observations: {len(observations)}")
print(f"Immunizations: {len(immunizations)}")
print(f"Care plans: {len(careplans)}")

# ============================================================
# CREATE COMMON MEMBER ID MAPPING
# ============================================================

patients = patients.reset_index(drop=True)

member_mapping = {}

for index, row in patients.iterrows():

    synthea_id = str(row["Id"])

    member_id = f"M{index + 1:05d}"

    member_mapping[synthea_id] = member_id

print("\nMember ID mapping created.")

# ============================================================
# NORMALIZE PATIENT COLUMNS
# ============================================================

encounters["PATIENT"] = encounters["PATIENT"].astype(str)
conditions["PATIENT"] = conditions["PATIENT"].astype(str)
observations["PATIENT"] = observations["PATIENT"].astype(str)
immunizations["PATIENT"] = immunizations["PATIENT"].astype(str)
careplans["PATIENT"] = careplans["PATIENT"].astype(str)

# ============================================================
# DATE NORMALIZATION
# ============================================================

encounters["START"] = pd.to_datetime(
    encounters["START"],
    errors="coerce",
    utc=True
)

conditions["START"] = pd.to_datetime(
    conditions["START"],
    errors="coerce",
    utc=True
)

conditions["STOP"] = pd.to_datetime(
    conditions["STOP"],
    errors="coerce",
    utc=True
)

observations["DATE"] = pd.to_datetime(
    observations["DATE"],
    errors="coerce",
    utc=True
)

immunizations["DATE"] = pd.to_datetime(
    immunizations["DATE"],
    errors="coerce",
    utc=True
)

careplans["START"] = pd.to_datetime(
    careplans["START"],
    errors="coerce",
    utc=True
)

careplans["STOP"] = pd.to_datetime(
    careplans["STOP"],
    errors="coerce",
    utc=True
)

# ============================================================
# HELPER
# ============================================================

def member_id_from_patient(patient_id):

    return member_mapping.get(str(patient_id))


def create_gap_id(number):

    return f"GAP{10000 + number}"


def add_gap(
    records,
    member_id,
    gap_type,
    description,
    status,
    due_date,
    source_type,
    source_id
):

    records.append({
        "member_id": member_id,
        "gap_type": gap_type,
        "description": description,
        "status": status,
        "due_date": due_date,
        "source_type": source_type,
        "source_id": source_id
    })


gap_records = []

# ============================================================
# RULE 1: PREVENTIVE WELLNESS RECORD GAP
# ============================================================

print("\nChecking preventive care gaps...")

preventive_cutoff = AS_OF_DATE - pd.Timedelta(days=365)

wellness_encounters = encounters[
    encounters["ENCOUNTERCLASS"]
    .astype(str)
    .str.lower()
    .eq("wellness")
]

recent_wellness = wellness_encounters[
    wellness_encounters["START"] >= preventive_cutoff
]

members_with_recent_wellness = set(
    recent_wellness["PATIENT"].dropna().astype(str)
)

for patient_uuid in member_mapping:

    member_id = member_mapping[patient_uuid]

    if patient_uuid not in members_with_recent_wellness:

        add_gap(
            gap_records,
            member_id,
            "Preventive Care Record Gap",
            "Expected preventive wellness encounter record "
            "not found in the defined period.",
            "Open",
            "2026-09-15",
            "dataset_audit",
            f"AUDIT-PREV-{member_id}"
        )

# ============================================================
# RULE 2: INFLUENZA IMMUNIZATION RECORD GAP
# ============================================================

print("Checking immunization gaps...")

immunization_cutoff = AS_OF_DATE - pd.Timedelta(days=365)

# Search DESCRIPTION for influenza/flu.
influenza_records = immunizations[
    immunizations["DESCRIPTION"]
    .astype(str)
    .str.lower()
    .str.contains(
        "influenza|flu",
        regex=True,
        na=False
    )
]

recent_influenza = influenza_records[
    influenza_records["DATE"] >= immunization_cutoff
]

members_with_recent_flu = set(
    recent_influenza["PATIENT"]
    .dropna()
    .astype(str)
)

for patient_uuid in member_mapping:

    member_id = member_mapping[patient_uuid]

    if patient_uuid not in members_with_recent_flu:

        add_gap(
            gap_records,
            member_id,
            "Immunization Record Gap",
            "No seasonal influenza immunization record "
            "was found in the defined period.",
            "Open",
            "2026-10-01",
            "dataset_audit",
            f"AUDIT-FLU-{member_id}"
        )

# ============================================================
# RULE 3: CONDITION MONITORING RECORD GAP
# ============================================================

print("Checking condition monitoring gaps...")

condition_cutoff = AS_OF_DATE - pd.Timedelta(days=180)

# Conditions that we can safely recognize as documented
# conditions from Synthea.

condition_keywords = [
    "hypertension",
    "diabetes",
    "high blood pressure"
]

monitoring_keywords = [
    "blood pressure",
    "hemoglobin a1c",
    "hba1c",
    "a1c"
]

recent_observations = observations[
    observations["DATE"] >= condition_cutoff
].copy()

# ============================================================
# CREATE SEARCHABLE OBSERVATION TEXT
# ============================================================

observation_text_parts = []

for column in ["DESCRIPTION", "CODE", "VALUE", "UNITS"]:

    if column in recent_observations.columns:

        observation_text_parts.append(
            recent_observations[column]
            .fillna("")
            .astype(str)
            .reset_index(drop=True)
        )

if observation_text_parts:

    obs_text = observation_text_parts[0]

    for part in observation_text_parts[1:]:
        obs_text = obs_text + " " + part

    recent_observations["OBS_TEXT"] = (
        obs_text
        .str.strip()
        .str.lower()
    )

else:

    recent_observations["OBS_TEXT"] = ""

for _, condition in conditions.iterrows():

    patient_uuid = str(condition["PATIENT"])

    if patient_uuid not in member_mapping:
        continue

    condition_start = condition["START"]

    condition_stop = condition["STOP"]

    # Determine whether condition is currently active
    condition_active = (
        pd.isna(condition_stop)
        or condition_stop >= AS_OF_DATE
    )

    if not condition_active:
        continue

    condition_text = str(
        condition.get("DESCRIPTION", "")
    ).lower()

    matched_condition = None

    for keyword in condition_keywords:

        if keyword in condition_text:

            matched_condition = keyword

            break

    if not matched_condition:
        continue

    patient_observations = recent_observations[
        recent_observations["PATIENT"] == patient_uuid
    ]

    monitoring_found = False

    for _, observation in patient_observations.iterrows():

        observation_text = str(
            observation["OBS_TEXT"]
        ).lower()

        if any(
            keyword in observation_text
            for keyword in monitoring_keywords
        ):
            monitoring_found = True
            break

    if not monitoring_found:

        member_id = member_mapping[
            patient_uuid
        ]

        source_id = str(
            condition.get("ENCOUNTER", "")
        )

        if not source_id:
            source_id = "CONDITION-AUDIT"

        add_gap(
            gap_records,
            member_id,
            "Condition Monitoring Record Gap",
            "No recent monitoring observation was found "
            "for the documented condition in the defined period.",
            "Open",
            "2026-09-20",
            "condition",
            source_id
        )

# ============================================================
# RULE 4: ACTIVE CARE PLAN REVIEW GAP
# ============================================================

print("Checking care plan review gaps...")

careplan_cutoff = AS_OF_DATE - pd.Timedelta(days=180)

recent_encounters = encounters[
    encounters["START"] >= careplan_cutoff
]

recent_encounter_members = set(
    recent_encounters["PATIENT"]
    .dropna()
    .astype(str)
)

for _, careplan in careplans.iterrows():

    patient_uuid = str(
        careplan["PATIENT"]
    )

    if patient_uuid not in member_mapping:
        continue

    stop_date = careplan["STOP"]

    # Active care plan
    active_plan = (
        pd.isna(stop_date)
        or stop_date >= AS_OF_DATE
    )

    if not active_plan:
        continue

    if patient_uuid not in recent_encounter_members:

        member_id = member_mapping[
            patient_uuid
        ]

        source_id = str(
            careplan.get("Id", "")
        )

        add_gap(
            gap_records,
            member_id,
            "Care Plan Review Gap",
            "Active care plan has no recent encounter "
            "record in the defined period.",
            "Open",
            "2026-09-25",
            "careplan",
            source_id
        )

# ============================================================
# CREATE DATAFRAME
# ============================================================

care_gaps = pd.DataFrame(gap_records)

# Remove duplicates
care_gaps = care_gaps.drop_duplicates(
    subset=[
        "member_id",
        "gap_type"
    ]
)

# ============================================================
# ADD GAP IDs
# ============================================================

care_gaps.insert(
    0,
    "gap_id",
    [
        create_gap_id(i)
        for i in range(
            1,
            len(care_gaps) + 1
        )
    ]
)

# ============================================================
# ADD RELATED AUTHORIZATION
# ============================================================

# Find the status column safely
auth_status_index = None

for i, column in enumerate(authorizations.columns):
    if str(column).strip().lower() == "status":
        auth_status_index = i
        break

if auth_status_index is None:
    raise ValueError(
        "Could not find 'status' column in authorizations.csv"
    )

# iloc[:, index] ALWAYS returns a Series
authorization_status = (
    authorizations.iloc[:, auth_status_index]
    .fillna("")
    .map(lambda value: str(value).strip().lower())
)

pending_auth = authorizations[
    authorization_status == "pending"
].copy()

pending_auth_by_member = (
    pending_auth
    .groupby("member_id")["authorization_id"]
    .first()
    .to_dict()
)

care_gaps["related_authorization_id"] = (
    care_gaps["member_id"]
    .map(pending_auth_by_member)
    .fillna("")
)

# ============================================================
# ADD RELATED INTERACTION
# ============================================================

# Find the status column safely
interaction_status_index = None

for i, column in enumerate(interactions.columns):
    if str(column).strip().lower() == "status":
        interaction_status_index = i
        break

if interaction_status_index is None:
    raise ValueError(
        "Could not find 'status' column in interactions.csv"
    )

# iloc[:, index] ALWAYS returns a Series
interaction_status = (
    interactions.iloc[:, interaction_status_index]
    .fillna("")
    .map(lambda value: str(value).strip().lower())
)

open_interactions = interactions[
    interaction_status.isin([
        "open",
        "in progress"
    ])
].copy()

open_interaction_by_member = (
    open_interactions
    .groupby("member_id")["interaction_id"]
    .first()
    .to_dict()
)

care_gaps["related_interaction_id"] = (
    care_gaps["member_id"]
    .map(open_interaction_by_member)
    .fillna("")
)

# ============================================================
# VALIDATION
# ============================================================

print("\nCare Gap Validation")

print(
    "Total care gaps:",
    len(care_gaps)
)

print(
    "Unique members:",
    care_gaps["member_id"].nunique()
)

print(
    "\nGap types:"
)

print(
    care_gaps["gap_type"].value_counts()
)

# Validate member IDs
valid_member_ids = set(
    member_mapping.values()
)

invalid_members = care_gaps[
    ~care_gaps["member_id"].isin(
        valid_member_ids
    )
]

if len(invalid_members) > 0:

    raise ValueError(
        "Invalid member IDs found."
    )

# ============================================================
# SAVE
# ============================================================

columns = [
    "gap_id",
    "member_id",
    "gap_type",
    "description",
    "status",
    "due_date",
    "source_type",
    "source_id",
    "related_authorization_id",
    "related_interaction_id"
]

care_gaps = care_gaps[columns]

care_gaps.to_csv(
    OUTPUT_FILE,
    index=False
)

print(
    f"\nCreated: {OUTPUT_FILE}"
)

print("\nFirst 10 records:")

print(
    care_gaps.head(10).to_string(
        index=False
    )
)