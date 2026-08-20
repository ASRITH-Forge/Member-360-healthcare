import os
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "member360")

PROCESSED_DIR = "data/processed"

collections_map = {
    "members": "members.csv",
    "eligibility": "eligibility.csv",
    "claims": "claims.csv",
    "medications": "medications.csv",
    "care_gaps": "care_gaps.csv",
    "authorizations": "authorizations.csv",
    "interactions": "interactions.csv",
}

print("Connecting to MongoDB Atlas...")

client = MongoClient(
    MONGODB_URI,
    serverSelectionTimeoutMS=10000,
    connectTimeoutMS=10000
)

client.admin.command("ping")

db = client[MONGODB_DATABASE]

print("✅ Connected to Atlas")
print(f"Database: {MONGODB_DATABASE}")

for collection_name, filename in collections_map.items():

    file_path = os.path.join(
        PROCESSED_DIR,
        filename
    )

    if not os.path.exists(file_path):
        print(f"⚠️ File not found: {file_path}")
        continue

    print(f"\nLoading {filename}...")

    df = pd.read_csv(file_path)

    # Convert NaN values to None
    df = df.where(
        pd.notnull(df),
        None
    )

    records = df.to_dict(
        orient="records"
    )

    collection = db[collection_name]

    # Remove old data before loading fresh data
    collection.delete_many({})

    if records:
        collection.insert_many(records)

    print(
        f"✅ {collection_name}: "
        f"{len(records)} records loaded"
    )

print("\n================================")
print("Atlas data loading completed!")
print("================================")

print("\nCollections and record counts:")

for collection_name in collections_map:

    count = db[collection_name].count_documents({})

    print(
        f"{collection_name}: {count}"
    )

client.close()