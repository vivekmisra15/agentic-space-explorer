from __future__ import annotations

from pathlib import Path
from io import StringIO
import time

import pandas as pd
import requests


# ---------- Path helpers (robust across where you run from) ----------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


# ---------- Tool 1: load_space_missions() -> csv_path ----------

def load_space_missions(
    local_filename: str = "space_missions.csv",
    url: str | None = None,
    out_filename: str = "space_missions_raw.csv",
) -> str:
    """
    Load the space missions CSV and return a *path* to the raw CSV.

    MVP-v1 behavior (reliable demos):
      1) Prefer local file: <project_root>/data/<local_filename>
      2) Optional URL fallback (if provided)
      3) If URL works, save a local copy anyway (so downstream steps are file-based)

    Returns:
        str: absolute path to raw CSV on disk
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    local_path = DATA_DIR / local_filename
    raw_out_path = DATA_DIR / out_filename

    # 1) Local preferred
    if local_path.exists():
        print(f"📁 Using local dataset: {local_path}")
        # Optionally copy to a canonical raw filename (keeps pipeline consistent)
        if local_path.name != raw_out_path.name:
            
            # Read CSV with encoding fallbacks (real-world datasets often aren't UTF-8)
            encodings_to_try = ["utf-8", "cp1252", "latin-1"]

            last_err = None
            for enc in encodings_to_try:
                try:
                    df = pd.read_csv(local_path, encoding=enc)
                    print(f"✅ Read CSV using encoding: {enc}")
                    break
                except UnicodeDecodeError as e:
                    last_err = e
                    print(f"⚠️ Encoding {enc} failed, trying next...")
            else:
                # If we never broke out of the loop
                raise last_err
            # Normalizing encoding to UTF-8 and writing canonical raw CSV…
            df.to_csv(raw_out_path, index=False, encoding='utf-8')
            print(f"✅ Wrote canonical raw CSV: {raw_out_path}")
            return str(raw_out_path)
        return str(local_path)

    print(f"⚠️ Local dataset not found at: {local_path}")

    # 2) URL fallback (optional)
    if url:
        try:
            print(f"📡 Downloading dataset from URL...")
            resp = requests.get(url, timeout=25)
            resp.raise_for_status()

            encodings_to_try = ["utf-8", "cp1252", "latin-1"]
            last_err = None

            for enc in encodings_to_try:
                try:
                    decoded_text = resp.content.decode(enc)
                    df = pd.read_csv(StringIO(decoded_text))
                    print(f"✅ Read CSV using encoding: {enc}")
                    break
                except UnicodeDecodeError as e:
                    last_err = e
                    print(f"⚠️ Encoding {enc} failed, trying next...")
            else:
                # If we never broke out of the loop
                raise last_err
            
            # Normalizing encoding to UTF-8 and writing canonical raw CSV…
            df.to_csv(raw_out_path, index=False, encoding='utf-8')

            print(f"✅ Downloaded and saved raw CSV to: {raw_out_path}")
            return str(raw_out_path)

        except Exception as e:
            raise RuntimeError(f"Failed to load dataset from URL. Error: {e}") from e

    # If we get here, no local file and no (working) URL
    raise FileNotFoundError(
        f"Could not find local file '{local_path}' and no URL was provided."
    )


# ---------- Tool 2: derive_features(csv_path) -> enriched_csv_path ----------

def derive_features(
    csv_path: str,
    out_filename: str = "space_missions_enriched.csv",
) -> str:
    """
    Read a CSV from csv_path, derive deterministic analytical features,
    write an enriched CSV, and return the enriched CSV path.

    Adds (MVP v1):
      - Year (from Date)
      - Decade (from Year)
      - Success (bool from MissionStatus containing 'Success')

    Returns:
        str: absolute path to enriched CSV on disk
    """
    in_path = Path(csv_path)
    if not in_path.exists():
        raise FileNotFoundError(f"Input csv_path does not exist: {in_path}")

    df = pd.read_csv(in_path)

    # --- Parse Date
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Year"] = df["Date"].dt.year
        df["Decade"] = (df["Year"] // 10) * 10
    else:
        # Keep pipeline predictable even if Date is missing
        df["Year"] = pd.NA
        df["Decade"] = pd.NA

    # --- Success boolean (based on your actual column name: MissionStatus)
    if "MissionStatus" in df.columns:
        df["Success"] = df["MissionStatus"].astype(str).str.contains(
            "Success", case=False, na=False
        )
    else:
        df["Success"] = False

    # Optional: add a simple "run timestamp" column for debugging (can remove later)
    df["EnrichedAtUnix"] = int(time.time())

    out_path = DATA_DIR / out_filename
    df.to_csv(out_path, index=False)

    print(f"✅ Enriched CSV written to: {out_path}")
    return str(out_path)

# ---------- Manual smoke test block ----------
#           Developer-only smoke test.

 #   This block allows running:
 #       python tools/data_tools.py

 #   to quickly verify that:
 #     - the dataset loads correctly
 #     - encodings are handled
 #     - feature derivation works
 #     - output CSVs are written

 #   This code is NOT used by agents or Streamlit.
 #-------------------------------  

if __name__ == "__main__":
    raw_path = load_space_missions(local_filename="space_missions.csv")
    enriched_path = derive_features(raw_path)

    df = pd.read_csv(enriched_path)
    print("\n--- Smoke test summary ---")
    print(f"Raw CSV path: {raw_path}")
    print(f"Enriched CSV path: {enriched_path}")
    if "Year" in df.columns:
        print(f"Year range: {df['Year'].dropna().min()} → {df['Year'].dropna().max()}")
    if "Success" in df.columns:
        print(f"Success rate: {df['Success'].mean():.2%}")
    print("--------------------------\n")
# Test script for data_tools.py