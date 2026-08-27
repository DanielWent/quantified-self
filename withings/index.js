const axios = require('axios');
const { config } = require('./config');
const { uploadJson } = require('./drive');

async function refreshAccessToken() {
  const response = await axios.post('https://wbsapi.withings.net/v2/oauth2', null, {
    params: {
      action: 'requesttoken',
      grant_type: 'refresh_token',
      client_id: config.withings.clientId,
      client_secret: config.withings.clientSecret,
      refresh_token: config.withings.refreshToken,
    },
  });

  if (response.data.status !== 0) {
    throw new Error(`Failed to refresh Withings token: ${JSON.stringify(response.data)}`);
  }

  return response.data.body.access_token;
}

async function fetchWithingsMeasurements(accessToken) {
  const response = await axios.get('https://wbsapi.withings.net/measure', {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    params: {
      action: 'getmeas',
      meastype: '1,5,6,8,76,77,88', // Weight, Fat Free Mass, Fat Ratio, Fat Mass, Muscle, Hydration, Bone
      category: 1,
    },
  });

  if (response.data.status !== 0) {
    throw new Error(`Failed to fetch Withings measurements: ${JSON.stringify(response.data)}`);
  }

  return response.data.body;
}

async function main() {
  try {
    console.log('Refreshing Withings access token...');
    const accessToken = await refreshAccessToken();

    console.log('Fetching body metrics from Withings...');
    const measurements = await fetchWithingsMeasurements(accessToken);

    const payload = {
      synced_at: new Date().toISOString(),
      measurements,
    };

    console.log('Uploading Withings data to Google Drive...');
    const fileId = await uploadJson('withings_data.json', payload);
    console.log(`Successfully synced Withings data. Drive File ID: ${fileId}`);
  } catch (error) {
    console.error('Error during Withings sync:', error.message);
    process.exit(1);
  }
}

main();
