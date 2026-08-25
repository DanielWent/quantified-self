import fs from 'fs';
import axios from 'axios';
import { config } from './config.js';

export async function getAccessToken() {
  let refreshToken = config.refreshToken;

  if (fs.existsSync(config.tokenFile)) {
    const saved = JSON.parse(fs.readFileSync(config.tokenFile, 'utf8'));
    refreshToken = saved.refresh_token || refreshToken;
  }

  const params = new URLSearchParams({
    action: 'requesttoken',
    grant_type: 'refresh_token',
    client_id: config.clientId,
    client_secret: config.clientSecret,
    refresh_token: refreshToken
  });

  const response = await axios.post('https://wbsapi.withings.net/v2/oauth2', params);

  if (response.data.status !== 0) {
    throw new Error(`Withings Token Refresh Error: ${JSON.stringify(response.data)}`);
  }

  fs.writeFileSync(config.tokenFile, JSON.stringify(response.data.body, null, 2));
  return response.data.body.access_token;
}

export function decodeMeasurements(measuregrps) {
  const records = [];

  for (const group of measuregrps) {
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
    records.push(row);
  }

  return records;
}
