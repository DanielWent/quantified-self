import fs from 'fs';
import path from 'path';
import axios from 'axios';
import { config } from './config.js';
import { getAccessToken, decodeMeasurements } from './utils.js';

async function fetchWithingsData(lastUpdate = 0) {
  const token = await getAccessToken();
  const params = new URLSearchParams({
    action: 'getmeas',
    lastupdate: lastUpdate
  });

  const response = await axios.post('https://wbsapi.withings.net/measure', params, {
    headers: { Authorization: `Bearer ${token}` }
  });

  if (response.data.status !== 0) {
    throw new Error(`Failed to fetch measurements: ${JSON.stringify(response.data)}`);
  }

  return decodeMeasurements(response.data.body.measuregrps || []);
}

function updateCSV(newRecords, filePath) {
  const absolutePath = path.resolve(filePath);
  fs.mkdirSync(path.dirname(absolutePath), { recursive: true });

  let existing = [];
  const headers = ['timestamp', 'date', 'grpid', 'weight_kg', 'fat_ratio_pct', 'fat_mass_kg', 'muscle_mass_kg', 'hydration_kg', 'bone_mass_kg', 'pulse_wave_velocity_mps', 'vascular_age'];

  if (fs.existsSync(absolutePath)) {
    const content = fs.readFileSync(absolutePath, 'utf8').trim().split('\n');
    const existingHeaders = content[0].split(',');
    existing = content.slice(1).map(line => {
      const vals = line.split(',');
      return existingHeaders.reduce((acc, h, i) => {
        acc[h] = vals[i];
        return acc;
      }, {});
    });
  }

  const mergedMap = new Map();
  existing.forEach(r => mergedMap.set(String(r.grpid), r));
  newRecords.forEach(r => mergedMap.set(String(r.grpid), r));

  const sortedRows = Array.from(mergedMap.values()).sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

  const csvContent = [
    headers.join(','),
    ...sortedRows.map(row => headers.map(h => row[h] !== undefined ? row[h] : '').join(','))
  ].join('\n');

  fs.writeFileSync(absolutePath, csvContent, 'utf8');
}

async function main() {
  try {
    const records = await fetchWithingsData(0);
    if (records.length > 0) {
      updateCSV(records, config.outputCsv);
      console.log(`Successfully synced ${records.length} Withings entries.`);
    }
  } catch (err) {
    console.error('Error running Withings sync:', err);
    process.exit(1);
  }
}

main();
