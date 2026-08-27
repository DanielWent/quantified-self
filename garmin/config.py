import os
import json
from dotenv import load_dotenv

load_dotenv()

GARMIN_EMAIL = os.getenv("GARMIN_EMAIL")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

def get_service_account_info() -> dict:
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON environment variable is not set.")
    
    # Handle if JSON string is passed directly or if a filepath is provided
    if os.path.isfile(GOOGLE_SERVICE_ACCOUNT_JSON):
        with open(GOOGLE_SERVICE_ACCOUNT_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    try:
        return json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    except json.JSONDecodeError as exc:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON is not a valid JSON string or file path.") from exc

def validate_garmin_config() -> None:
    missing = []
    if not GARMIN_EMAIL:
        missing.append("GARMIN_EMAIL")
    if not GARMIN_PASSWORD:
        missing.append("GARMIN_PASSWORD")
    if not GOOGLE_DRIVE_FOLDER_ID:
        missing.append("GOOGLE_DRIVE_FOLDER_ID")
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        missing.append("GOOGLE_SERVICE_ACCOUNT_JSON")
        
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")
