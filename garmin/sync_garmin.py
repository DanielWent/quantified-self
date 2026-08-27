import logging
from datetime import datetime, timezone
from garmin.config import validate_garmin_config, GARMIN_EMAIL, GARMIN_PASSWORD
from garmin.drive_client import GoogleDriveClient
from garmin.garmin_client import GarminClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main():
    validate_garmin_config()
    
    logging.info("Connecting to Garmin Connect for %s...", GARMIN_EMAIL)
    garmin = GarminClient(email=GARMIN_EMAIL, password=GARMIN_PASSWORD)
    garmin.login()

    logging.info("Fetching Garmin metrics...")
    today_stats = garmin.get_user_summary()
    activities = garmin.get_recent_activities(limit=20)
    sleep_data = garmin.get_sleep_data()

    payload = {
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "summary": today_stats,
        "recent_activities": activities,
        "sleep": sleep_data
    }

    logging.info("Uploading Garmin sync data to Google Drive...")
    drive = GoogleDriveClient()
    file_id = drive.upload_json("garmin_data.json", payload)
    logging.info("Successfully synced Garmin data. Drive File ID: %s", file_id)

if __name__ == "__main__":
    main()
