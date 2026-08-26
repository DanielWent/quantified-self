import dotenv from 'dotenv';
dotenv.config();

export const config = {
  clientId: process.env.WITHINGS_CLIENT_ID,
  clientSecret: process.env.WITHINGS_CLIENT_SECRET,
  refreshToken: process.env.WITHINGS_REFRESH_TOKEN,
  folderId: process.env.GOOGLE_DRIVE_FOLDER_ID,
  serviceAccountJson: process.env.GOOGLE_SERVICE_ACCOUNT_JSON,
  outputFileName: 'withings_measurements.csv',
  measureTypes: {
    1: 'weight_kg',
    4: 'height_m',
    5: 'fat_free_mass_kg',
    6: 'fat_ratio_pct',
    8: 'fat_mass_kg',
    76: 'muscle_mass_kg',
    77: 'hydration_kg',
    88: 'bone_mass_kg',
    91: 'pulse_wave_velocity_mps',
    130: 'vascular_age'
  }
};
