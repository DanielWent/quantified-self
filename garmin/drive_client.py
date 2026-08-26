import os
import json
import base64
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)

class DriveClient:
    def __init__(self, credentials_raw, folder_id=None):
        self.folder_id = folder_id
        self.service = self._init_drive_service(credentials_raw)

    def _init_drive_service(self, credentials_raw):
        try:
            if os.path.exists(credentials_raw):
                with open(credentials_raw, "r", encoding="utf-8") as f:
                    creds_dict = json.load(f)
            else:
                try:
                    decoded = base64.b64decode(credentials_raw).decode("utf-8")
                    creds_dict = json.loads(decoded)
                except Exception:
                    creds_dict = json.loads(credentials_raw)

            scopes = ["https://www.googleapis.com/auth/drive"]
            creds = service_account.Credentials.from_service_account_info(
                creds_dict, scopes=scopes
            )
            return build("drive", "v3", credentials=creds)
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive service: {e}")
            raise

    def upload_file(self, file_path, folder_id=None, convert_to_sheets=False):
        target_folder = folder_id or self.folder_id
        file_name = os.path.basename(file_path)

        query = f"name = '{file_name}' and trashed = false"
        if target_folder:
            query += f" and '{target_folder}' in parents"

        response = self.service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
        existing_files = response.get("files", [])

        mime_type = "text/csv" if file_path.endswith(".csv") else "application/json"
        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

        if convert_to_sheets and file_path.endswith(".csv"):
            for existing in existing_files:
                try:
                    self.service.files().delete(fileId=existing["id"]).execute()
                    logger.info(f"Replaced existing Google Sheet '{file_name}' (ID: {existing['id']})")
                except Exception as e:
                    logger.warning(f"Failed to delete existing file {existing['id']}: {e}")

            file_metadata = {
                "name": file_name,
                "mimeType": "application/vnd.google-apps.spreadsheet"
            }
            if target_folder:
                file_metadata["parents"] = [target_folder]

            created_file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, name"
            ).execute()
            logger.info(f"Created Google Sheet '{file_name}' (ID: {created_file.get('id')})")
            return created_file.get("id")

        if existing_files:
            file_id = existing_files[0]["id"]
            updated_file = self.service.files().update(
                fileId=file_id,
                media_body=media,
                fields="id, name"
            ).execute()
            logger.info(f"Updated existing file '{file_name}' (ID: {updated_file.get('id')})")
            return updated_file.get("id")
        else:
            file_metadata = {"name": file_name}
            if target_folder:
                file_metadata["parents"] = [target_folder]

            created_file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, name"
            ).execute()
            logger.info(f"Created new file '{file_name}' (ID: {created_file.get('id')})")
            return created_file.get("id")
