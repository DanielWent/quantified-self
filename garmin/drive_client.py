import io
import json
import logging
import os
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import pandas as pd

try:
    import config
except ImportError:
    try:
        from garmin import config
    except ImportError:
        config = None

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive"]

def get_drive_service():
    """Authenticates and returns the Google Drive v3 service client."""
    credentials_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
    creds_path = getattr(config, "GOOGLE_CREDENTIALS_PATH", "credentials.json") if config else "credentials.json"
    
    if credentials_json:
        try:
            key_data = json.loads(credentials_json)
            creds = service_account.Credentials.from_service_account_info(key_data, scopes=SCOPES)
        except Exception as e:
            logger.error(f"Failed to parse GOOGLE_SERVICE_ACCOUNT_KEY: {e}")
            raise
    elif os.path.exists(creds_path):
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    else:
        raise FileNotFoundError("Google Drive service account credentials not found in env or file.")

    return build("drive", "v3", credentials=creds, cache_discovery=False)

def find_file(service, file_name: str, folder_id: str = None) -> dict:
    """Finds a non-trashed file by name in Google Drive."""
    target_folder = folder_id or (getattr(config, "GOOGLE_DRIVE_FOLDER_ID", None) if config else os.getenv("GOOGLE_DRIVE_FOLDER_ID"))
    
    query = f"name = '{file_name}' and trashed = false"
    if target_folder:
        query += f" and '{target_folder}' in parents"
        
    response = service.files().list(
        q=query,
        fields="files(id, name)",
        spaces="drive",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    
    files = response.get("files", [])
    return files[0] if files else None

def download_csv_from_drive(file_name: str, folder_id: str = None) -> pd.DataFrame:
    """Downloads an existing CSV file from Google Drive into a pandas DataFrame."""
    try:
        service = get_drive_service()
        file_meta = find_file(service, file_name, folder_id)
        
        if not file_meta:
            logger.info(f"File '{file_name}' not found on Google Drive. A new file will be created.")
            return None

        file_id = file_meta["id"]
        request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
        
        file_stream = io.BytesIO()
        downloader = MediaIoBaseDownload(file_stream, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
            
        file_stream.seek(0)
        
        if file_stream.getbuffer().nbytes == 0:
            logger.warning(f"File '{file_name}' on Google Drive is 0 bytes.")
            return None

        df = pd.read_csv(file_stream)
        logger.info(f"Downloaded existing '{file_name}' ({len(df)} rows) from Google Drive.")
        return df

    except Exception as e:
        logger.warning(f"Could not download '{file_name}' from Drive: {e}")
        return None

def upload_csv_to_drive(file_path: str, file_name: str, folder_id: str = None) -> str:
    """Uploads or updates a CSV file on Google Drive."""
    service = get_drive_service()
    target_folder = folder_id or (getattr(config, "GOOGLE_DRIVE_FOLDER_ID", None) if config else os.getenv("GOOGLE_DRIVE_FOLDER_ID"))

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Local file '{file_path}' does not exist.")

    if os.path.getsize(file_path) == 0:
        raise ValueError(f"Refusing to upload 0-byte file '{file_path}' to Google Drive.")

    existing_file = find_file(service, file_name, target_folder)
    media = MediaFileUpload(file_path, mimetype="text/csv", resumable=True)

    if existing_file:
        file_id = existing_file["id"]
        updated_file = service.files().update(
            fileId=file_id,
            media_body=media,
            fields="id, name",
            supportsAllDrives=True
        ).execute()
        logger.info(f"Updated existing file '{file_name}' (ID: {file_id})")
        return updated_file["id"]
    else:
        file_metadata = {"name": file_name}
        if target_folder:
            file_metadata["parents"] = [target_folder]
            
        new_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name",
            supportsAllDrives=True
        ).execute()
        logger.info(f"Created new file '{file_name}' (ID: {new_file['id']})")
        return new_file["id"]
