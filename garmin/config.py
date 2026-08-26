import os
from dotenv import load_dotenv

load_dotenv()

# Garmin Credentials & Tokens
GARMIN_EMAIL = os.getenv("GARMIN_EMAIL")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")
GARMIN_TOKEN_STORE = os.getenv("GARMIN_TOKEN_STORE", "~/.garminconnect")

# Google Drive Settings
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
GOOGLE_PARENT_FOLDER_ID = os.getenv("GOOGLE_PARENT_FOLDER_ID")

# Output Filenames
GARMIN_DATA_FILENAME = "drw_garmin_data.csv"
GARMIN_ACTIVITIES_FILENAME = "drw_garmin_activities_list.csv"

# Daily Data Schema Headers
GARMIN_DATA_HEADERS = [
    "Date",
    "Total Steps",
    "Daily Step Goal",
    "Total Distance (km)",
    "Resting Heart Rate (bpm)",
    "Min Heart Rate (bpm)",
    "Max Heart Rate (bpm)",
    "Average Stress Level",
    "Max Stress Level",
    "Rest Stress Duration (min)",
    "Low Stress Duration (min)",
    "Medium Stress Duration (min)",
    "High Stress Duration (min)",
    "Sleep Duration (hrs)",
    "Deep Sleep (hrs)",
    "Light Sleep (hrs)",
    "REM Sleep (hrs)",
    "Awake (hrs)",
    "Sleep Score",
    "Sleep Quality",
    "Overnight Avg HRV (ms)",
    "Overnight 5-Min High HRV (ms)",
    "HRV Status",
    "Body Battery Lowest",
    "Body Battery Highest",
    "Body Battery Charged",
    "Body Battery Drained",
    "Active Kilocalories (kcal)",
    "Total Kilocalories (kcal)",
    "Floors Ascended",
    "Floors Descended",
    "Running VO2 Max",
    "Lowest Respiration (brpm)",
    "Highest Respiration (brpm)",
    "Avg Waking Respiration (brpm)",
    "Avg Overnight Respiration (brpm)",
    "Avg SpO2 (%)",
    "Lowest SpO2 (%)",
]

# Activity Data Schema Headers
GARMIN_ACTIVITIES_HEADERS = [
    "Activity ID",
    "Activity Name",
    "Activity Type",
    "Start Time",
    "Distance (km)",
    "Duration (min)",
    "Elapsed Duration (min)",
    "Moving Duration (min)",
    "Average Speed (km/h)",
    "Max Speed (km/h)",
    "Average Pace (min/km)",
    "Average Heart Rate (bpm)",
    "Max Heart Rate (bpm)",
    "Average Cadence (spm)",
    "Max Cadence (spm)",
    "Calories (kcal)",
    "Total Elevation Gain (m)",
    "Total Elevation Loss (m)",
    "Min Elevation (m)",
    "Max Elevation (m)",
    "Average Stride Length (m)",
    "Aerobic Training Effect",
    "Anaerobic Training Effect",
    "VO2 Max",
    "Steps",
]
