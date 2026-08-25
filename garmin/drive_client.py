import io
import json
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

class DriveClient:
    def __init__(self, service_account_info_or_path: str, folder_id: str):
        self.folder_id = folder_id
        scopes = ['https://www.googleapis.com/auth/drive']
        
        if os.path.exists(service_account_info_or_path):
            self.creds = service_account.Credentials.from_service_account_file(
                service_account_info_or_path, scopes=scopes
            )
        else:
            self.creds = service_account.Credentials.from_service_account_info(
                json.loads(service_account_info_or_path), scopes=scopes
            )
        self.service = build('drive', 'v3', credentials=self.creds)

    def find_file(self, filename: str) -> str:
        query = f"name = '{filename}' and '{self.folder_id}' in parents and trashed = false"
        results = self.service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])
        return files[0]['id'] if files else None

    def download_csv(self, file_id: str) -> io.BytesIO:
        request = self.service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        fh.seek(0)
        return fh

    def upload_or_update_csv(self, filename: str, csv_content: str):
        file_id = self.find_file(filename)
        media = MediaIoBaseUpload(io.BytesIO(csv_content.encode('utf-8')), mimetype='text/csv', resumable=True)
        
        if file_id:
            self.service.files().update(fileId=file_id, media_body=media).execute()
        else:
            file_metadata = {'name': filename, 'parents': [self.folder_id]}
            self.service.files().create(body=file_metadata, media_body=media).execute()
