import fs from 'fs';
import { google } from 'googleapis';

export function initDriveClient(credentialsRaw) {
  if (!credentialsRaw) {
    return null;
  }
  try {
    let credsDict;
    if (fs.existsSync(credentialsRaw)) {
      credsDict = JSON.parse(fs.readFileSync(credentialsRaw, 'utf-8'));
    } else {
      try {
        const decoded = Buffer.from(credentialsRaw, 'base64').toString('utf-8');
        credsDict = JSON.parse(decoded);
      } catch {
        credsDict = JSON.parse(credentialsRaw);
      }
    }

    const auth = new google.auth.GoogleAuth({
      credentials: credsDict,
      scopes: ['https://www.googleapis.com/auth/drive']
    });
    return google.drive({ version: 'v3', auth });
  } catch (err) {
    console.warn('Failed to initialize Google Drive client for Withings:', err.message);
    return null;
  }
}

export async function uploadFileToDrive(drive, folderId, filePath) {
  if (!drive) {
    return null;
  }
  try {
    const fileName = filePath.split('/').pop().split('\\').pop();
    const baseName = fileName.replace(/\.[^/.]+$/, "");

    let query = `(name = '${fileName}' or name = '${baseName}') and trashed = false`;
    if (folderId) {
      query += ` and '${folderId}' in parents`;
    }

    const listRes = await drive.files.list({
      q: query,
      spaces: 'drive',
      fields: 'files(id, name)'
    });

    const files = listRes.data.files || [];
    if (files.length === 0) {
      console.error(`Cannot update '${fileName}': File not found in Google Drive folder.`);
      return null;
    }

    const fileId = files[0].id;
    const media = {
      mimeType: 'text/csv',
      body: fs.createReadStream(filePath)
    };

    await drive.files.update({
      fileId,
      media,
      fields: 'id, name'
    });
    console.log(`Updated '${files[0].name}' on Google Drive (File ID: ${fileId})`);
    return fileId;
  } catch (err) {
    console.error(`Failed to upload ${filePath} to Google Drive:`, err.message);
    return null;
  }
}
