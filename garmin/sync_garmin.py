import os
import sys
from datetime import datetime, timedelta
import logging

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

try:
    from config import (
        GARMIN_EMAIL,
        GARMIN_PASSWORD,
        GARMIN_TOKEN,
        GOOGLE_SHEETS_CREDENTIALS,
        GOOGLE_SPREADSHEET_KEY,
        DAYS_TO_SYNC,
    )
    from garmin_client import GarminClient
    from drive_client import DriveClient
    from parser import parse_daily_summary
except ImportError:
    from garmin.config import (
        GARMIN_EMAIL,
        GARMIN_PASSWORD,
        GARMIN_TOKEN,
        GOOGLE_SHEETS_CREDENTIALS,
        GOOGLE_SPREADSHEET_KEY,
        DAYS_TO_SYNC,
    )
    from garmin.garmin_client import GarminClient
    from garmin.drive_client import DriveClient
    from garmin.parser import parse_daily_summary

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def sync_garmin_data(days: int = None):
    sync_days = days if days is not None else DAYS_TO_SYNC
    logger.info(f"Starting Garmin sync for the past {sync_days} days...")

    garmin_client = GarminClient()
    garmin_client.authenticate()

    drive_client = DriveClient()
    worksheet = drive_client.get_worksheet("Garmin")
    existing_records = drive_client.get_existing_dates(worksheet)

    today = datetime.now().date()
    rows_to_update = []

    for i in range(sync_days):
        target_date = today - timedelta(days=i)
        date_str = target_date.strftime("%Y-%m-%d")

        try:
            raw_stats = garmin_client.get_stats_for_date(date_str)
            parsed_data = parse_daily_summary(date_str, raw_stats)
            if parsed_data:
                rows_to_update.append(parsed_data)
        except Exception as e:
            logger.warning(f"Could not retrieve Garmin data for {date_str}: {e}")

    if rows_to_update:
        drive_client.upsert_rows(worksheet, rows_to_update, existing_records)
        logger.info(f"Successfully processed {len(rows_to_update)} Garmin records.")
    else:
        logger.warning("No Garmin data retrieved to update.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        days_input = int(sys.argv[1])
    else:
        days_input = DAYS_TO_SYNC
    sync_garmin_data(days=days_input)
