import axios from 'axios';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import config from './config.js';
import { parseWithingsMeasures } from './utils.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function getAccessToken(clientId, clientSecret, refreshToken) {
  const response = await axios.post('https://wbsapi.withings.net/v2/oauth2', null, {
    params: {
      action: 'requesttoken',
      grant_type: 'refresh_token',
      client_id: clientId,
      client_secret: clientSecret,
      refresh_token: refreshToken
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
    console.error('Missing Withings credentials in environment variables.');
    process.exit(1);
  }

  try {
    const accessToken = await getAccessToken(config.clientId, config.clientSecret, config.refreshToken);
    const endDate = Math.floor(Date.now() / 1000);
    const startDate = endDate - (days * 24 * 60 * 60);

    const measureGroups = await fetchAllMeasurements(accessToken, startDate, endDate);
    const parsedData = parseWithingsMeasures(measureGroups);

    const outputPath = path.join(__dirname, 'withings_data.json');
    fs.writeFileSync(outputPath, JSON.stringify(parsedData, null, 2), 'utf-8');
    console.log(`Saved ${parsedData.length} records to ${outputPath}`);
  } catch (error) {
    console.error('Error executing Withings sync:', error.message);
    process.exit(1);
  }
}

run();
