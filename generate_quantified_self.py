import os
import json
import logging
from datetime import datetime, timezone
from garmin.drive_client import GoogleDriveClient
from garmin.config import GOOGLE_DRIVE_FOLDER_ID, GOOGLE_SERVICE_ACCOUNT_JSON

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main():
    if not GOOGLE_DRIVE_FOLDER_ID or not GOOGLE_SERVICE_ACCOUNT_JSON:
        raise EnvironmentError("GOOGLE_DRIVE_FOLDER_ID and GOOGLE_SERVICE_ACCOUNT_JSON are required.")

    drive = GoogleDriveClient()
    logging.info("Downloading latest raw data from Google Drive...")
    
    garmin_raw = drive.download_json("garmin_data.json") or {}
    withings_raw = drive.download_json("withings_data.json") or {}

    logging.info("Compiling Quantified Self summary...")
    compiled_dataset = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "garmin": garmin_raw,
        "withings": withings_raw,
    }

    file_id = drive.upload_json("quantified_self_summary.json", compiled_dataset)
    logging.info("Quantified self dataset generated and updated. File ID: %s", file_id)

if __name__ == "__main__":
    main()
