import io
import json
import logging
import os
import sys
from typing import Optional
import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'garmin'))
from drive_client import DriveClient

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

GARMIN_FILENAME = "garmin_daily_summary.csv"
WITHINGS_FILENAME = "withings_measurements.csv"
OUTPUT_DATASET_FILENAME = "quantified_self.csv"

def load_csv(drive: Optional[DriveClient], filename: str) -> pd.DataFrame:
    # 1. Check local file path
    for local_path in [filename, os.path.join("data", filename)]:
        if os.path.exists(local_path):
            try:
                df = pd.read_csv(local_path)
                if not df.empty:
                    logger.info(f"Loaded '{filename}' from local path: {local_path}")
                    return df
            except Exception:
                pass

    # 2. Check Google Drive
    if drive:
        try:
            file_id = drive.find_file(filename)
            if file_id:
                fh = drive.download_csv(file_id)
                df = pd.read_csv(fh)
                if not df.empty:
                    logger.info(f"Loaded '{filename}' from Google Drive.")
                    return df
        except Exception as e:
            logger.warning(f"Error loading '{filename}' from Google Drive: {e}")

    return pd.DataFrame()

def build_quantified_self_dataset() -> None:
    drive = None
    if SERVICE_ACCOUNT_JSON and DRIVE_FOLDER_ID:
        try:
            drive = DriveClient(SERVICE_ACCOUNT_JSON, DRIVE_FOLDER_ID)
        except Exception as e:
            logger.warning(f"DriveClient initialization note: {e}")

    garmin_df = load_csv(drive, GARMIN_FILENAME)
    withings_df = load_csv(drive, WITHINGS_FILENAME)

    if garmin_df.empty and withings_df.empty:
        raise ValueError(
            f"Could not load '{GARMIN_FILENAME}' or '{WITHINGS_FILENAME}' locally or from Google Drive."
        )

    if not garmin_df.empty and 'date' in garmin_df.columns:
        garmin_df['date'] = garmin_df['date'].astype(str)
    if not withings_df.empty and 'date' in withings_df.columns:
        withings_df['date'] = withings_df['date'].astype(str)

    if not garmin_df.empty and not withings_df.empty:
        merged_df = pd.merge(garmin_df, withings_df, on='date', how='outer')
    elif not garmin_df.empty:
        merged_df = garmin_df
    else:
        merged_df = withings_df

    merged_df.sort_values(by='date', ascending=True, inplace=True)
    merged_df.drop_duplicates(subset=['date'], keep='last', inplace=True)

    # Save output locally
    os.makedirs("data", exist_ok=True)
    local_out_path = os.path.join("data", OUTPUT_DATASET_FILENAME)
    merged_df.to_csv(local_out_path, index=False)
    logger.info(f"Saved dataset locally to {local_out_path} ({len(merged_df)} rows).")

    # Upload merged dataset to Google Drive
    if drive:
        csv_content = merged_df.to_csv(index=False)
        drive.upload_or_update_csv(OUTPUT_DATASET_FILENAME, csv_content)
        logger.info(f"Uploaded '{OUTPUT_DATASET_FILENAME}' to Google Drive.")

if __name__ == "__main__":
    build_quantified_self_dataset()
