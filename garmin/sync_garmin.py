import os
import sys
import csv
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

    # Save local JSON cache
    with open("garmin_data.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(all_data)} daily records to garmin_data.json")

    # 1. Generate garmin_daily_summary.csv
    daily_csv = "garmin_daily_summary.csv"
    daily_headers = [
        "Date", "Steps", "Distance (km)", "VO2 Max",
        "Resting Heart Rate (bpm)", "HRV Avg (ms)", "Sleep Duration (hours)", "Sleep Score"
    ]
    daily_rows = []
    for d in sorted(all_data, key=lambda x: x.get("date", ""), reverse=True):
        dist_km = round(d.get("distance_meters", 0.0) / 1000.0, 2) if d.get("distance_meters") else ""
        sleep_hrs = round(d.get("sleep_duration_seconds", 0) / 3600.0, 2) if d.get("sleep_duration_seconds") else ""
        daily_rows.append([
            d.get("date", ""),
            d.get("steps", ""),
            dist_km,
            d.get("vo2_max", ""),
            d.get("resting_heart_rate", ""),
            d.get("hrv_avg", ""),
            sleep_hrs,
            d.get("sleep_score", "")
        ])

    with open(daily_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(daily_headers)
        writer.writerows(daily_rows)
    logger.info(f"Generated {daily_csv} with {len(daily_rows)} rows.")

    # 2. Generate garmin_activities.csv
    activities_csv = "garmin_activities.csv"
    activity_headers = [
        "Activity ID", "Date", "Name", "Type", "Distance (km)",
        "Duration (mins)", "Average HR (bpm)", "Max HR (bpm)", "Average Pace (min/km)"
    ]
    activity_rows = []
    for d in sorted(all_data, key=lambda x: x.get("date", ""), reverse=True):
        for act in d.get("activities", []):
            dist_km = round(act.get("distance_meters", 0.0) / 1000.0, 2) if act.get("distance_meters") else ""
            dur_mins = round(act.get("duration_seconds", 0.0) / 60.0, 2) if act.get("duration_seconds") else ""
            
            speed_ms = act.get("avg_pace_meter_per_sec")
            pace_str = ""
            if speed_ms and speed_ms > 0:
                sec_per_km = 1000.0 / speed_ms
                pace_mins = int(sec_per_km // 60)
                pace_secs = int(sec_per_km % 60)
                pace_str = f"{pace_mins:02d}:{pace_secs:02d}"

            activity_rows.append([
                act.get("activity_id", ""),
                d.get("date", ""),
                act.get("name", ""),
                act.get("type", ""),
                dist_km,
                dur_mins,
                act.get("average_hr", ""),
                act.get("max_hr", ""),
                pace_str
            ])

    with open(activities_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(activity_headers)
        writer.writerows(activity_rows)
    logger.info(f"Generated {activities_csv} with {len(activity_rows)} rows.")

    # Upload to Google Drive
    if drive_client:
        try:
            drive_client.upload_file(daily_csv, GOOGLE_DRIVE_FOLDER_ID)
            drive_client.upload_file(activities_csv, GOOGLE_DRIVE_FOLDER_ID)
            logger.info("Updated garmin_daily_summary.csv and garmin_activities.csv on Google Drive.")
        except Exception as e:
            logger.error(f"Failed to upload Garmin files to Drive: {e}")

if __name__ == "__main__":
    try:
        days_input = int(os.getenv("DAYS_TO_SYNC", str(DAYS_TO_SYNC)))
    except (ValueError, TypeError):
        days_input = DAYS_TO_SYNC
    sync_garmin_data(days=days_input)
