import os
import sys
import csv
import json
import logging
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), "garmin"))
try:
    from drive_client import DriveClient
except ImportError:
    DriveClient = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

def resolve_data_file(filename, search_dirs=None):
    if os.path.exists(filename):
        return filename
    if search_dirs:
        for sdir in search_dirs:
            candidate = os.path.join(sdir, filename)
            if os.path.exists(candidate):
                return candidate
    return None

def load_json_records(filename, search_dirs=None):
    path = resolve_data_file(filename, search_dirs)
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading {path}: {e}")
    return []

def generate_quantified_self():
    try:
        days = int(os.getenv("DAYS_TO_SYNC", "730"))
    except (ValueError, TypeError):
        days = 730

    logger.info(f"Generating full Quantified Self spreadsheets for the past {days} days...")

    garmin_records = load_json_records("garmin_data.json", ["garmin", "."])
    withings_records = load_json_records("withings_data.json", ["withings", "."])

    cutoff_date = (datetime.now() - timedelta(days=days)).date().isoformat()

    garmin_by_date = {
        r.get("date"): r for r in garmin_records
        if isinstance(r, dict) and r.get("date", "") >= cutoff_date
    }
    withings_by_date = {
        r.get("date"): r for r in withings_records
        if isinstance(r, dict) and r.get("date", "") >= cutoff_date
    }

    all_dates = sorted(
        list(set(list(garmin_by_date.keys()) + list(withings_by_date.keys()))),
        reverse=True
    )

    # 1. Daily Metrics Spreadsheet
    daily_csv = "quantified_self_daily.csv"
    daily_headers = [
        "Date", "Steps", "Distance (km)", "VO2 Max", "Resting Heart Rate (bpm)",
        "HRV Avg (ms)", "Sleep Duration (hours)", "Sleep Score",
        "Weight (kg)", "Fat Ratio (%)", "Fat Mass (kg)", "Muscle Mass (kg)",
        "Hydration (kg)", "Bone Mass (kg)", "Pulse Wave Velocity (m/s)",
        "Visceral Fat", "Vascular Age", "Nerve Health Score"
    ]

    daily_rows = []
    for d in all_dates:
        g = garmin_by_date.get(d, {})
        w = withings_by_date.get(d, {})
        wm = w.get("measures", {})

        distance_km = round(g.get("distance_meters", 0.0) / 1000.0, 2) if g.get("distance_meters") else ""
        sleep_hrs = round(g.get("sleep_duration_seconds", 0) / 3600.0, 2) if g.get("sleep_duration_seconds") else ""

        daily_rows.append([
            d,
            g.get("steps", ""),
            distance_km,
            g.get("vo2_max", ""),
            g.get("resting_heart_rate", ""),
            g.get("hrv_avg", ""),
            sleep_hrs,
            g.get("sleep_score", ""),
            wm.get("weight_kg", ""),
            wm.get("fat_ratio_pct", ""),
            wm.get("fat_mass_weight_kg", ""),
            wm.get("muscle_mass_kg", ""),
            wm.get("hydration_kg", ""),
            wm.get("bone_mass_kg", ""),
            wm.get("pulse_wave_velocity_ms", ""),
            wm.get("visceral_fat", ""),
            wm.get("vascular_age", ""),
            wm.get("nerve_health_score", "")
        ])

    with open(daily_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(daily_headers)
        writer.writerows(daily_rows)
    logger.info(f"Generated {daily_csv} with {len(daily_rows)} rows.")

    # 2. Activities Spreadsheet
    activities_csv = "quantified_self_activities.csv"
    activity_headers = [
        "Activity ID", "Date", "Name", "Type", "Distance (km)",
        "Duration (mins)", "Average HR (bpm)", "Max HR (bpm)", "Average Pace (min/km)"
    ]

    activity_rows = []
    for d in sorted(garmin_by_date.keys(), reverse=True):
        g = garmin_by_date[d]
        for act in g.get("activities", []):
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
                d,
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

    # 3. Google Drive / Sheets Sync
    drive_creds = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") or os.getenv("GOOGLE_DRIVE_CREDENTIALS")
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    if drive_creds and DriveClient:
        try:
            drive_client = DriveClient(drive_creds, folder_id)
            drive_client.upload_file(daily_csv, folder_id, convert_to_sheets=True)
            drive_client.upload_file(activities_csv, folder_id, convert_to_sheets=True)
            logger.info("Synced full datasets to Google Drive / Sheets.")
        except Exception as e:
            logger.error(f"Failed Drive upload: {e}")

if __name__ == "__main__":
    generate_quantified_self()
