require('dotenv').config();

function getRequiredEnv(key) {
  const value = process.env[key];
  if (!value) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
  return value;
}

const config = {
  withings: {
    clientId: getRequiredEnv('WITHINGS_CLIENT_ID'),
    clientSecret: getRequiredEnv('WITHINGS_CLIENT_SECRET'),
    refreshToken: getRequiredEnv('WITHINGS_REFRESH_TOKEN'),
  },
  google: {
    folderId: getRequiredEnv('GOOGLE_DRIVE_FOLDER_ID'),
    serviceAccountJson: getRequiredEnv('GOOGLE_SERVICE_ACCOUNT_JSON'),
  },
};

function getServiceAccountCredentials() {
  const raw = config.google.serviceAccountJson;
  try {
    return JSON.parse(raw);
  } catch (err) {
    const fs = require('fs');
    if (fs.existsSync(raw)) {
      return JSON.parse(fs.readFileSync(raw, 'utf8'));
    }
    throw new Error('GOOGLE_SERVICE_ACCOUNT_JSON must be a valid JSON string or file path.');
  }
}

module.exports = {
  config,
  getServiceAccountCredentials,
};
