import os
import sys
import json
import logging
from datetime import datetime, timedelta
from config import (
    GOOGLE_DRIVE_CREDENTIALS,
    GOOGLE_DRIVE_FOLDER_ID,
    DAYS_TO_SYNC
)
from garmin_client import GarminClient
from drive_client import DriveClient
from parser import parse_garmin_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

def sync_garmin_data(days=DAYS_TO_SYNC):
    logger.info(f"Starting Garmin sync for the past {days} days...")
    
    drive_client = None
    if GOOGLE_DRIVE_CREDENTIALS:
        try:
            drive_client = DriveClient(GOOGLE_DRIVE_CREDENTIALS, GOOGLE_DRIVE_FOLDER_ID)
        except Exception as e:
            logger.warning(f"Failed to initialize Drive client: {e}")

    garmin_client = GarminClient()

    today = datetime.now().date()
    start_date = today - timedelta(days=days)
    
    activities = []
    try:
        activities = garmin_client.get_activities(
            start_date=start_date.isoformat(),
            end_date=today.isoformat(),
            limit=max(days * 3, 1000)
        ) or []
        logger.info(f"Retrieved {len(activities)} activities across {days} days.")
    except Exception as e:
        logger.warning(f"Error fetching activities: {e}")

    all_data = []
    for i in range(days):
        current_date = today - timedelta(days=i)
        date_str = current_date.isoformat()
        try:
            stats = None
            sleep = None
            rhr = None
            hrv = None

            try:
                stats = garmin_client.get_stats(date_str)
            except Exception as e:
                logger.debug(f"Stats unavailable for {date_str}: {e}")

            try:
                sleep = garmin_client.get_sleep_data(date_str)
            except Exception as e:
                logger.debug(f"Sleep data unavailable for {date_str}: {e}")

            try:
                rhr = garmin_client.get_rhr_data(date_str)
            except Exception as e:
                logger.debug(f"RHR data unavailable for {date_str}: {e}")

            try:
                hrv = garmin_client.get_hrv_data(date_str)
            except Exception as e:
                logger.debug(f"HRV data unavailable for {date_str}: {e}")

            day_data = parse_garmin_data(date_str, stats, sleep, rhr, hrv, activities)
            all_data.append(day_data)
        except Exception as e:
            logger.warning(f"Error processing Garmin data for {date_str}: {e}")
            continue

    output_filename = "garmin_data.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(all_data)} daily records to {output_filename}")

    if drive_client:
        try:
            drive_client.upload_file(output_filename, GOOGLE_DRIVE_FOLDER_ID)
            logger.info(f"Uploaded {output_filename} to Google Drive")
        except Exception as e:
            logger.error(f"Failed to upload {output_filename} to Drive: {e}")

if __name__ == "__main__":
    try:
        days_input = int(os.getenv("DAYS_TO_SYNC", str(DAYS_TO_SYNC)))
    except (ValueError, TypeError):
        days_input = DAYS_TO_SYNC
    sync_garmin_data(days=days_input)
