const axios = require('axios');
const {
  CLIENT_ID,
  CLIENT_SECRET,
  REFRESH_TOKEN,
  OUTPUT_FILENAME,
  CSV_HEADERS,
  DEFAULT_USER_HEIGHT_M
} = require('./config');
const { parseMeasureGroups, csvToObjects, objectsToCsv } = require('./utils');
const { downloadFileByName, uploadCsv } = require('./drive');

async function getAccessToken() {
  try {
    const response = await axios.post('https://wbsapi.withings.net/v2/oauth2', null, {
      params: {
        action: 'requesttoken',
        grant_type: 'refresh_token',
        client_id: CLIENT_ID,
        client_secret: CLIENT_SECRET,
        refresh_token: REFRESH_TOKEN
      }
    });

    if (response.data.status !== 0) {
      throw new Error(`Withings Auth Error: status ${response.data.status}`);
    }

    return response.data.body.access_token;
  } catch (error) {
    console.error('Failed to refresh access token:', error.message);
    throw error;
  }
}

async function fetchWithingsMeasures(accessToken, lastUpdateTimestamp = 0) {
  try {
    // Requesting without restricting meastypes returns all Body Scan metrics
    const response = await axios.get('https://wbsapi.withings.net/measure', {
      headers: {
        Authorization: `Bearer ${accessToken}`
      },
      params: {
        action: 'getmeas',
        category: 1,
        lastupdate: lastUpdateTimestamp
      }
    });

    if (response.data.status !== 0) {
      throw new Error(`Withings API Error: status ${response.data.status}`);
    }

    return response.data.body.measuregrps || [];
  } catch (error) {
    console.error('Failed to fetch measures from Withings:', error.message);
    throw error;
  }
}

async function syncWithingsData() {
  console.log('Starting Withings Body Scan sync...');
  const accessToken = await getAccessToken();

  console.log('Fetching existing CSV from Google Drive...');
  const existingCsv = await downloadFileByName(OUTPUT_FILENAME);
  let existingData = [];
  let lastTimestamp = 0;

  if (existingCsv) {
    existingData = csvToObjects(existingCsv);
    if (existingData.length > 0) {
      const dates = existingData
        .map((d) => new Date(d.Date).getTime())
        .filter((t) => !isNaN(t));
      if (dates.length > 0) {
        lastTimestamp = Math.floor(Math.max(...dates) / 1000);
      }
    }
  }

  console.log(`Fetching measures from Withings (after timestamp ${lastTimestamp})...`);
  const measureGroups = await fetchWithingsMeasures(accessToken, lastTimestamp);
  console.log(`Retrieved ${measureGroups.length} measure groups.`);

  const newRows = parseMeasureGroups(measureGroups, DEFAULT_USER_HEIGHT_M);

  const mergedMap = new Map();
  existingData.forEach((row) => mergedMap.set(row.Date, row));
  newRows.forEach((row) => mergedMap.set(row.Date, row));

  const finalRows = Array.from(mergedMap.values()).sort(
    (a, b) => new Date(b.Date).getTime() - new Date(a.Date).getTime()
  );

  const updatedCsv = objectsToCsv(finalRows, CSV_HEADERS);
  await uploadCsv(OUTPUT_FILENAME, updatedCsv);
  console.log(`Successfully uploaded ${OUTPUT_FILENAME} with ${finalRows.length} total rows.`);
}

if (require.main === module) {
  syncWithingsData().catch((err) => {
    console.error('Sync failed:', err);
    process.exit(1);
  });
}

module.exports = { syncWithingsData };
