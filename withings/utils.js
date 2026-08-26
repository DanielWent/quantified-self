const { MEASURE_TYPES, CSV_HEADERS, DEFAULT_USER_HEIGHT_M } = require('./config');

function formatDateTime(timestamp) {
  const d = new Date(timestamp * 1000);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function round(val, decimals = 2) {
  if (val === null || val === undefined || isNaN(val)) return '';
  return Number(Math.round(val + 'e' + decimals) + 'e-' + decimals);
}

function parseMeasureGroups(measuregrps, userHeight = DEFAULT_USER_HEIGHT_M) {
  if (!Array.isArray(measuregrps)) return [];

  return measuregrps.map((group) => {
    const row = {};
    CSV_HEADERS.forEach((header) => {
      row[header] = '';
    });

    row['Date'] = formatDateTime(group.date);

    let parsedWeight = null;
    let parsedHeight = userHeight;

    if (Array.isArray(group.measures)) {
      group.measures.forEach((m) => {
        const realValue = m.value * Math.pow(10, m.unit);
        const headerName = MEASURE_TYPES[m.type];

        if (m.type === 1) {
          parsedWeight = realValue;
          row['Weight (kg)'] = round(realValue, 2);
        } else if (m.type === 4) {
          parsedHeight = realValue;
        } else if (headerName && CSV_HEADERS.includes(headerName)) {
          row[headerName] = round(realValue, 2);
        } else if (m.type === 167 || m.type === 170) {
          row['Visceral Fat Rating'] = round(realValue, 1);
        } else if (m.type === 196) {
          row['Nerve Health Score'] = round(realValue, 1);
        } else if (m.type === 155) {
          row['Vascular Age'] = round(realValue, 1);
        } else if (m.type === 91) {
          row['Pulse Wave Velocity (m/s)'] = round(realValue, 2);
        }
      });
    }

    if (parsedWeight && parsedHeight) {
      const bmi = parsedWeight / (parsedHeight * parsedHeight);
      row['Body Mass Index'] = round(bmi, 2);
    }

    return row;
  });
}

function csvToObjects(csvString) {
  if (!csvString || !csvString.trim()) return [];
  const lines = csvString.trim().split('\n');
  if (lines.length < 2) return [];

  const headers = lines[0].split(',').map((h) => h.trim().replace(/^"|"$/g, ''));
  const objects = [];

  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    const values = line.split(',').map((v) => v.trim().replace(/^"|"$/g, ''));
    const obj = {};
    headers.forEach((h, idx) => {
      obj[h] = values[idx] !== undefined ? values[idx] : '';
    });
    objects.push(obj);
  }
  return objects;
}

function objectsToCsv(objects, headers = CSV_HEADERS) {
  const headerRow = headers.join(',');
  const rows = objects.map((obj) => {
    return headers
      .map((h) => {
        const val = obj[h] !== undefined && obj[h] !== null ? String(obj[h]) : '';
        return val.includes(',') ? `"${val}"` : val;
      })
      .join(',');
  });
  return [headerRow, ...rows].join('\n');
}

module.exports = {
  parseMeasureGroups,
  csvToObjects,
  objectsToCsv,
  formatDateTime,
  round
};
