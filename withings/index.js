import { Readable } from 'stream';
import axios from 'axios';
import { config } from './config.js';
import { getDriveClient, getAccessToken, decodeMeasurements } from './utils.js';

function getDaysArg() {
  const daysIndex = process.argv.indexOf('--days');
  if (daysIndex !== -1 && process.argv[daysIndex + 1]) {
    const parsed = parseInt(process.argv[daysIndex + 1], 10);
    return isNaN(parsed) ? 7 : parsed;
  }
  return 7;
}

async function fetchWithingsData(daysBack = 7) {
  const token = await getAccessToken();
  const startTimestamp = Math.floor(Date.now() / 1000) - (daysBack * 86400);

  const params = new URLSearchParams({
    action: 'getmeas',
    startdate: startTimestamp,
    category: 1
  });

  const response = await axios.post('https://wbsapi.withings.net/measure', params, {
    headers: { Authorization: `Bearer ${token}` }
  });

  if (response.data.status !== 0) {
    throw new Error(`Failed to fetch measurements: ${JSON.stringify(response.data)}`);
  }

  return decodeMeasurements(response.data.body.measuregrps || []);
}

async function getExistingDriveCSV(drive, filename, folderId) {
  const query = `name = '${filename}' and '${folderId}' in parents and trashed = false`;
  const res = await drive.files.list({ q: query, fields: 'files(id, name)' });
  if (!res.data.files.length) return { fileId: null, rows: [] };

  const fileId = res.data.files[0].id;
  const fileData = await drive.files.get({ fileId, alt: 'media' }, { responseType: 'text' });
  const lines = fileData.data.trim().split('\n');
  const headers = lines[0].split(',');
  const rows = lines.slice(1).map(line => {
    const vals = line.split(',');
    return headers.reduce((acc, h, i) => { acc[h] = vals[i]; return acc; }, {});
  });
  return { fileId, rows };
}

async function uploadCSVToDrive(drive, filename, folderId, fileId, csvContent) {
  const media = {
    mimeType: 'text/csv',
    body: Readable.from([csvContent])
  };

  if (fileId) {
    await drive.files.update({ fileId, media });
  } else {
    await drive.files.create({
      resource: { name: filename, parents: [folderId] },
      media,
      fields: 'id'
    });
  }
}

async function main() {
  try {
    const days = getDaysArg();
    const drive = getDriveClient();
    const records = await fetchWithingsData(days);

    const { fileId, rows: existingRows } = await getExistingDriveCSV(drive, config.outputFileName, config.folderId);
    const headers = ['timestamp', 'date', 'grpid', 'weight_kg', 'fat_ratio_pct', 'fat_mass_kg', 'muscle_mass_kg', 'hydration_kg', 'bone_mass_kg', 'pulse_wave_velocity_mps', 'vascular_age'];

    // Map existing rows by group ID and overwrite/add the newly fetched records
    const recordMap = new Map();
    existingRows.forEach(r => recordMap.set(String(r.grpid), r));
    records.forEach(r => recordMap.set(String(r.grpid), r));

    const sortedRows = Array.from(recordMap.values()).sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    const csvContent = [
      headers.join(','),
      ...sortedRows.map(row => headers.map(h => row[h] !== undefined ? row[h] : '').join(','))
    ].join('\n');

    await uploadCSVToDrive(drive, config.outputFileName, config.folderId, fileId, csvContent);
    console.log(`Withings sync complete for past ${days} days. Total rows on Drive: ${sortedRows.length}`);
  } catch (err) {
    console.error('Error running Withings sync:', err);
    process.exit(1);
  }
}

main();
