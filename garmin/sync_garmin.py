import os
import argparse
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv
from garmin_client import GarminSyncClient
from drive_client import DriveClient
from parser import parse_daily_summary, parse_activity

load_dotenv()

def sync_to_drive(drive_client: DriveClient, filename: str, new_df: pd.DataFrame, key: str):
    file_id = drive_client.find_file(filename)
    if file_id:
        existing_stream = drive_client.download_csv(file_id)
        existing_df = pd.read_csv(existing_stream)
        
        # Merge new records into existing dataframe, updating rows that changed
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df.drop_duplicates(subset=[key], keep="last", inplace=True)
        combined_df.sort_values(by=key, ascending=True, inplace=True)
    else:
        combined_df = new_df

    csv_content = combined_df.to_csv(index=False)
    drive_client.upload_or_update_csv(filename, csv_content)
    print(f"Updated {filename} on Google Drive ({len(combined_df)} total rows).")

def main(days_back: int = 7):
    service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    drive_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    
    drive = DriveClient(service_account_json, drive_folder_id)
    client = GarminSyncClient()
    client.login()

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days_back)

    # 1. Fetch and merge Daily Health Summaries
    daily_rows = []
    curr_date = start_date
    while curr_date <= end_date:
        date_str = curr_date.strftime("%Y-%m-%d")
        try:
            summary = client.get_stats(date_str)
            sleep = client.get_sleep(date_str)
            hrv = client.get_hrv(date_str)
            daily_rows.append(parse_daily_summary(date_str, summary, sleep, hrv))
        except Exception as e:
            print(f"Skipping daily summary for {date_str}: {e}")
        curr_date += timedelta(days=1)

    if daily_rows:
        sync_to_drive(drive, "garmin_daily_summary.csv", pd.DataFrame(daily_rows), key="date")

    # 2. Fetch and merge Activities
    try:
        activity_limit = max(50, days_back * 4)
        activities = client.get_activities(limit=activity_limit)
        parsed_activities = [parse_activity(a) for a in activities]
        if parsed_activities:
            sync_to_drive(drive, "garmin_activities.csv", pd.DataFrame(parsed_activities), key="activity_id")
    except Exception as e:
        print(f"Failed to sync activities: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7, help="Days of history to fetch")
    args = parser.parse_args()
    main(days_back=args.days)
