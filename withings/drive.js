const { google } = require('googleapis');
const { Readable } = require('stream');
const { config, getServiceAccountCredentials } = require('./config');

const SCOPES = ['https://www.googleapis.com/auth/drive'];

function getDriveClient() {
  const credentials = getServiceAccountCredentials();
  const auth = new google.auth.GoogleAuth({
    credentials,
    scopes: SCOPES,
  });
  return google.drive({ version: 'v3', auth });
}

async function findFileId(drive, filename) {
  const query = `name = '${filename}' and '${config.google.folderId}' in parents and trashed = false`;
  const response = await drive.files.list({
    q: query,
    spaces: 'drive',
    fields: 'files(id, name)',
  });
  const files = response.data.files;
  return files && files.length > 0 ? files[0].id : null;
}

async function uploadJson(filename, data) {
  const drive = getDriveClient();
  const fileId = await findFileId(drive, filename);
  const media = {
    mimeType: 'application/json',
    body: Readable.from([JSON.stringify(data, null, 2)]),
  };

  if (fileId) {
    const res = await drive.files.update({
      fileId,
      media,
      fields: 'id',
    });
    return res.data.id;
  } else {
    const res = await drive.files.create({
      requestBody: {
        name: filename,
        parents: [config.google.folderId],
      },
      media,
      fields: 'id',
    });
    return res.data.id;
  }
}

module.exports = {
  uploadJson,
};
