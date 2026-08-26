import fs from 'fs';
import axios from 'axios';
import { google } from 'googleapis';
import { config } from './config.js';

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

export async function getAccessToken() {
  if (!config.clientId || !config.clientSecret || !config.refreshToken) {
    throw new Error('Missing Withings credentials in environment variables.');
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
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    }
  );

  if (response.data.status !== 0) {
    throw new Error(`Withings Token Refresh Error: ${JSON.stringify(response.data)}`);
  }

  return response.data.body.access_token;
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
