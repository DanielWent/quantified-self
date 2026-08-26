import os
from dotenv import load_dotenv

load_dotenv()

GARMIN_TOKENS = os.getenv("GARMIN_TOKENS")
GARMIN_EMAIL = os.getenv("GARMIN_EMAIL")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")
GOOGLE_DRIVE_CREDENTIALS = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") or os.getenv("GOOGLE_DRIVE_CREDENTIALS")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

try:
    DAYS_TO_SYNC = int(os.getenv("DAYS_TO_SYNC", "7"))
except (ValueError, TypeError):
    DAYS_TO_SYNC = 7

# Exact spreadsheet names matching the target files
GARMIN_DATA_FILENAME = "drw_garmin_data.csv"
GARMIN_ACTIVITIES_FILENAME = "drw_garmin_activities_list.csv"

# Daily Data Schema Headers (43 columns)
GARMIN_DATA_HEADERS = [
    "Date (YYYY-MM-DD)",
    "User Name",
    "User Age",
    "User Gender",
    "Physiological Maximum Heart Rate (bpm)",
    "VO2 Max (ml/kg/min)",
    "VO2 Max Percentile (Age-Gender Adjusted)",
    "Lactate Threshold Pace (min/km)",
    "Lactate Threshold Heart Rate (bpm)",
    "Garmin Sleep Score (0-100)",
    "Sleep Start Time",
    "Sleep End Time",
    "Deep Sleep (min)",
    "Light Sleep (min)",
    "REM Sleep (min)",
    "Awake Time (min)",
    "Sleep Length (min)",
    "Sleep Need (min)",
    "Overnight Average Pulse Ox / SpO2 (%)",
    "Garmin Average Stress Score (0-100)",
    "Daily Min Body Battery (0-100)",
    "Daily Max Body Battery (0-100)",
    "Body Battery Charged (0-100)",
    "Body Battery Drained (0-100)",
    "Daily Steps",
    "Daily Floors Climbed",
    "Daily Intensity Minutes",
    "Total Calories (kcal)",
    "Systolic Blood Pressure (mmHg)",
    "Diastolic Blood Pressure (mmHg)",
    "Garmin Training Load (7 Day Sum)",
    "Garmin Training Load Focus",
    "Morning Garmin Training Readiness (0-100)",
    "Overnight Resting HR (bpm)",
    "Overnight HRV (ms)",
    "Garmin HRV Status (Text Label)",
    "Garmin Training Status (Text Label)",
    "Total Walking Distance (km)",
    "Total Walking Duration (min)",
    "Total Running Activities Count",
    "Total Running Distance (km)",
    "Total Running Duration (min)",
    "Total Strength Training Duration (min)"
]

# Activity Data Schema Headers (38 columns)
GARMIN_ACTIVITIES_HEADERS = [
    "Activity ID",
    "Date (YYYY-MM-DD)",
    "Start Time (HH:MM)",
    "Activity Type",
    "Activity Name",
    "Distance (km)",
    "Duration (min)",
    "Avg Pace (min/km)",
    "Average Grade Adjusted Pace (min/km)",
    "Total Ascent (m)",
    "Total Descent (m)",
    "Feels Like Temperature (Celsius)",
    "Weather Condition",
    "Sustained Wind Speed (km/h)",
    "Avg HR (bpm)",
    "Max HR (bpm)",
    "Average Cadence (spm)",
    "Average Stride Length (m)",
    "Average Ground Contact Time (ms)",
    "Vertical Oscillation (cm)",
    "Aerobic Training Effect (0.0-5.0)",
    "Anaerobic Training Effect (0.0-5.0)",
    "Activity Training Load",
    "Avg Power (Watts)",
    "Max Power (Watts)",
    "Normalized Power (Watts)",
    "Estimated Sweat Loss (ml)",
    "Garmin Training Effect Label",
    "HR Zone 1 (min)",
    "HR Zone 2 (min)",
    "HR Zone 3 (min)",
    "HR Zone 4 (min)",
    "HR Zone 5 (min)",
    "Power Zone 1 (min)",
    "Power Zone 2 (min)",
    "Power Zone 3 (min)",
    "Power Zone 4 (min)",
    "Power Zone 5 (min)"
]
