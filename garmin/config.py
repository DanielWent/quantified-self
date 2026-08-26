import os
from dotenv import load_dotenv

load_dotenv()

GARMIN_EMAIL = os.getenv("GARMIN_EMAIL")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")
GARMIN_TOKEN = os.getenv("GARMIN_TOKEN")
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
GOOGLE_SPREADSHEET_KEY = os.getenv("GOOGLE_SPREADSHEET_KEY")

DAYS_TO_SYNC = int(os.getenv("DAYS_TO_SYNC", os.getenv("DAYS", "7")))
