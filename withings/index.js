const fs = require('fs');
const path = require('path');
const axios = require('axios');
const drive = require('./drive');
const config = require('./config');

const OUTPUT_DIR = './.withings2gsheets';
const TOKEN_FILE_NAME = 'drw_tokens.json';
const LOCAL_TOKEN_PATH = path.join(OUTPUT_DIR, TOKEN_FILE_NAME);

async function ensureDirectoryExists(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

async function getOrInitTokens() {
  await ensureDirectoryExists(OUTPUT_DIR);

  // 1. Attempt to download the existing rotated tokens from Google Drive
  try {
    const driveTokenBuffer = await drive.downloadFile(TOKEN_FILE_NAME);
    if (driveTokenBuffer && driveTokenBuffer.length > 0) {
      fs.writeFileSync(LOCAL_TOKEN_PATH, driveTokenBuffer);
      console.log(`[drw] Successfully downloaded rotated ${TOKEN_FILE_NAME} from Google Drive.`);
      return JSON.parse(driveTokenBuffer.toString());
    }
  } catch (err) {
    console.warn(`[drw] No remote ${TOKEN_FILE_NAME} found on Google Drive. Checking environment fallback...`);
  }

  // 2. Fall back to local file if available
  if (fs.existsSync(LOCAL_TOKEN_PATH)) {
    console.log(`[drw] Using existing local ${TOKEN_FILE_NAME}.`);
    return JSON.parse(fs.readFileSync(LOCAL_TOKEN_PATH, 'utf8'));
  }

  // 3. Fall back to process.env.WITHINGS_REFRESH_TOKEN
  const envRefreshToken = process.env.WITHINGS_REFRESH_TOKEN || process.env.WITHINGS_DRW_REFRESH_TOKEN;
  if (envRefreshToken) {
    console.log(`[drw] Initializing ${TOKEN_FILE_NAME} from environment refresh token.`);
    const initialTokens = { refresh_token: envRefreshToken.trim() };
    fs.writeFileSync(LOCAL_TOKEN_PATH, JSON.stringify(initialTokens, null, 2));
    return initialTokens;
  }

  throw new Error("No tokens available in Google Drive, local storage, or environment variables.");
}

async function refreshAccessToken(refreshToken) {
  console.log("[drw] Attempting to refresh Withings Access Token...");
  const params = new URLSearchParams({
    action: 'requesttoken',
    grant_type: 'refresh_token',
    client_id: config.WITHINGS_CLIENT_ID,
    client_secret: config.WITHINGS_CLIENT_SECRET,
    refresh_token: refreshToken
  });

  const response = await axios.post('https://wbsapi.net/v2/oauth2', params.toString(), {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  });

  if (response.data.status !== 0 || !response.data.body?.access_token) {
    throw new Error(`Token refresh failed: ${JSON.stringify(response.data)}`);
  }

  const newTokens = response.data.body;
  fs.writeFileSync(LOCAL_TOKEN_PATH, JSON.stringify(newTokens, null, 2));

  // Persist updated tokens immediately to Google Drive
  await drive.uploadFile(LOCAL_TOKEN_PATH, TOKEN_FILE_NAME);
  console.log("[drw] Refreshed tokens successfully uploaded to Google Drive.");
  
  return newTokens;
}

async function syncWithings() {
  console.log("Starting Withings Sync Process...");
  let tokens = await getOrInitTokens();

  // Test current access token or trigger refresh sequence
  try {
    if (!tokens.access_token) {
      tokens = await refreshAccessToken(tokens.refresh_token);
    }
  } catch (err) {
    console.warn(`[WARN] [drw] Initial token invalid. Refreshing... Reason: ${err.message}`);
    tokens = await refreshAccessToken(tokens.refresh_token);
  }

  console.log("[drw] Withings client ready for data extraction.");
  // Proceed with measurement fetch and CSV generation logic...
}

if (require.main === module) {
  syncWithings().catch((err) => {
    console.error(`[ERROR] Sync failed: ${err.message}`);
    process.exit(1);
  });
}

module.exports = { syncWithings, getOrInitTokens };
