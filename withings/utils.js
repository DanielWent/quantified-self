import { google } from 'googleapis';
import axios from 'axios';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const TOKEN_FILE_NAME = 'withings_tokens.json';
const LOCAL_TOKEN_PATH = path.join(__dirname, TOKEN_FILE_NAME);

export function getDriveClient() {
  const serviceAccountJson = process.env.GOOGLE_SERVICE_ACCOUNT_JSON || process.env.GOOGLE_CREDENTIALS;
  if (!serviceAccountJson) {
    throw new Error('GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_CREDENTIALS is not configured.');
  }

  let credentials;
  try {
    credentials = JSON.parse(serviceAccountJson);
  } catch (e) {
    throw new Error('Failed to parse Google service account credentials JSON.');
  }

  const auth = new google.auth.JWT(
    credentials.client_email,
    null,
    credentials.private_key,
    ['https://www.googleapis.com/auth/drive']
  );

  return google.drive({ version: 'v3', auth });
}

export async function loadTokensFromDrive(drive) {
  const folderId = process.env.GOOGLE_DRIVE_FOLDER_ID;
  let query = `name = '${TOKEN_FILE_NAME}' and trashed = false`;
  if (folderId) {
    query += ` and '${folderId}' in parents`;
  }

  try {
    const res = await drive.files.list({
      q: query,
      fields: 'files(id, name)',
      spaces: 'drive',
    });

    if (res.data.files && res.data.files.length > 0) {
      const fileId = res.data.files[0].id;
      const fileRes = await drive.files.get(
        { fileId, alt: 'media' },
        { responseType: 'json' }
      );
      return { fileId, tokens: fileRes.data };
    }
  } catch (err) {
    console.warn('[Withings] Could not load tokens from Google Drive:', err.message);
  }

  if (fs.existsSync(LOCAL_TOKEN_PATH)) {
    try {
      const localData = JSON.parse(fs.readFileSync(LOCAL_TOKEN_PATH, 'utf8'));
      return { fileId: null, tokens: localData };
    } catch (e) {}
  }

  return { fileId: null, tokens: null };
}

export async function saveTokensToDrive(drive, tokens, existingFileId = null) {
  const folderId = process.env.GOOGLE_DRIVE_FOLDER_ID;
  fs.writeFileSync(LOCAL_TOKEN_PATH, JSON.stringify(tokens, null, 2));

  const media = {
    mimeType: 'application/json',
    body: JSON.stringify(tokens, null, 2),
  };

  try {
    if (existingFileId) {
      await drive.files.update({
        fileId: existingFileId,
        media,
      });
      console.log('[Withings] Updated withings_tokens.json on Google Drive.');
    } else {
      let fileId = existingFileId;
      // Search if created elsewhere
      let query = `name = '${TOKEN_FILE_NAME}' and trashed = false`;
      if (folderId) query += ` and '${folderId}' in parents`;
      const res = await drive.files.list({ q: query, fields: 'files(id, name)' });

      if (res.data.files && res.data.files.length > 0) {
        fileId = res.data.files[0].id;
        await drive.files.update({ fileId, media });
        console.log('[Withings] Updated existing withings_tokens.json on Google Drive.');
      } else {
        const fileMetadata = {
          name: TOKEN_FILE_NAME,
          parents: folderId ? [folderId] : [],
        };
        await drive.files.create({
          resource: fileMetadata,
          media,
          fields: 'id',
        });
        console.log('[Withings] Created new withings_tokens.json on Google Drive.');
      }
    }
  } catch (err) {
    console.error('[Withings] Failed to save tokens to Google Drive:', err.message);
  }
}

export async function getAccessToken() {
  const drive = getDriveClient();
  const { fileId, tokens } = await loadTokensFromDrive(drive);

  const clientId = process.env.WITHINGS_CLIENT_ID;
  const clientSecret = process.env.WITHINGS_CLIENT_SECRET;
  
  // Use refresh token from Drive file first, fallback to environment variable
  let refreshToken = tokens?.refresh_token || process.env.WITHINGS_REFRESH_TOKEN;

  if (!refreshToken) {
    throw new Error('No refresh token found in Google Drive or environment variables.');
  }

  // If token exists and is not expired (with 5-minute buffer), reuse it
  if (tokens && tokens.access_token && tokens.expires_at) {
    const now = Math.floor(Date.now() / 1000);
    if (tokens.expires_at > now + 300) {
      return tokens.access_token;
    }
  }

  console.log('[Withings] Refreshing access token via Withings API...');
  const params = new URLSearchParams({
    action: 'requesttoken',
    grant_type: 'refresh_token',
    client_id: clientId,
    client_secret: clientSecret,
    refresh_token: refreshToken,
  });

  try {
    const response = await axios.post('https://wbsapi.withings.net/v2/oauth2', params.toString(), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });

    if (response.data.status !== 0) {
      throw new Error(`Withings API Error: ${JSON.stringify(response.data)}`);
    }

    const body = response.data.body;
    const now = Math.floor(Date.now() / 1000);
    const updatedTokens = {
      access_token: body.access_token,
      refresh_token: body.refresh_token,
      expires_in: body.expires_in,
      expires_at: now + body.expires_in,
      userid: body.userid,
      scope: body.scope,
    };

    await saveTokensToDrive(drive, updatedTokens, fileId);
    return updatedTokens.access_token;
  } catch (error) {
    const errBody = error.response ? JSON.stringify(error.response.data) : error.message;
    throw new Error(`Withings Token Refresh Error: ${errBody}`);
  }
}
