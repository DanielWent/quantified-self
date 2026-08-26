import 'dotenv/config';

const config = {
  clientId: process.env.WITHINGS_CLIENT_ID,
  clientSecret: process.env.WITHINGS_CLIENT_SECRET,
  refreshToken: process.env.WITHINGS_REFRESH_TOKEN,
  googleDriveCredentials: process.env.GOOGLE_SERVICE_ACCOUNT_JSON || process.env.GOOGLE_DRIVE_CREDENTIALS,
  googleDriveFolderId: process.env.GOOGLE_DRIVE_FOLDER_ID,
  daysToSync: parseInt(process.env.DAYS_TO_SYNC, 10) || 7
};

export default config;
