"""
Unit Tests for Data Transformation and Validation Pipeline
"""
import os
import pytest
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

def test_processed_files_exist():
    required_files = [
        "members.csv",
        "eligibility.csv",
        "claims.csv",
        "medications.csv",
        "care_gaps.csv",
        "authorizations.csv",
        "interactions.csv"
    ]
    for fname in required_files:
        fpath = os.path.join(PROCESSED_DIR, fname)
        assert os.path.exists(fpath), f"Processed file {fname} does not exist."
        df = pd.read_csv(fpath)
        assert len(df) > 0, f"Processed file {fname} is empty."

def test_members_primary_key_uniqueness():
    df = pd.read_csv(os.path.join(PROCESSED_DIR, "members.csv"))
    assert df["member_id"].is_unique, "member_id in members.csv must be unique."
    assert "first_name" in df.columns
    assert "last_name" in df.columns
    assert "date_of_birth" in df.columns

def test_foreign_key_referential_integrity():
    members_df = pd.read_csv(os.path.join(PROCESSED_DIR, "members.csv"))
    valid_member_ids = set(members_df["member_id"])

    other_files = [
        "eligibility.csv",
        "claims.csv",
        "medications.csv",
        "care_gaps.csv",
        "authorizations.csv",
        "interactions.csv"
    ]

    for fname in other_files:
        df = pd.read_csv(os.path.join(PROCESSED_DIR, fname))
        assert "member_id" in df.columns, f"{fname} missing member_id column."
        unknown_ids = set(df["member_id"]) - valid_member_ids
        assert len(unknown_ids) == 0, f"{fname} contains {len(unknown_ids)} unknown member_ids not in members.csv"

def test_financial_sanity_in_claims():
    df = pd.read_csv(os.path.join(PROCESSED_DIR, "claims.csv"))
    assert (df["amount"] >= 0).all(), "Claims amount must be non-negative."
    assert (df["member_copay"] >= 0).all(), "Claims copay must be non-negative."
