import os
import argparse
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv
from garmin_client import GarminSyncClient
from parser import parse_daily_summary, parse_activity

load_dotenv()

DAILY_CSV_PATH = os.path.join("data", "garmin_daily_summary.csv")
ACTIVITIES_CSV_PATH = os.path.join("data", "garmin_activities.csv")

def update_csv(new_df: pd.DataFrame, file_path: str, primary_key: str):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    if os.path.exists(file_path):
        existing_df = pd.read_csv(file_path)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df.drop_duplicates(subset=[primary_key], keep="last", inplace=True)
        combined_df.sort_values(by=primary_key, ascending=True, inplace=True)
    else:
        combined_df = new_df
    combined_df.to_csv(file_path, index=False)

def main(days_back: int = 7):
    client = GarminSyncClient()
    client.login()

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days_back)

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
        update_csv(pd.DataFrame(daily_rows), DAILY_CSV_PATH, primary_key="date")

    try:
        activities = client.get_activities(start_date.strftime("%Y-%m-%d"), limit=50)
        parsed_activities = [parse_activity(a) for a in activities]
        if parsed_activities:
            update_csv(pd.DataFrame(parsed_activities), ACTIVITIES_CSV_PATH, primary_key="activity_id")
    except Exception as e:
        print(f"Failed to sync activities: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7, help="Days to fetch backwards")
    args = parser.parse_args()
    main(days_back=args.days)
