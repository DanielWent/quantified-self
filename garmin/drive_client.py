import io
import json
import logging
import os
from typing import Any, Dict, Optional, Union
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from exceptions import DriveSyncError

logger = logging.getLogger(__name__)

class DriveClient:
    def __init__(self, service_account_info_or_path: Union[str, Dict[str, Any]], folder_id: str):
        self.folder_id = folder_id
        scopes = ['https://www.googleapis.com/auth/drive']

        if not service_account_info_or_path:
            raise DriveSyncError("GOOGLE_SERVICE_ACCOUNT_JSON is not configured or empty.")

        try:
            if isinstance(service_account_info_or_path, dict):
                self.creds = service_account.Credentials.from_service_account_info(
                    service_account_info_or_path, scopes=scopes
                )
            elif isinstance(service_account_info_or_path, str):
                if os.path.exists(service_account_info_or_path):
                    self.creds = service_account.Credentials.from_service_account_file(
                        service_account_info_or_path, scopes=scopes
                    )
                else:
                    info = json.loads(service_account_info_or_path)
                    self.creds = service_account.Credentials.from_service_account_info(
                        info, scopes=scopes
                    )
            else:
                raise DriveSyncError(f"Unsupported credentials type: {type(service_account_info_or_path)}")

            self.service = build('drive', 'v3', credentials=self.creds)
        except Exception as e:
            raise DriveSyncError(f"Failed to initialize Google Drive client: {e}")

    def find_file(self, filename: str) -> Optional[str]:
        try:
            query = f"name = '{filename}' and '{self.folder_id}' in parents and trashed = false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            files = results.get('files', [])
            return files[0]['id'] if files else None
        except Exception as e:
            raise DriveSyncError(f"Failed searching for {filename}: {e}")

    def download_csv(self, file_id: str) -> io.BytesIO:
        try:
            request = self.service.files().get_media(fileId=file_id, supportsAllDrives=True)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            fh.seek(0)
            return fh
        except Exception as e:
            raise DriveSyncError(f"Failed downloading file ID {file_id}: {e}")

    def upload_or_update_csv(self, filename: str, csv_content: str) -> None:
        try:
            file_id = self.find_file(filename)
            media = MediaIoBaseUpload(io.BytesIO(csv_content.encode('utf-8')), mimetype='text/csv', resumable=True)

            if file_id:
                self.service.files().update(
                    fileId=file_id,
                    media_body=media,
                    supportsAllDrives=True
                ).execute()
                logger.info(f"Updated '{filename}' on Google Drive.")
            else:
                file_metadata = {'name': filename, 'parents': [self.folder_id]}
                self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    supportsAllDrives=True
                ).execute()
                logger.info(f"Created '{filename}' on Google Drive.")
        except Exception as e:
            raise DriveSyncError(f"Failed uploading '{filename}': {e}")
