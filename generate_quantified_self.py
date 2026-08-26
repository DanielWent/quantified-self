import os
import sys
import json
import logging
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SPREADSHEET_KEY = os.getenv("GOOGLE_SPREADSHEET_KEY")
CREDENTIALS_JSON = os.getenv("GOOGLE_SHEETS_CREDENTIALS")

if len(sys.argv) > 1 and sys.argv[1].isdigit():
    DAYS_TO_SYNC = int(sys.argv[1])
else:
    DAYS_TO_SYNC = int(os.getenv("DAYS_TO_SYNC", os.getenv("DAYS", "7")))

def get_gspread_client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    if os.path.exists(CREDENTIALS_JSON):
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_JSON, scope)
    else:
        creds_dict = json.loads(CREDENTIALS_JSON)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

def main():
    logger.info(f"Aggregating Quantified Self data (configured sync window: {DAYS_TO_SYNC} days)...")
    gc = get_gspread_client()
    spreadsheet = gc.open_by_key(SPREADSHEET_KEY)

    garmin_sheet = spreadsheet.worksheet("Garmin")
    withings_sheet = spreadsheet.worksheet("Withings")

    garmin_data = garmin_sheet.get_all_records()
    withings_data = withings_sheet.get_all_records()

    if not garmin_data and not withings_data:
        logger.warning("No data found in Garmin or Withings sheets.")
        return

    df_garmin = pd.DataFrame(garmin_data)
    df_withings = pd.DataFrame(withings_data)

    if not df_garmin.empty and "Date" in df_garmin.columns:
        df_garmin["Date"] = pd.to_datetime(df_garmin["Date"]).dt.strftime("%Y-%m-%d")
    if not df_withings.empty and "Date" in df_withings.columns:
        df_withings["Date"] = pd.to_datetime(df_withings["Date"]).dt.strftime("%Y-%m-%d")

    if not df_garmin.empty and not df_withings.empty:
        merged_df = pd.merge(df_garmin, df_withings, on="Date", how="outer")
    elif not df_garmin.empty:
        merged_df = df_garmin
    else:
        merged_df = df_withings

    merged_df.sort_values(by="Date", ascending=False, inplace=True)
    merged_df.drop_duplicates(subset=["Date"], keep="first", inplace=True)
    merged_df.fillna("", inplace=True)

    try:
        qs_sheet = spreadsheet.worksheet("Quantified Self")
    except gspread.WorksheetNotFound:
        qs_sheet = spreadsheet.add_worksheet(title="Quantified Self", rows=str(max(1000, len(merged_df) + 100)), cols="50")

    header = merged_df.columns.tolist()
    values = [header] + merged_df.values.tolist()

    qs_sheet.clear()
    qs_sheet.update("A1", values)
    logger.info(f"Quantified Self sheet updated successfully with {len(merged_df)} total records.")

if __name__ == "__main__":
    main()
