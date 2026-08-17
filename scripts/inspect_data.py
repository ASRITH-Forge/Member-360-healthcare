"""
Inspect Raw Synthea CSV Datasets
Reads all raw Synthea CSV files from data/raw/synthea/
Outputs schema, row counts, columns, non-null counts, and sample values.
"""
import os
import glob
import pandas as pd
import json

RAW_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw", "synthea")

def inspect_all():
    csv_files = glob.glob(os.path.join(RAW_DIR, "*.csv"))
    if not csv_files:
        print(f"No CSV files found in {RAW_DIR}")
        return

    print("=" * 80)
    print("SYNTHEA RAW DATASET INSPECTION REPORT")
    print(f"Found {len(csv_files)} CSV files in {RAW_DIR}")
    print("=" * 80)

    summary = {}

    for file_path in sorted(csv_files):
        file_name = os.path.basename(file_path)
        print(f"\n>>> File: {file_name}")
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        print(f"    Size: {file_size_mb:.2f} MB")
        
        try:
            # Read first 100 rows for quick inspection and full row count
            df_sample = pd.read_csv(file_path, nrows=5)
            # Count rows efficiently
            row_count = sum(1 for _ in open(file_path, 'r', encoding='utf-8', errors='ignore')) - 1
            print(f"    Total Rows: {row_count}")
            print(f"    Columns ({len(df_sample.columns)}): {list(df_sample.columns)}")
            print("    Sample Row 1:")
            if not df_sample.empty:
                for col in df_sample.columns:
                    val = df_sample.iloc[0][col]
                    print(f"      - {col}: {val}")
            
            summary[file_name] = {
                "rows": row_count,
                "columns": list(df_sample.columns),
                "size_mb": round(file_size_mb, 2)
            }
        except Exception as e:
            print(f"    Error reading {file_name}: {e}")

    output_path = os.path.join(os.path.dirname(__file__), "inspection_summary.json")
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nInspection summary saved to {output_path}")

if __name__ == "__main__":
    inspect_all()
