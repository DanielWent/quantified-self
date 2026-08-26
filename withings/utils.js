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

  return Object.values(dailyRecords).sort((a, b) => a.date.localeCompare(b.date));
}
