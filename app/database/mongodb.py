"""
MongoDB Database Connection Manager
Provides unified access to MongoDB collections with automatic resilient fallback
to in-memory mongomock if a standalone MongoDB instance is offline.
"""
import os
import logging
from dotenv import load_dotenv
import pymongo
import mongomock

load_dotenv()

logger = logging.getLogger("member360.database")
logging.basicConfig(level=logging.INFO)

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "member360")

_client = None
_db = None
_is_mock = False

def get_database():
    """
    Get or initialize the MongoDB database connection.
    Attempts live connection first; falls back to mongomock seamlessly.
    """
    global _client, _db, _is_mock

    if _db is not None:
        return _db

    # Try live MongoDB connection with short timeout
    try:
        real_client = pymongo.MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=1500,
            connectTimeoutMS=1500
        )
        # Verify connection
        real_client.admin.command('ping')
        _client = real_client
        _db = _client[MONGODB_DATABASE]
        _is_mock = False
        logger.info(f"[Database] Connected successfully to live MongoDB at {MONGODB_URI}, DB: {MONGODB_DATABASE}")
        return _db
    except Exception as e:
        logger.warning(f"[Database] Live MongoDB connection unavailable ({e}). Initializing resilient in-memory MongoDB store (mongomock)...")
        mock_client = mongomock.MongoClient()
        _client = mock_client
        _db = _client[MONGODB_DATABASE]
        _is_mock = True
        
        # Proactively load processed CSV data into mongomock if empty
        _bootstrap_mock_data(_db)
        return _db

def is_mock_db() -> bool:
    """Return True if running in mock/in-memory mode."""
    return _is_mock

def _bootstrap_mock_data(db):
    """Auto-populates collections from processed CSV files if database is fresh."""
    import pandas as pd
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    processed_dir = os.path.join(base_dir, "data", "processed")

    collections_map = {
        "members": "members.csv",
        "eligibility": "eligibility.csv",
        "claims": "claims.csv",
        "medications": "medications.csv",
        "care_gaps": "care_gaps.csv",
        "authorizations": "authorizations.csv",
        "interactions": "interactions.csv",
        "requests": "requests.csv"
    }

    for coll_name, fname in collections_map.items():
        fpath = os.path.join(processed_dir, fname)
        if os.path.exists(fpath) and db[coll_name].count_documents({}) == 0:
            df = pd.read_csv(fpath)
            # Replace NaN with appropriate defaults
            df = df.where(pd.notnull(df), None)
            records = df.to_dict(orient="records")
            if records:
                db[coll_name].insert_many(records)
                logger.info(f"[Database Bootstrap] Loaded {len(records)} records into mock collection '{coll_name}'.")

    create_indexes(db)

def create_indexes(db):
    """Create optimized indexes for fast queries across all entities."""
    try:
        # Member ID index on every collection
        collections = ["members", "eligibility", "claims", "medications", "care_gaps", "authorizations", "interactions", "requests"]
        for coll in collections:
            db[coll].create_index("member_id")

        # Specific query indexes
        db.members.create_index("first_name")
        db.members.create_index("last_name")
        db.claims.create_index([("member_id", 1), ("claim_date", -1)])
        db.claims.create_index("status")
        db.authorizations.create_index([("member_id", 1), ("status", 1)])
        db.authorizations.create_index("authorization_id", unique=True)
        db.care_gaps.create_index([("member_id", 1), ("status", 1)])
        db.interactions.create_index([("member_id", 1), ("status", 1)])
        db.interactions.create_index("interaction_id", unique=True)
        db.medications.create_index([("member_id", 1), ("status", 1)])
        db.requests.create_index("request_id", unique=True)
        db.requests.create_index("organization_id")
        db.requests.create_index("status")
        db.requests.create_index("priority")
        db.requests.create_index("request_date")
        db.requests.create_index([("member_id", 1), ("status", 1)])
        logger.info("[Database] Indexes created successfully.")
    except Exception as e:
        logger.warning(f"[Database] Index creation note: {e}")

def get_collection(collection_name: str):
    """Helper to get a specific collection from the active database."""
    db = get_database()
    return db[collection_name]
