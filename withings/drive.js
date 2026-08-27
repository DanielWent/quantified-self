const fs = require('fs');
const path = require('path');
const { google } = require('googleapis');
const config = require('./config');

let driveClient = null;

/**
 * Initializes and caches the Google Drive v3 client using Service Account credentials.
 */
function getDriveClient() {
  if (driveClient) {
    return driveClient;
  }

  let credentials;
  if (process.env.GOOGLE_SERVICE_ACCOUNT_KEY) {
    try {
      credentials = JSON.parse(process.env.GOOGLE_SERVICE_ACCOUNT_KEY);
    } catch (e) {
      throw new Error(`Failed to parse GOOGLE_SERVICE_ACCOUNT_KEY environment variable: ${e.message}`);
    }
  } else if (config.GOOGLE_CREDENTIALS_PATH && fs.existsSync(config.GOOGLE_CREDENTIALS_PATH)) {
    credentials = JSON.parse(fs.readFileSync(config.GOOGLE_CREDENTIALS_PATH, 'utf8'));
  } else if (fs.existsSync('credentials.json')) {
    credentials = JSON.parse(fs.readFileSync('credentials.json', 'utf8'));
  } else {
    throw new Error('Google Drive credentials not found in environment or local file.');
  }

  const auth = new google.auth.GoogleAuth({
    credentials,
    scopes: ['https://www.googleapis.com/auth/drive'],
  });

  driveClient = google.drive({ version: 'v3', auth });
  return driveClient;
}

/**
 * Searches for an existing file by name (and optional folder).
 * @param {string} fileName 
 * @param {string} [folderId]
 * @returns {Promise<{id: string, name: string}|null>}
 */
async function findFile(fileName, folderId = null) {
  const drive = getDriveClient();
  let query = `name = '${fileName}' and trashed = false`;
  
  const targetFolderId = folderId || config.GOOGLE_DRIVE_FOLDER_ID;
  if (targetFolderId) {
    query += ` and '${targetFolderId}' in parents`;
  }

  const res = await drive.files.list({
    q: query,
    fields: 'files(id, name)',
    spaces: 'drive',
    supportsAllDrives: true,
    includeItemsFromAllDrives: true,
  });

  if (res.data.files && res.data.files.length > 0) {
    return res.data.files[0];
  }
  return null;
}

/**
 * Downloads a file from Google Drive as a Buffer.
 * Returns null if the file does not exist.
 * @param {string} fileName
 * @param {string} [folderId]
 * @returns {Promise<Buffer|null>}
 */
async function downloadFile(fileName, folderId = null) {
  const drive = getDriveClient();
  const file = await findFile(fileName, folderId);

  if (!file) {
    return null;
  }

  try {
    const res = await drive.files.get(
      {
        fileId: file.id,
        alt: 'media',
        supportsAllDrives: true,
      },
      { responseType: 'arraybuffer' }
    );

    return Buffer.from(res.data);
  } catch (error) {
    if (error.response && error.response.status === 404) {
      return null;
    }
    throw new Error(`Failed to download ${fileName} (ID: ${file.id}) from Google Drive: ${error.message}`);
  }
}

/**
 * Uploads or updates a file on Google Drive.
 * @param {string} filePath - Path to the local file to upload
 * @param {string} fileName - Destination file name on Google Drive
 * @param {string} [mimeType='application/json']
 * @param {string} [folderId]
 * @returns {Promise<string>} Uploaded file ID
 */
async function uploadFile(filePath, fileName, mimeType = 'application/json', folderId = null) {
  const drive = getDriveClient();
  const targetFolderId = folderId || config.GOOGLE_DRIVE_FOLDER_ID;

  if (!fs.existsSync(filePath)) {
    throw new Error(`Local file not found for upload: ${filePath}`);
  }

  const fileStats = fs.statSync(filePath);
  if (fileStats.size === 0) {
    throw new Error(`Refusing to upload 0-byte file (${fileName}) to Google Drive.`);
  }

  const existingFile = await findFile(fileName, targetFolderId);
  const media = {
    mimeType: mimeType,
    body: fs.createReadStream(filePath),
  };

  if (existingFile) {
    const res = await drive.files.update({
      fileId: existingFile.id,
      media: media,
      fields: 'id, name',
      supportsAllDrives: true,
    });
    return res.data.id;
  } else {
    const fileMetadata = {
      name: fileName,
      parents: targetFolderId ? [targetFolderId] : [],
    };
    const res = await drive.files.create({
      resource: fileMetadata,
      media: media,
      fields: 'id, name',
      supportsAllDrives: true,
    });
    return res.data.id;
  }
}

module.exports = {
  getDriveClient,
  findFile,
  downloadFile,
  uploadFile,
};
