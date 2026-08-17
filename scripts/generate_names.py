import pandas as pd
import random
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================

FILE = Path("data/processed/members.csv")

SEED = 42
random.seed(SEED)

# ============================================================
# NAME POOLS
# ============================================================

male_first_names = [
    "Aarav", "Arjun", "Aditya", "Rahul", "Rohan",
    "Vikram", "Karan", "Arnav", "Varun", "Siddharth",
    "Akash", "Ravi", "Raj", "Nikhil", "Amit",
    "Anil", "Manoj", "Sanjay", "Harsha", "Vivek",
    "Abhishek", "Rakesh", "Pranav", "Karthik", "Rohit",
    "Suresh", "Tarun", "Yash", "Dhruv", "Krishna"
]

female_first_names = [
    "Ananya", "Priya", "Sneha", "Kavya", "Neha",
    "Pooja", "Divya", "Swathi", "Meghana", "Lakshmi",
    "Isha", "Aisha", "Riya", "Nisha", "Shreya",
    "Pallavi", "Sakshi", "Keerthi", "Deepika", "Sonia",
    "Anjali", "Bhavana", "Harini", "Madhuri", "Manasa",
    "Sravya", "Tanvi", "Vaishnavi", "Navya", "Aditi"
]

last_names = [
    "Sharma", "Reddy", "Kumar", "Patel", "Rao",
    "Verma", "Mehta", "Gupta", "Nair", "Iyer",
    "Naidu", "Singh", "Joshi", "Kapoor", "Mishra",
    "Das", "Chowdhury", "Menon", "Pillai", "Desai",
    "Bose", "Shah", "Agarwal", "Malhotra", "Bhat",
    "Kulkarni", "Sinha", "Chandra", "Yadav", "Pandey"
]

# ============================================================
# LOAD MEMBERS
# ============================================================

members = pd.read_csv(FILE)

print(f"Members loaded: {len(members)}")

# ============================================================
# GENERATE UNIQUE NAMES
# ============================================================

used_names = set()

for index, row in members.iterrows():

    gender = str(
        row["gender"]
    ).strip().upper()

    if gender == "M":
        first_pool = male_first_names

    elif gender == "F":
        first_pool = female_first_names

    else:
        first_pool = (
            male_first_names +
            female_first_names
        )

    # Keep trying until a unique full name is created
    while True:

        first_name = random.choice(
            first_pool
        )

        last_name = random.choice(
            last_names
        )

        full_name = (
            f"{first_name} {last_name}"
        )

        if full_name not in used_names:
            used_names.add(full_name)
            break

    members.loc[
        index,
        "first_name"
    ] = first_name

    members.loc[
        index,
        "last_name"
    ] = last_name

# ============================================================
# SAVE
# ============================================================

members.to_csv(
    FILE,
    index=False
)

print(
    f"\nUpdated: {FILE}"
)

print(
    f"Unique names generated: "
    f"{len(used_names)}"
)

print("\nFirst 20 members:")

print(
    members[
        [
            "member_id",
            "first_name",
            "last_name",
            "gender"
        ]
    ]
    .head(20)
    .to_string(index=False)
)