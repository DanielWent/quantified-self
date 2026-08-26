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

  const response = await axios.post(
    'https://wbsapi.withings.net/measure',
    params.toString(),
    {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    }
  );

  if (response.data.status !== 0) {
    throw new Error(`Withings API Error: ${JSON.stringify(response.data)}`);
  }

  return decodeMeasurements(response.data.body.measuregrps || []);
}

async function getExistingDriveCSV(drive, filename, folderId) {
  const query = `name = '${filename}' and '${folderId}' in parents and trashed = false`;
  const res = await drive.files.list({
    q: query,
    fields: 'files(id, name)',
    supportsAllDrives: true,
    includeItemsFromAllDrives: true
  });
  if (!res.data.files.length) return { fileId: null, rows: [] };

  const fileId = res.data.files[0].id;
  const fileData = await drive.files.get({ fileId, alt: 'media', supportsAllDrives: true }, { responseType: 'text' });
  const lines = (fileData.data || '').trim().split('\n');
  if (lines.length <= 1 || !lines[0]) return { fileId, rows: [] };

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
    await drive.files.update({
      fileId,
      media,
      supportsAllDrives: true
    });
  } else {
    await drive.files.create({
      resource: { name: filename, parents: [folderId] },
      media,
      fields: 'id',
      supportsAllDrives: true
    });
  }
}

async function main() {
  try {
    const days = getDaysArg();
    const drive = getDriveClient();
    const newDailyRecords = await fetchWithingsData(days);

    const { fileId, rows: existingRows } = await getExistingDriveCSV(drive, config.outputFileName, config.folderId);

    const headers = [
      'date',
      'weight_kg',
      'fat_ratio_pct',
      'fat_mass_kg',
      'fat_free_mass_kg',
      'muscle_mass_kg',
      'hydration_kg',
      'bone_mass_kg',
      'pulse_wave_velocity_mps',
      'vascular_age'
    ];

    const recordMap = new Map();
    existingRows.forEach(row => {
      if (row.date) recordMap.set(row.date, row);
    });

    newDailyRecords.forEach(record => {
      const existing = recordMap.get(record.date) || {};
      recordMap.set(record.date, { ...existing, ...record });
    });

    const sortedRows = Array.from(recordMap.values()).sort((a, b) => a.date.localeCompare(b.date));
    const csvContent = [
      headers.join(','),
      ...sortedRows.map(row => headers.map(h => row[h] !== undefined && row[h] !== null ? row[h] : '').join(','))
    ].join('\n');

    await uploadCSVToDrive(drive, config.outputFileName, config.folderId, fileId, csvContent);
    console.log(`Withings sync complete (${days} days requested). Total Drive rows: ${sortedRows.length}`);
  } catch (err) {
    console.error('Error in Withings sync:', err);
    process.exit(1);
  }
}

main();
