import io
import json
from typing import Optional
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from garmin.config import get_service_account_info, GOOGLE_DRIVE_FOLDER_ID

SCOPES = ["https://www.googleapis.com/auth/drive"]

class GoogleDriveClient:
    def __init__(self, folder_id: Optional[str] = None):
        self.folder_id = folder_id or GOOGLE_DRIVE_FOLDER_ID
        if not self.folder_id:
            raise ValueError("GOOGLE_DRIVE_FOLDER_ID is required.")
        
        sa_info = get_service_account_info()
        self.creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
        self.service = build("drive", "v3", credentials=self.creds)

    def find_file(self, filename: str) -> Optional[str]:
        query = f"name = '{filename}' and '{self.folder_id}' in parents and trashed = false"
        results = self.service.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name)"
        ).execute()
        files = results.get("files", [])
        return files[0]["id"] if files else None

    def upload_json(self, filename: str, data: dict) -> str:
        file_id = self.find_file(filename)
        json_bytes = json.dumps(data, indent=2).encode("utf-8")
        media = MediaIoBaseUpload(io.BytesIO(json_bytes), mimetype="application/json", resumable=True)

        if file_id:
            updated_file = self.service.files().update(
                fileId=file_id,
                media_body=media,
                fields="id"
            ).execute()
            return updated_file.get("id")
        else:
            file_metadata = {
                "name": filename,
                "parents": [self.folder_id]
            }
            created_file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id"
            ).execute()
            return created_file.get("id")

    def download_json(self, filename: str) -> Optional[dict]:
        file_id = self.find_file(filename)
        if not file_id:
            return None

        request = self.service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        
        fh.seek(0)
        return json.loads(fh.read().decode("utf-8"))
