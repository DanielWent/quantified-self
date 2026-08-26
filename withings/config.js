require('dotenv').config();

const parsedDays = parseInt(process.argv[2] || process.env.DAYS_TO_SYNC || process.env.DAYS || '7', 10);

module.exports = {
  clientId: process.env.WITHINGS_CLIENT_ID,
  clientSecret: process.env.WITHINGS_CLIENT_SECRET,
  refreshToken: process.env.WITHINGS_REFRESH_TOKEN,
  spreadsheetKey: process.env.GOOGLE_SPREADSHEET_KEY,
  googleCredentials: process.env.GOOGLE_SHEETS_CREDENTIALS,
  days: isNaN(parsedDays) ? 7 : parsedDays,
};
