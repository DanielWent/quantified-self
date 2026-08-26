import axios from 'axios';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import config from './config.js';
import { parseWithingsMeasures, formatWithingsCsv } from './utils.js';
import { initDriveClient, uploadFileToDrive } from './drive.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function getAccessToken(clientId, clientSecret, currentRefreshToken) {
  const params = new URLSearchParams();
  params.append('action', 'requesttoken');
  params.append('grant_type', 'refresh_token');
  params.append('client_id', clientId);
  params.append('client_secret', clientSecret);
  params.append('refresh_token', currentRefreshToken);

  const response = await axios.post('https://wbsapi.withings.net/v2/oauth2', params, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
  });

  if (response.data && response.data.status === 0 && response.data.body) {
    return response.data.body.access_token;
  }
  throw new Error(`Failed to refresh Withings token: ${JSON.stringify(response.data)}`);
}

async function fetchAllMeasurements(accessToken, startDate, endDate) {
  let allGroups = [];
  let offset = 0;
  let hasMore = true;
  let pageCount = 0;
  const MAX_PAGES = 100;

  while (hasMore && pageCount < MAX_PAGES) {
    pageCount++;
    const params = {
      action: 'getmeas',
      startdate: startDate,
      enddate: endDate,
      category: 1
    };
    if (offset > 0) {
      params.offset = offset;
    }

    const response = await axios.get('https://wbsapi.withings.net/measure', {
      params,
      headers: {
        Authorization: `Bearer ${accessToken}`
      }
    });

    if (response.data && response.data.status === 0 && response.data.body) {
      const groups = response.data.body.measuregrps || [];
      allGroups = allGroups.concat(groups);

      if (response.data.body.more && response.data.body.offset) {
        offset = response.data.body.offset;
      } else {
        hasMore = false;
      }
    } else {
      hasMore = false;
    }
  }

  return allGroups;
}

async function run() {
  const days = config.daysToSync;
  console.log(`Starting Withings sync for the past ${days} days...`);

  if (!config.clientId || !config.clientSecret || !config.refreshToken) {
    console.error('Missing Withings credentials or refresh token in environment variables.');
    process.exit(1);
  }

  try {
    const accessToken = await getAccessToken(config.clientId, config.clientSecret, config.refreshToken);
    const endDate = Math.floor(Date.now() / 1000);
    const startDate = endDate - (days * 24 * 60 * 60);

    const measureGroups = await fetchAllMeasurements(accessToken, startDate, endDate);
    const parsedData = parseWithingsMeasures(measureGroups);

    // Save JSON cache
    const jsonPath = path.join(__dirname, 'withings_data.json');
    fs.writeFileSync(jsonPath, JSON.stringify(parsedData, null, 2), 'utf-8');
    console.log(`Saved ${parsedData.length} records to ${jsonPath}`);

    // Generate withings_measurements.csv
    const csvPath = path.join(__dirname, 'withings_measurements.csv');
    const csvContent = formatWithingsCsv(parsedData);
    fs.writeFileSync(csvPath, csvContent, 'utf-8');
    console.log(`Saved ${parsedData.length} records to ${csvPath}`);

    // Upload withings_measurements.csv to Google Drive
    const drive = initDriveClient(config.googleDriveCredentials);
    if (drive) {
      await uploadFileToDrive(drive, config.googleDriveFolderId, csvPath);
    }
  } catch (error) {
    console.error('Error executing Withings sync:', error.message);
    process.exit(1);
  }
}

run();
