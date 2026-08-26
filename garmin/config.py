import os
from dotenv import load_dotenv

load_dotenv()

GARMIN_TOKENS = os.getenv("GARMIN_TOKENS")
GARMIN_EMAIL = os.getenv("GARMIN_EMAIL")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")
GOOGLE_DRIVE_CREDENTIALS = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") or os.getenv("GOOGLE_DRIVE_CREDENTIALS")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

try:
    DAYS_TO_SYNC = int(os.getenv("DAYS_TO_SYNC", "7"))
except (ValueError, TypeError):
    DAYS_TO_SYNC = 7
