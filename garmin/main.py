import argparse
from datetime import datetime, timedelta
import logging
import os
import sys
import pandas as pd

from config import (
    GARMIN_EMAIL, GARMIN_PASSWORD, GARMIN_TOKENS_PATH,
    GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_DRIVE_FOLDER_ID,
    GARMIN_DAILY_FILENAME, GARMIN_ACTIVITIES_FILENAME
)
from drive_client import DriveClient
from garmin_client import GarminClient
from parser import parse_daily_summary, parse_activity

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def sync_dataframe_to_drive(drive_client: DriveClient, filename: str, new_df: pd.DataFrame, key: str) -> None:
    file_id = drive_client.find_file(filename)
    if file_id:
        existing_stream = drive_client.download_csv(file_id)
        try:
            existing_df = pd.read_csv(existing_stream)
            if not existing_df.empty:
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                combined_df.drop_duplicates(subset=[key], keep="last", inplace=True)
                combined_df.sort_values(by=key, ascending=True, inplace=True)
            else:
                combined_df = new_df
        except pd.errors.EmptyDataError:
            combined_df = new_df
    else:
        combined_df = new_df

    csv_content = combined_df.to_csv(index=False)
    drive_client.upload_or_update_csv(filename, csv_content)

def main(days_back: int = 7) -> None:
    drive = DriveClient(GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_DRIVE_FOLDER_ID)
    garmin = GarminClient(GARMIN_EMAIL, GARMIN_PASSWORD, GARMIN_TOKENS_PATH)
    garmin.login()

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days_back)
    logger.info(f"Syncing Garmin data from {start_date} to {end_date} ({days_back} days)...")

    # 1. Fetch daily telemetry -> garmin_daily_summary.csv
    daily_rows = []
    curr = start_date
    while curr <= end_date:
        d_str = curr.strftime("%Y-%m-%d")
        try:
            summary = garmin.get_user_summary(d_str)
            sleep = garmin.get_sleep_data(d_str)
            hrv = garmin.get_hrv_data(d_str)
            body_battery = garmin.get_body_battery(d_str)
            readiness = garmin.get_training_readiness(d_str)
            respiration = garmin.get_respiration_data(d_str)
            spo2 = garmin.get_spo2_data(d_str)
            max_metrics = garmin.get_max_metrics(d_str)
            training_status = garmin.get_training_status(d_str)

            daily_rows.append(parse_daily_summary(
                date_str=d_str,
                summary=summary,
                sleep=sleep,
                hrv=hrv,
                body_battery=body_battery,
                readiness=readiness,
                respiration=respiration,
                spo2=spo2,
                max_metrics=max_metrics,
                training_status=training_status
            ))
        except Exception as e:
            logger.warning(f"Could not parse daily metrics for {d_str}: {e}")
        curr += timedelta(days=1)

    if daily_rows:
        sync_dataframe_to_drive(drive, GARMIN_DAILY_FILENAME, pd.DataFrame(daily_rows), key="date")

    # 2. Fetch workout activities -> garmin_activities.csv
    try:
        activity_limit = max(50, days_back * 4)
        activities = garmin.get_activities(start=0, limit=activity_limit)
        parsed = [parse_activity(a) for a in activities]
        if parsed:
            sync_dataframe_to_drive(drive, GARMIN_ACTIVITIES_FILENAME, pd.DataFrame(parsed), key="activity_id")
    except Exception as e:
        logger.error(f"Failed syncing Garmin activities: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync Garmin data to Google Drive.")
    parser.add_argument("--days", type=int, default=7, help="Number of days to sync backwards.")
    args = parser.parse_args()
    main(days_back=args.days)
