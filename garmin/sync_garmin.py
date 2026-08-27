import os
import logging
from datetime import datetime, timedelta
import pandas as pd
from garmin.garmin_client import GarminClient
from garmin.parser import parse_garmin_day
from garmin.drive_client import upload_csv_to_drive, download_csv_from_drive
from garmin.config import GARMIN_EMAIL, GARMIN_PASSWORD, GARMIN_TOKENSTORE, DRIVE_FILE_NAME

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def sync_garmin_data(days_back: int = 7):
    logger.info(f"Starting Garmin sync for the past {days_back} days...")
    client = GarminClient(GARMIN_EMAIL, GARMIN_PASSWORD, GARMIN_TOKENSTORE)
    
    # Demographic and biometric profile fetched once per run
    profile = client.get_user_profile()
    settings = client.get_user_settings()
    
    records = []
    today = datetime.now().date()

    for i in range(days_back, -1, -1):
        target_date = (today - timedelta(days=i)).isoformat()
        
        summary = client.get_daily_summary(target_date)
        max_metrics = client.get_max_metrics(target_date)
        
        day_record = parse_garmin_day(summary, profile, settings, max_metrics, target_date)
        records.append(day_record)

    new_df = pd.DataFrame(records)
    
    # Merge new records with existing Google Drive CSV data
    existing_df = download_csv_from_drive(DRIVE_FILE_NAME)
    if existing_df is not None and not existing_df.empty:
        combined_df = pd.concat([existing_df, new_df], ignore_index=True).drop_duplicates(subset=["Date"], keep="last")
    else:
        combined_df = new_df

    combined_df.sort_values(by="Date", inplace=True)
    
    temp_csv_path = "drw_garmin_data.csv"
    combined_df.to_csv(temp_csv_path, index=False)
    logger.info(f"Saved {len(combined_df)} rows to {temp_csv_path}")
    
    upload_csv_to_drive(temp_csv_path, DRIVE_FILE_NAME)
    logger.info("Uploaded Garmin CSV to Google Drive successfully.")

if __name__ == "__main__":
    sync_garmin_data()
