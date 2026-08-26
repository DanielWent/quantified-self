export const MEASURE_TYPES = {
  1: 'weight_kg',
  4: 'height_m',
  5: 'fat_free_mass_kg',
  6: 'fat_ratio_pct',
  8: 'fat_mass_weight_kg',
  76: 'muscle_mass_kg',
  77: 'hydration_kg',
  88: 'bone_mass_kg',
  91: 'pulse_wave_velocity_ms',
  123: 'visceral_fat',
  130: 'vascular_age',
  168: 'nerve_health_score'
};

export function parseWithingsMeasures(measureGroups) {
  if (!Array.isArray(measureGroups)) {
    return [];
  }

  const dailyRecords = {};

  for (const group of measureGroups) {
    if (!group || !group.date || !Array.isArray(group.measures)) {
      continue;
    }

    const dateStr = new Date(group.date * 1000).toISOString().split('T')[0];
    if (!dailyRecords[dateStr]) {
      dailyRecords[dateStr] = {
        date: dateStr,
        timestamp: group.date,
        measures: {}
      };
    }

    for (const measure of group.measures) {
      if (!measure || measure.type === undefined || measure.value === undefined) {
        continue;
      }
      const typeName = MEASURE_TYPES[measure.type] || `type_${measure.type}`;
      const actualValue = measure.value * Math.pow(10, measure.unit || 0);
      dailyRecords[dateStr].measures[typeName] = actualValue;
    }
  }

  return Object.values(dailyRecords).sort((a, b) => b.date.localeCompare(a.date));
}

export function formatWithingsCsv(records) {
  const headers = [
    "Date", "Weight (kg)", "Fat Ratio (%)", "Fat Mass (kg)", "Muscle Mass (kg)",
    "Hydration (kg)", "Bone Mass (kg)", "Pulse Wave Velocity (m/s)",
    "Visceral Fat", "Vascular Age", "Nerve Health Score"
  ];

  const rows = [headers.join(",")];

  for (const r of records) {
    const m = r.measures || {};
    const row = [
      r.date || "",
      m.weight_kg !== undefined ? m.weight_kg.toFixed(2) : "",
      m.fat_ratio_pct !== undefined ? m.fat_ratio_pct.toFixed(2) : "",
      m.fat_mass_weight_kg !== undefined ? m.fat_mass_weight_kg.toFixed(2) : "",
      m.muscle_mass_kg !== undefined ? m.muscle_mass_kg.toFixed(2) : "",
      m.hydration_kg !== undefined ? m.hydration_kg.toFixed(2) : "",
      m.bone_mass_kg !== undefined ? m.bone_mass_kg.toFixed(2) : "",
      m.pulse_wave_velocity_ms !== undefined ? m.pulse_wave_velocity_ms.toFixed(2) : "",
      m.visceral_fat !== undefined ? m.visceral_fat : "",
      m.vascular_age !== undefined ? m.vascular_age : "",
      m.nerve_health_score !== undefined ? m.nerve_health_score : ""
    ];
    rows.push(row.join(","));
  }

  return rows.join("\n");
}
