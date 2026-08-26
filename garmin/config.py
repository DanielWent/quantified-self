import os
from dotenv import load_dotenv

load_dotenv()

GARMIN_EMAIL = os.getenv("GARMIN_EMAIL")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")
GARMIN_TOKENS_PATH = os.getenv("GARMIN_TOKENS_PATH", ".garmin_tokens")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

GARMIN_DAILY_FILENAME = "garmin_daily_summary.csv"
GARMIN_ACTIVITIES_FILENAME = "garmin_activities.csv"
