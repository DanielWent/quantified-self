const config = require('./config');
const { getAccessToken, getMeasurements, getSleepSummary, updateWithingsSheet } = require('./utils');

async function run() {
  const daysToFetch = config.days;
  console.log(`Starting Withings sync for the past ${daysToFetch} days...`);
  
  const accessToken = await getAccessToken(config.clientId, config.clientSecret, config.refreshToken);
  
  const endTimestamp = Math.floor(Date.now() / 1000);
  const startTimestamp = endTimestamp - (daysToFetch * 24 * 60 * 60);

  const [measurements, sleepData] = await Promise.all([
    getMeasurements(accessToken, startTimestamp, endTimestamp),
    getSleepSummary(accessToken, startTimestamp, endTimestamp),
  ]);

  await updateWithingsSheet(config.spreadsheetKey, config.googleCredentials, measurements, sleepData);
  console.log(`Successfully synced Withings data for ${daysToFetch} days.`);
}

run().catch((err) => {
  console.error('Error during Withings sync:', err);
  process.exit(1);
});
