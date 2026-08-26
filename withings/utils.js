import fs from 'fs';
import { Readable } from 'stream';
import axios from 'axios';
import { google } from 'googleapis';
import { config } from './config.js';

const TOKEN_FILE_NAME = 'withings_tokens.json';

export function getDriveClient() {
  if (!config.serviceAccountJson) {
    throw new Error('GOOGLE_SERVICE_ACCOUNT_JSON is not configured.');
  }

  let auth;
  if (typeof config.serviceAccountJson === 'object' && config.serviceAccountJson !== null) {
    auth = new google.auth.GoogleAuth({
      credentials: config.serviceAccountJson,
      scopes: ['https://www.googleapis.com/auth/drive']
    });
  } else if (typeof config.serviceAccountJson === 'string') {
    if (fs.existsSync(config.serviceAccountJson)) {
      auth = new google.auth.GoogleAuth({
        keyFile: config.serviceAccountJson,
        scopes: ['https://www.googleapis.com/auth/drive']
      });
    } else {
      auth = new google.auth.GoogleAuth({
        credentials: JSON.parse(config.serviceAccountJson),
        scopes: ['https://www.googleapis.com/auth/drive']
      });
    }
  } else {
    throw new Error('Invalid GOOGLE_SERVICE_ACCOUNT_JSON credential format.');
  }

  return google.drive({ version: 'v3', auth });
}

async function getStoredRefreshToken(drive) {
  try {
    const query = `name = '${TOKEN_FILE_NAME}' and '${config.folderId}' in parents and trashed = false`;
    const res = await drive.files.list({
      q: query,
      fields: 'files(id, name)',
      supportsAllDrives: true,
      includeItemsFromAllDrives: true
    });

    if (res.data.files && res.data.files.length > 0) {
      const fileId = res.data.files[0].id;
      const fileData = await drive.files.get({ fileId, alt: 'media', supportsAllDrives: true }, { responseType: 'text' });
      const parsed = typeof fileData.data === 'string' ? JSON.parse(fileData.data) : fileData.data;
      if (parsed && parsed.refresh_token) {
        return { fileId, refreshToken: parsed.refresh_token };
      }
    }
  } catch (err) {
    console.warn('Could not read stored Withings token from Drive, falling back to secret:', err.message);
  }
  return { fileId: null, refreshToken: config.refreshToken ? config.refreshToken.trim() : null };
}

async function saveRefreshToken(drive, fileId, newRefreshToken) {
  try {
    const payload = JSON.stringify({ refresh_token: newRefreshToken, updated_at: new Date().toISOString() });
    const media = {
      mimeType: 'application/json',
      body: Readable.from([payload])
    };

    if (fileId) {
      await drive.files.update({ fileId, media, supportsAllDrives: true });
    } else {
      await drive.files.create({
        resource: { name: TOKEN_FILE_NAME, parents: [config.folderId] },
        media,
        fields: 'id',
        supportsAllDrives: true
      });
    }
    console.log('Saved updated Withings refresh token to Google Drive.');
  } catch (err) {
    console.warn('Could not persist updated Withings token to Drive:', err.message);
  }
}

export async function getAccessToken() {
  if (!config.clientId || !config.clientSecret) {
    throw new Error('Missing WITHINGS_CLIENT_ID or WITHINGS_CLIENT_SECRET in environment.');
  }

  const drive = getDriveClient();
  const { fileId, refreshToken } = await getStoredRefreshToken(drive);

  if (!refreshToken) {
    throw new Error('No refresh token found in Google Drive or WITHINGS_REFRESH_TOKEN secret.');
  }

  const params = new URLSearchParams({
    action: 'requesttoken',
    grant_type: 'refresh_token',
    client_id: config.clientId.trim(),
    client_secret: config.clientSecret.trim(),
    refresh_token: refreshToken.trim()
  });

  const response = await axios.post(
    'https://wbsapi.withings.net/v2/oauth2',
    params.toString(),
    {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    }
  );

  if (response.data.status !== 0 || !response.data.body) {
    throw new Error(`Withings Token Refresh Error: ${JSON.stringify(response.data)}`);
  }

  const { access_token, refresh_token: nextRefreshToken } = response.data.body;

  if (nextRefreshToken && nextRefreshToken !== refreshToken) {
    await saveRefreshToken(drive, fileId, nextRefreshToken);
  }

  return access_token;
}

export function decodeMeasurements(measuregrps) {
  const dailyMap = new Map();
  const sortedGroups = [...(measuregrps || [])].sort((a, b) => a.date - b.date);

  for (const group of sortedGroups) {
    const dateStr = new Date(group.date * 1000).toISOString().split('T')[0];
    const current = dailyMap.get(dateStr) || { date: dateStr };

    for (const measure of group.measures) {
      const typeName = config.measureTypes[measure.type];
      if (typeName) {
        current[typeName] = parseFloat((measure.value * Math.pow(10, measure.unit)).toFixed(3));
      }
    }
    dailyMap.set(dateStr, current);
  }

  return Array.from(dailyMap.values());
}
