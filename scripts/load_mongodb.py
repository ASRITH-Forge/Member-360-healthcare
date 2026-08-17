"""
Load Processed Data into MongoDB
Reads all 7 CSV files from data/processed/ and bulk loads them into MongoDB collections.
Creates optimized indexes for fast retrieval.
"""
import os
import sys
import pandas as pd

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.database.mongodb import get_database, create_indexes, is_mock_db

PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

def load_all():
    print("=" * 80)
    print("LOADING PROCESSED DATA INTO MONGODB")
    print("=" * 80)

    db = get_database()
    print(f"Target Database: {db.name} (In-Memory Mock: {is_mock_db()})")

    collections_map = {
        "members": "members.csv",
        "eligibility": "eligibility.csv",
        "claims": "claims.csv",
        "medications": "medications.csv",
        "care_gaps": "care_gaps.csv",
        "authorizations": "authorizations.csv",
        "interactions": "interactions.csv"
    }

    total_inserted = 0

    for coll_name, fname in collections_map.items():
        fpath = os.path.join(PROCESSED_DIR, fname)
        if not os.path.exists(fpath):
            print(f"[WARN] File not found: {fpath}, skipping.")
            continue

        df = pd.read_csv(fpath)
        df = df.where(pd.notnull(df), None)
        records = df.to_dict(orient="records")

        # Clear existing collection and bulk insert
        coll = db[coll_name]
        coll.delete_many({})
        if records:
            coll.insert_many(records)
            count = coll.count_documents({})
            print(f"  [+] Loaded {count:>6,} documents into '{coll_name}'")
            total_inserted += count

    print("-" * 80)
    print(f"Total documents loaded: {total_inserted:,}")
    print("Creating database indexes...")
    create_indexes(db)
    print("=" * 80)
    print("DATABASE LOADING COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    load_all()
