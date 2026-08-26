import fs from 'fs';
import { Readable } from 'stream';
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

export async function getWithingsTokenFromDrive(drive, folderId) {
  if (!drive) {
    return null;
  }
  try {
    let query = "name = 'withings_token.json' and trashed = false";
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
      return null;
    }

    const fileId = files[0].id;
    const getRes = await drive.files.get(
      { fileId, alt: 'media' },
      { responseType: 'json' }
    );

    if (getRes.data && getRes.data.refresh_token) {
      console.log(`Loaded Withings refresh token from Google Drive (File ID: ${fileId})`);
      return getRes.data.refresh_token;
    }
  } catch (err) {
    console.warn('Could not retrieve withings_token.json from Google Drive:', err.message);
  }
  return null;
}

export async function saveWithingsTokenToDrive(drive, folderId, tokenPayload) {
  if (!drive) {
    return null;
  }
  try {
    let query = "name = 'withings_token.json' and trashed = false";
    if (folderId) {
      query += ` and '${folderId}' in parents`;
    }

    const listRes = await drive.files.list({
      q: query,
      spaces: 'drive',
      fields: 'files(id, name)'
    });

    const files = listRes.data.files || [];
    const contentString = JSON.stringify(tokenPayload, null, 2);
    const media = {
      mimeType: 'application/json',
      body: Readable.from([contentString])
    };

    if (files.length > 0) {
      const fileId = files[0].id;
      await drive.files.update({
        fileId,
        media,
        fields: 'id, name'
      });
      console.log(`Updated withings_token.json on Google Drive (File ID: ${fileId})`);
      return fileId;
    } else {
      const requestBody = {
        name: 'withings_token.json',
        mimeType: 'application/json'
      };
      if (folderId) {
        requestBody.parents = [folderId];
      }
      const createRes = await drive.files.create({
        requestBody,
        media,
        fields: 'id, name'
      });
      console.log(`Created withings_token.json on Google Drive (File ID: ${createRes.data.id})`);
      return createRes.data.id;
    }
  } catch (err) {
    console.error('Failed to save withings_token.json to Google Drive:', err.message);
    return null;
  }
}
