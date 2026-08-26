import logging
import io
import pandas as pd
from datetime import datetime, timedelta, date
from typing import List, Dict, Any

from garmin.config import (
    GARMIN_DATA_FILENAME,
    GARMIN_ACTIVITIES_FILENAME,
    GARMIN_DATA_HEADERS,
    GARMIN_ACTIVITIES_HEADERS,
)
from garmin.garmin_client import GarminClient
from garmin.parser import parse_daily_data, parse_activity
from garmin.drive_client import DriveClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def sync_garmin_data(days_back: int = 30):
    garmin = GarminClient()
    garmin.login()

    drive = DriveClient()

    # 1. Sync Daily Data
    logger.info("Fetching existing Garmin Daily Data from Google Drive...")
    existing_daily_content = drive.download_file_by_name(GARMIN_DATA_FILENAME)
    if existing_daily_content:
        df_daily = pd.read_csv(io.StringIO(existing_daily_content))
    else:
        df_daily = pd.DataFrame(columns=GARMIN_DATA_HEADERS)

    start_date = date.today() - timedelta(days=days_back)
    end_date = date.today()

    daily_rows: List[Dict[str, Any]] = []
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        logger.info(f"Retrieving daily data for {date_str}...")

        summary = garmin.get_user_summary(date_str)
        sleep = garmin.get_sleep_data(date_str)
        hrv = garmin.get_hrv_data(date_str)
        resp = garmin.get_respiration_data(date_str)
        spo2 = garmin.get_spo2_data(date_str)
        training_status = garmin.get_training_status(date_str)
        max_metrics = garmin.get_max_metrics(date_str)

        row = parse_daily_data(
            date_str, summary, sleep, hrv, resp, spo2, training_status, max_metrics
        )
        daily_rows.append(row)
        current += timedelta(days=1)

    new_df_daily = pd.DataFrame(daily_rows)
    combined_daily = (
        pd.concat([df_daily, new_df_daily], ignore_index=True)
        .drop_duplicates(subset=["Date"], keep="last")
        .sort_values(by="Date", ascending=False)
    )
    combined_daily = combined_daily.reindex(columns=GARMIN_DATA_HEADERS)

    drive.upload_csv(GARMIN_DATA_FILENAME, combined_daily.to_csv(index=False))
    logger.info(f"Uploaded updated {GARMIN_DATA_FILENAME} ({len(combined_daily)} rows)")

    # 2. Sync Activities Data
    logger.info("Fetching existing Garmin Activities List from Google Drive...")
    existing_act_content = drive.download_file_by_name(GARMIN_ACTIVITIES_FILENAME)
    if existing_act_content:
        df_act = pd.read_csv(io.StringIO(existing_act_content))
    else:
        df_act = pd.DataFrame(columns=GARMIN_ACTIVITIES_HEADERS)

    logger.info(f"Retrieving activities from {start_date} to {end_date}...")
    raw_activities = garmin.get_activities_by_date(
        start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
    )

    activity_rows = [parse_activity(act) for act in raw_activities]
    new_df_act = pd.DataFrame(activity_rows)

    if not new_df_act.empty:
        combined_act = (
            pd.concat([df_act, new_df_act], ignore_index=True)
            .drop_duplicates(subset=["Activity ID"], keep="last")
            .sort_values(by="Start Time", ascending=False)
        )
    else:
        combined_act = df_act

    combined_act = combined_act.reindex(columns=GARMIN_ACTIVITIES_HEADERS)
    drive.upload_csv(GARMIN_ACTIVITIES_FILENAME, combined_act.to_csv(index=False))
    logger.info(f"Uploaded updated {GARMIN_ACTIVITIES_FILENAME} ({len(combined_act)} rows)")


if __name__ == "__main__":
    sync_garmin_data(days_back=30)
