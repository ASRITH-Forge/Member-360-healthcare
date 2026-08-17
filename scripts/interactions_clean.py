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

# Use existing processed datasets when available
AUTHORIZATIONS_FILE = PROCESSED_DIR / "authorizations.csv"
CARE_GAPS_FILE = PROCESSED_DIR / "care_gaps.csv"

OUTPUT_FILE = PROCESSED_DIR / "interactions.csv"

SEED = 42
random.seed(SEED)

MAX_INTERACTIONS = 5000

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

print(
    f"Patients: {len(patients)}"
)

print(
    f"Encounters: {len(encounters)}"
)

# ============================================================
# LOAD OPTIONAL PROJECT DATA
# ============================================================

authorizations = None
care_gaps = None

if AUTHORIZATIONS_FILE.exists():

    authorizations = pd.read_csv(
        AUTHORIZATIONS_FILE
    )

    print(
        f"Authorizations: {len(authorizations)}"
    )

if CARE_GAPS_FILE.exists():

    care_gaps = pd.read_csv(
        CARE_GAPS_FILE
    )

    print(
        f"Care gaps: {len(care_gaps)}"
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
# NORMALIZE ENCOUNTERS
# ============================================================

encounters["PATIENT"] = (
    encounters["PATIENT"]
    .astype(str)
)

encounters["START"] = pd.to_datetime(
    encounters["START"],
    errors="coerce",
    utc=True
)

encounters = encounters[
    encounters["START"].notna()
].copy()

# ============================================================
# INTERACTION CHANNELS
# ============================================================

channels = [
    "Phone",
    "Email",
    "Portal Message",
    "In Person"
]

# ============================================================
# REASONS
# ============================================================

general_reasons = [
    "Care Coordination",
    "Clinical Follow-up",
    "Appointment Follow-up",
    "Member Support",
    "Preventive Care Outreach"
]

# ============================================================
# CREATE INTERACTION SUMMARY
# ============================================================

def create_summary(
    reason,
    channel,
    encounter_type
):

    if reason == "Authorization Follow-up":

        return (
            "Follow-up regarding a pending "
            "authorization request."
        )

    if reason == "Care Gap Outreach":

        return (
            "Member contacted regarding "
            "an outstanding care gap."
        )

    if reason == "Medication Follow-up":

        return (
            "Follow-up interaction related "
            "to medication management."
        )

    if reason == "Appointment Follow-up":

        return (
            "Follow-up regarding a recent "
            "healthcare appointment."
        )

    if reason == "Preventive Care Outreach":

        return (
            "Member contacted regarding "
            "preventive care activity."
        )

    if reason == "Clinical Follow-up":

        return (
            "Follow-up interaction related "
            "to recent healthcare activity."
        )

    return (
        f"{reason} interaction conducted "
        f"through {channel.lower()}."
    )


# ============================================================
# CREATE GENERAL INTERACTIONS FROM ENCOUNTERS
# ============================================================

interaction_records = []

for _, encounter in encounters.iterrows():

    patient_uuid = str(
        encounter["PATIENT"]
    )

    if patient_uuid not in member_mapping:
        continue

    encounter_class = str(
        encounter.get(
            "ENCOUNTERCLASS",
            ""
        )
    ).strip().lower()

    # Select a subset rather than turning
    # every encounter into an interaction.

    if random.random() > 0.08:
        continue

    if encounter_class == "emergency":

        reason = "Clinical Follow-up"

    elif encounter_class == "wellness":

        reason = "Preventive Care Outreach"

    elif encounter_class in [
        "outpatient",
        "ambulatory"
    ]:

        reason = random.choice([
            "Clinical Follow-up",
            "Appointment Follow-up",
            "Care Coordination"
        ])

    elif encounter_class == "inpatient":

        reason = "Clinical Follow-up"

    else:

        reason = random.choice(
            general_reasons
        )

    channel = random.choice(
        channels
    )

    interaction_records.append({

        "patient_uuid":
            patient_uuid,

        "interaction_date":
            encounter["START"],

        "channel":
            channel,

        "reason":
            reason,

        "summary":
            create_summary(
                reason,
                channel,
                encounter_class
            ),

        "status":
            random.choices(
                [
                    "Completed",
                    "Open",
                    "In Progress"
                ],
                weights=[
                    75,
                    15,
                    10
                ],
                k=1
            )[0]
    })

# ============================================================
# ADD AUTHORIZATION-RELATED INTERACTIONS
# ============================================================

if authorizations is not None:

    print(
        "\nCreating authorization interactions..."
    )

    # Find pending authorizations

    if "status" in authorizations.columns:

        pending_authorizations = (
            authorizations[
                authorizations["status"]
                .fillna("")
                .astype(str)
                .map(
                    lambda x:
                    x.strip().lower()
                )
                == "pending"
            ]
        )

        for _, auth in (
            pending_authorizations
            .iterrows()
        ):

            # Not every authorization needs
            # an interaction.

            if random.random() > 0.65:
                continue

            member_id = str(
                auth["member_id"]
            )

            # Reverse mapping to patient UUID
            # isn't required because we already
            # have the clean member ID.

            interaction_records.append({

                "patient_uuid":
                    None,

                "member_id_direct":
                    member_id,

                "interaction_date":
                    pd.to_datetime(
                        auth["request_date"],
                        errors="coerce"
                    ),

                "channel":
                    random.choice([
                        "Phone",
                        "Portal Message",
                        "Email"
                    ]),

                "reason":
                    "Authorization Follow-up",

                "summary":
                    "Follow-up regarding a "
                    "pending authorization request.",

                "status":
                    random.choice([
                        "Open",
                        "In Progress"
                    ])
            })

# ============================================================
# ADD CARE-GAP INTERACTIONS
# ============================================================

if care_gaps is not None:

    print(
        "Creating care-gap interactions..."
    )

    if "member_id" in care_gaps.columns:

        for _, gap in care_gaps.iterrows():

            # Only some care gaps generate
            # outreach interactions.

            if random.random() > 0.30:
                continue

            member_id = str(
                gap["member_id"]
            )

            gap_type = str(
                gap.get(
                    "gap_type",
                    "Care Gap"
                )
            )

            if "Immunization" in gap_type:

                reason = (
                    "Care Gap Outreach"
                )

            elif "Preventive" in gap_type:

                reason = (
                    "Preventive Care Outreach"
                )

            elif "Medication" in gap_type:

                reason = (
                    "Medication Follow-up"
                )

            else:

                reason = (
                    "Care Gap Outreach"
                )

            interaction_records.append({

                "patient_uuid":
                    None,

                "member_id_direct":
                    member_id,

                "interaction_date":
                    pd.Timestamp(
                        "2026-08-13"
                    ),

                "channel":
                    random.choice([
                        "Phone",
                        "Portal Message",
                        "Email"
                    ]),

                "reason":
                    reason,

                "summary":
                    create_summary(
                        reason,
                        random.choice(
                            channels
                        ),
                        ""
                    ),

                "status":
                    random.choice([
                        "Open",
                        "Completed",
                        "In Progress"
                    ])
            })

# ============================================================
# CREATE DATAFRAME
# ============================================================

interactions = pd.DataFrame(
    interaction_records
)

print(
    f"\nInteraction candidates generated: "
    f"{len(interactions)}"
)

# ============================================================
# LIMIT RECORD COUNT
# ============================================================

if len(interactions) > MAX_INTERACTIONS:

    interactions = interactions.sample(
        n=MAX_INTERACTIONS,
        random_state=SEED
    ).copy()

print(
    f"Interactions selected: "
    f"{len(interactions)}"
)

# ============================================================
# CONVERT PATIENT UUID → MEMBER ID
# ============================================================

def resolve_member_id(row):

    # Direct member ID from authorization/care gap

    if (
        "member_id_direct" in row.index
        and pd.notna(
            row["member_id_direct"]
        )
        and str(
            row["member_id_direct"]
        ).strip()
        != ""
        and str(
            row["member_id_direct"]
        ).lower()
        != "nan"
    ):

        return str(
            row["member_id_direct"]
        )

    # Otherwise use patient UUID

    patient_uuid = str(
        row.get(
            "patient_uuid",
            ""
        )
    )

    return member_mapping.get(
        patient_uuid,
        ""
    )


interactions["member_id"] = (
    interactions
    .apply(
        resolve_member_id,
        axis=1
    )
)

# ============================================================
# REMOVE INVALID MEMBERS
# ============================================================

interactions = interactions[
    interactions["member_id"]
    .astype(str)
    .str.startswith("M")
].copy()

# ============================================================
# CREATE INTERACTION IDs
# ============================================================

interactions = interactions.reset_index(
    drop=True
)

interactions.insert(
    0,
    "interaction_id",
    [
        f"INT{10000 + i}"
        for i in range(
            1,
            len(interactions) + 1
        )
    ]
)

# ============================================================
# DATE FORMAT
# ============================================================

interactions["interaction_date"] = (
    pd.to_datetime(
        interactions["interaction_date"],
        errors="coerce",
        utc=True
    )
    .dt.strftime("%Y-%m-%d")
)

# ============================================================
# SOURCE
# ============================================================

interactions["source"] = "Synthetic"

# ============================================================
# FINAL COLUMNS
# ============================================================

interactions = interactions[
    [
        "interaction_id",
        "member_id",
        "interaction_date",
        "channel",
        "reason",
        "summary",
        "status",
        "source"
    ]
]

# ============================================================
# CLEAN VALUES
# ============================================================

for column in [
    "member_id",
    "channel",
    "reason",
    "summary",
    "status",
    "source"
]:

    interactions[column] = (
        interactions[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

# ============================================================
# VALIDATION
# ============================================================

print(
    "\nInteraction Validation"
)

print(
    "Total interactions:",
    len(interactions)
)

print(
    "Unique members:",
    interactions["member_id"]
    .nunique()
)

print(
    "\nChannel distribution:"
)

print(
    interactions["channel"]
    .value_counts()
)

print(
    "\nReason distribution:"
)

print(
    interactions["reason"]
    .value_counts()
)

print(
    "\nStatus distribution:"
)

print(
    interactions["status"]
    .value_counts()
)

# ============================================================
# MEMBER VALIDATION
# ============================================================

valid_member_ids = set(
    member_mapping.values()
)

invalid_members = interactions[
    ~interactions["member_id"].isin(
        valid_member_ids
    )
]

if len(invalid_members) > 0:

    raise ValueError(
        "Invalid member IDs found."
    )

# ============================================================
# DUPLICATE ID CHECK
# ============================================================

if interactions[
    "interaction_id"
].duplicated().any():

    raise ValueError(
        "Duplicate interaction IDs found."
    )

# ============================================================
# SAVE
# ============================================================

interactions.to_csv(
    OUTPUT_FILE,
    index=False
)

print(
    f"\nCreated: {OUTPUT_FILE}"
)

print(
    "\nFirst 10 interactions:"
)

print(
    interactions.head(10)
    .to_string(index=False)
)