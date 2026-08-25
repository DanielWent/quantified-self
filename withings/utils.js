import fs from 'fs';
import axios from 'axios';
import { google } from 'googleapis';
import { config } from './config.js';

export function getDriveClient() {
  if (!config.serviceAccountJson) {
    throw new Error('GOOGLE_SERVICE_ACCOUNT_JSON is not configured.');
  }

  let auth;
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
  return google.drive({ version: 'v3', auth });
}

export async function getAccessToken() {
  if (!config.clientId || !config.clientSecret || !config.refreshToken) {
    throw new Error(
      `Missing Withings credentials:\n` +
      `- WITHINGS_CLIENT_ID: ${config.clientId ? 'Present' : 'MISSING'}\n` +
      `- WITHINGS_CLIENT_SECRET: ${config.clientSecret ? 'Present' : 'MISSING'}\n` +
      `- WITHINGS_REFRESH_TOKEN: ${config.refreshToken ? 'Present' : 'MISSING'}`
    );
  }

  const params = new URLSearchParams({
    action: 'requesttoken',
    grant_type: 'refresh_token',
    client_id: config.clientId.trim(),
    client_secret: config.clientSecret.trim(),
    refresh_token: config.refreshToken.trim()
  });

  const response = await axios.post(
    'https://wbsapi.withings.net/v2/oauth2',
    params.toString(),
    {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    }
  );

  if (response.data.status !== 0) {
    throw new Error(`Withings Token Refresh Error: ${JSON.stringify(response.data)}`);
  }

  return response.data.body.access_token;
}

export function decodeMeasurements(measuregrps) {
  return measuregrps.map(group => {
    const timestamp = new Date(group.date * 1000).toISOString();
    const row = {
      timestamp,
      date: timestamp.split('T')[0],
      grpid: group.grpid
    };

    for (const measure of group.measures) {
      const typeName = config.measureTypes[measure.type];
      if (typeName) {
        row[typeName] = parseFloat((measure.value * Math.pow(10, measure.unit)).toFixed(3));
      }
    }
    return row;
  });
}
