import csv
from datetime import datetime, timedelta
import json
import logging
import os
import sys

# Ensure local garmin directory is at the front of sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    DAYS_TO_SYNC,
    GARMIN_ACTIVITIES_FILENAME,
    GARMIN_ACTIVITIES_HEADERS,
    GARMIN_DATA_FILENAME,
    GARMIN_DATA_HEADERS,
    GOOGLE_DRIVE_CREDENTIALS,
    GOOGLE_DRIVE_FOLDER_ID,
)
from drive_client import DriveClient
from garmin_client import GarminClient
from parser import parse_garmin_activity_data, parse_garmin_daily_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def load_existing_csv(file_path: str, key_field: str) -> dict:
    rows_map = {}
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = str(row.get(key_field, "")).strip()
                    if key:
                        rows_map[key] = row
        except Exception as e:
            logger.warning(f"Could not load existing CSV {file_path}: {e}")
    return rows_map


def sync_garmin_data(days: int = DAYS_TO_SYNC):
    logger.info(f"Starting Garmin sync for the past {days} days...")

    drive_client = None
    if GOOGLE_DRIVE_CREDENTIALS:
        try:
            drive_client = DriveClient(GOOGLE_DRIVE_CREDENTIALS, GOOGLE_DRIVE_FOLDER_ID)
        except Exception as e:
            logger.warning(f"Failed to initialize Drive client: {e}")

    garmin_client = GarminClient()
    user_profile = garmin_client.get_user_profile()

    today = datetime.now().date()
    start_date = today - timedelta(days=days)

    activities = []
    try:
        activities = garmin_client.get_activities(
            start_date=start_date.isoformat(),
            end_date=today.isoformat(),
            limit=max(days * 4, 1000)
        ) or []
        logger.info(f"Retrieved {len(activities)} activities across {days} days.")
    except Exception as e:
        logger.warning(f"Error fetching activities: {e}")

    # Load existing CSVs to preserve history
    existing_daily = load_existing_csv(GARMIN_DATA_FILENAME, "Date (YYYY-MM-DD)")
    existing_acts = load_existing_csv(GARMIN_ACTIVITIES_FILENAME, "Activity ID")

    all_daily_records = []
    for i in range(days):
        current_date = today - timedelta(days=i)
        date_str = current_date.isoformat()
        try:
            payloads = garmin_client.fetch_daily_payloads(date_str)
            daily_row = parse_garmin_daily_data(
                date_str=date_str,
                user_profile=user_profile,
                summary=payloads["summary"],
                stats=payloads["stats"],
                sleep_data=payloads["sleep_data"],
                hrv_payload=payloads["hrv_payload"],
                bp_payload=payloads["bp_payload"],
                training_status_std=payloads["training_status_std"],
                training_status_modern=payloads["training_status_modern"],
                lactate_data=payloads["lactate_data"],
                lactate_range_hr=payloads["lactate_range_hr"],
                lactate_range_speed=payloads["lactate_range_speed"],
                readiness_data=payloads["readiness_data"],
                activities=activities,
            )
            existing_daily[date_str] = daily_row
            all_daily_records.append(daily_row)
        except Exception as e:
            logger.warning(f"Error processing Garmin daily data for {date_str}: {e}")
            continue

    # Process activities
    for act in activities:
        if not isinstance(act, dict):
            continue
        act_id = str(act.get("activityId", ""))
        if not act_id:
            continue
        try:
            act_payloads = garmin_client.fetch_activity_payloads(act)
            act_row = parse_garmin_activity_data(
                activity=act_payloads["activity"],
                full_activity=act_payloads["full_activity"],
                weather_data=act_payloads["weather_data"],
                hr_zones=act_payloads["hr_zones"],
                power_zones=act_payloads["power_zones"],
            )
            existing_acts[act_id] = act_row
        except Exception as e:
            logger.warning(f"Error processing activity {act_id}: {e}")
            continue

    # 1. Write drw_garmin_data.csv (sorted descending by date)
    daily_rows_sorted = sorted(
        list(existing_daily.values()),
        key=lambda r: str(r.get("Date (YYYY-MM-DD)", "")),
        reverse=True
    )
    with open(GARMIN_DATA_FILENAME, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=GARMIN_DATA_HEADERS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(daily_rows_sorted)
    logger.info(f"Saved {len(daily_rows_sorted)} daily rows to {GARMIN_DATA_FILENAME}")

    # 2. Write drw_garmin_activities_list.csv (sorted descending by date and time)
    act_rows_sorted = sorted(
        list(existing_acts.values()),
        key=lambda r: (str(r.get("Date (YYYY-MM-DD)", "")), str(r.get("Start Time (HH:MM)", ""))),
        reverse=True
    )
    with open(GARMIN_ACTIVITIES_FILENAME, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=GARMIN_ACTIVITIES_HEADERS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(act_rows_sorted)
    logger.info(f"Saved {len(act_rows_sorted)} activity rows to {GARMIN_ACTIVITIES_FILENAME}")

    # 3. Save JSON cache for backward compatibility
    with open("garmin_data.json", "w", encoding="utf-8") as f:
        json.dump(all_daily_records, f, indent=2, ensure_ascii=False)

    # 4. Upload to Google Drive
    if drive_client:
        try:
            drive_client.upload_file(GARMIN_DATA_FILENAME, GOOGLE_DRIVE_FOLDER_ID)
            drive_client.upload_file(GARMIN_ACTIVITIES_FILENAME, GOOGLE_DRIVE_FOLDER_ID)
            logger.info("Uploaded Garmin CSVs to Google Drive successfully.")
        except Exception as e:
            logger.error(f"Failed to upload Garmin files to Drive: {e}")


if __name__ == "__main__":
    try:
        days_input = int(os.getenv("DAYS_TO_SYNC", str(DAYS_TO_SYNC)))
    except (ValueError, TypeError):
        days_input = DAYS_TO_SYNC
    sync_garmin_data(days=days_input)
