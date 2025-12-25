"""
Test script for tools/data_tools.py

Run from project root:
    python tools/test_data_tools.py
"""

from tools.data_tools import load_space_missions, derive_features
import pandas as pd


def main():
    print("\n=== Running data tools test ===\n")

    # 1) Load raw dataset (path-based)
    raw_csv_path = load_space_missions(local_filename="space_missions.csv")
    print(f"Raw CSV path returned: {raw_csv_path}")

    # 2) Derive features (path-based)
    enriched_csv_path = derive_features(raw_csv_path)
    print(f"Enriched CSV path returned: {enriched_csv_path}")

    # 3) Validate enriched output
    df = pd.read_csv(enriched_csv_path)

    required_columns = ["Date", "Year", "Decade", "Success", "MissionStatus"]
    missing = [c for c in required_columns if c not in df.columns]

    if missing:
        print(f"❌ Missing required columns: {missing}")
        return

    print("✅ All required columns present")

    # 4) Sanity checks
    print("\n--- Sanity checks ---")
    print(f"Rows: {len(df)}")
    print(f"Year range: {df['Year'].dropna().min()} → {df['Year'].dropna().max()}")
    print(f"Success rate: {df['Success'].mean():.2%}")

    print("\n=== Data tools test PASSED ===\n")


if __name__ == "__main__":
    main()
