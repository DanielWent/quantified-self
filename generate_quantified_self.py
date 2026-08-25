import io
import json
import os
import re
import sys
from typing import Optional, Union
import numpy as np
import pandas as pd

# ==========================================
# Configurable Demographic & Export Settings
# ==========================================
AGE: int = 40
HEIGHT_CM: int = 185
MAX_HR: int = 185

OUTPUT_FILE: str = "quantified_self_data.csv"
DAYS_TO_EXPORT: int = 730

LOCAL_GARMIN_CSV: str = "garmin_data.csv"
LOCAL_WITHINGS_CSV: str = "withings_data.csv"


# ==========================================
# Parsing & Formatting Utilities
# ==========================================
def parse_pace_to_decimal(pace_val: Union[str, float, int, None]) -> Optional[float]:
    """Converts MM:SS or numeric pace representation to decimal minutes (e.g., 04:30 -> 4.5)."""
    if pd.isna(pace_val) or pace_val == "" or pace_val is None:
        return np.nan
    pace_str = str(pace_val).strip()
    if ":" in pace_str:
        parts = pace_str.split(":")
        try:
            minutes = float(parts[0])
            seconds = float(parts[1])
            return round(minutes + (seconds / 60.0), 2)
        except (ValueError, IndexError):
            return np.nan
    try:
        val = float(pace_str)
        return round(val, 2) if val > 0 else np.nan
    except ValueError:
        return np.nan


def parse_time_to_hh_mm(time_val: Union[str, pd.Timestamp, None]) -> Optional[str]:
    """Formats sleep start and end timestamps into strict 24-hour HH:MM strings."""
    if pd.isna(time_val) or time_val == "" or time_val is None:
        return np.nan
    try:
        ts = pd.to_datetime(time_val)
        return ts.strftime("%H:%M")
    except Exception:
        match = re.search(r"(\d{1,2}):(\d{2})", str(time_val))
        if match:
            return f"{int(match.group(1)):02d}:{match.group(2)}"
        return np.nan


# ==========================================
# Google Drive Integration
# ==========================================
def get_drive_service():
    """Initializes Google Drive API client from environment variables."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds_raw = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_raw:
        return None

    try:
        creds_dict = json.loads(creds_raw)
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=["https://www.googleapis.com/auth/drive"]
        )
        return build("drive", "v3", credentials=credentials)
    except Exception as e:
        print(f"Failed to initialize Drive service: {e}")
        return None


def fetch_csv_from_drive_or_local(filename: str, service) -> pd.DataFrame:
    """Loads CSV from local file path or downloads directly from Google Drive."""
    # Check local filesystem first
    possible_paths = [
        filename,
        os.path.join("garmin", filename),
        os.path.join("withings", filename),
    ]
    for p in possible_paths:
        if os.path.exists(p):
            print(f"Loading local file: {p}")
            return pd.read_csv(p)

    # If not found locally, fetch from Drive
    if service:
        folder_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID")
        query = f"name = '{filename}' and trashed = false"
        if folder_id:
            query += f" and '{folder_id}' in parents"

        response = service.files().list(q=query, fields="files(id, name)").execute()
        files = response.get("files", [])
        if files:
            file_id = files[0]["id"]
            print(f"Downloading {filename} from Google Drive (ID: {file_id})...")
            content = service.files().get_media(fileId=file_id).execute()
            return pd.read_csv(io.BytesIO(content))

    return pd.DataFrame()


def upload_quantified_self_to_drive(file_path: str, service) -> None:
    """Uploads or replaces the final CSV file on Google Drive."""
    if not service:
        print("Google Drive credentials not found. File saved locally only.")
        return

    from googleapiclient.http import MediaFileUpload

    file_name = os.path.basename(file_path)
    folder_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID")

    query = f"name = '{file_name}' and trashed = false"
    if folder_id:
        query += f" and '{folder_id}' in parents"

    response = service.files().list(q=query, fields="files(id, name)").execute()
    files = response.get("files", [])

    media = MediaFileUpload(file_path, mimetype="text/csv", resumable=True)

    if files:
        file_id = files[0]["id"]
        print(f"Updating existing '{file_name}' on Google Drive (ID: {file_id})...")
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        print(f"Creating new '{file_name}' on Google Drive...")
        file_metadata = {"name": file_name}
        if folder_id:
            file_metadata["parents"] = [folder_id]
        service.files().create(body=file_metadata, media_body=media).execute()

    print("Google Drive sync completed successfully.")


# ==========================================
# Core Data Pipeline
# ==========================================
def build_quantified_self_dataset() -> None:
    drive_service = get_drive_service()

    garmin_df = fetch_csv_from_drive_or_local(LOCAL_GARMIN_CSV, drive_service)
    withings_df = fetch_csv_from_drive_or_local(LOCAL_WITHINGS_CSV, drive_service)

    if garmin_df.empty and withings_df.empty:
        raise ValueError("Could not locate Garmin or Withings datasets locally or on Google Drive.")

    # 1. Standardize date column across source dataframes
    for df_source in [garmin_df, withings_df]:
        if not df_source.empty:
            date_col = next(
                (c for c in df_source.columns if c.lower() in ["date", "date_yyyy_mm_dd", "day"]),
                df_source.columns[0],
            )
            df_source["Date_YYYY_MM_DD"] = pd.to_datetime(df_source[date_col]).dt.strftime("%Y-%m-%d")

    # 2. Outer merge on Date across entire historical timeline
    if not garmin_df.empty and not withings_df.empty:
        merged = pd.merge(garmin_df, withings_df, on="Date_YYYY_MM_DD", how="outer")
    elif not garmin_df.empty:
        merged = garmin_df
    else:
        merged = withings_df

    merged["Date_YYYY_MM_DD"] = pd.to_datetime(merged["Date_YYYY_MM_DD"])
    merged = merged.sort_values("Date_YYYY_MM_DD").reset_index(drop=True)

    # 3. Continuous daily calendar reindexing (1 row = 1 calendar day)
    full_date_range = pd.date_range(
        start=merged["Date_YYYY_MM_DD"].min(),
        end=merged["Date_YYYY_MM_DD"].max(),
        freq="D",
    )
    df = (
        merged.set_index("Date_YYYY_MM_DD")
        .reindex(full_date_range)
        .rename_axis("Date_YYYY_MM_DD")
        .reset_index()
    )
    df["Date_YYYY_MM_DD"] = df["Date_YYYY_MM_DD"].dt.strftime("%Y-%m-%d")

    # Helper function for case-insensitive column matching
    def get_source_series(candidates, default_val=np.nan):
        for candidate in candidates:
            for col in df.columns:
                if col.lower() == candidate.lower():
                    return df[col]
        return pd.Series(default_val, index=df.index)

    # 4. Map and cast raw pass-through columns
    df["Daily_Running_Distance_km"] = pd.to_numeric(
        get_source_series(["Daily_Running_Distance_km", "running_distance_km", "running_distance", "run_distance"]),
        errors="coerce",
    )
    df["Daily_Running_Duration_min"] = pd.to_numeric(
        get_source_series(["Daily_Running_Duration_min", "running_duration_min", "running_duration", "run_duration"]),
        errors="coerce",
    )
    df["Daily_Walking_Distance_km"] = pd.to_numeric(
        get_source_series(["Daily_Walking_Distance_km", "walking_distance_km", "walking_distance", "walk_distance"]),
        errors="coerce",
    )
    df["Daily_Strength_Duration_min"] = pd.to_numeric(
        get_source_series(["Daily_Strength_Duration_min", "strength_duration_min", "strength_duration"]),
        errors="coerce",
    )
    df["Daily_Steps_Count"] = pd.to_numeric(
        get_source_series(["Daily_Steps_Count", "steps", "step_count", "total_steps"]),
        errors="coerce",
    )
    df["Garmin_7d_Training_Load_Sum"] = pd.to_numeric(
        get_source_series(["Garmin_7d_Training_Load_Sum", "training_load_7d", "training_load", "training_load_sum"]),
        errors="coerce",
    )
    df["Garmin_VO2_Max_ml_kg_min"] = pd.to_numeric(
        get_source_series(["Garmin_VO2_Max_ml_kg_min", "vo2_max", "vo2max", "garmin_vo2_max"]),
        errors="coerce",
    )

    raw_pace = get_source_series(["Lactate_Threshold_Pace_decimal_min_km", "lactate_threshold_pace", "lt_pace", "threshold_pace"])
    df["Lactate_Threshold_Pace_decimal_min_km"] = raw_pace.apply(parse_pace_to_decimal).astype(float).round(2)

    df["Lactate_Threshold_Heart_Rate_bpm"] = pd.to_numeric(
        get_source_series(["Lactate_Threshold_Heart_Rate_bpm", "lactate_threshold_hr", "lt_hr", "threshold_heart_rate"]),
        errors="coerce",
    )
    df["Overnight_Sleep_Duration_min"] = pd.to_numeric(
        get_source_series(["Overnight_Sleep_Duration_min", "sleep_duration_min", "sleep_duration", "total_sleep_minutes"]),
        errors="coerce",
    )

    raw_start = get_source_series(["Sleep_Start_Time_HH_MM", "sleep_start_time", "sleep_start"])
    raw_end = get_source_series(["Sleep_End_Time_HH_MM", "sleep_end_time", "sleep_end"])
    df["Sleep_Start_Time_HH_MM"] = raw_start.apply(parse_time_to_hh_mm)
    df["Sleep_End_Time_HH_MM"] = raw_end.apply(parse_time_to_hh_mm)

    df["Overnight_Resting_Heart_Rate_bpm"] = pd.to_numeric(
        get_source_series(["Overnight_Resting_Heart_Rate_bpm", "resting_heart_rate", "rhr", "resting_hr"]),
        errors="coerce",
    )
    df["Overnight_HRV_RMSSD_ms"] = pd.to_numeric(
        get_source_series(["Overnight_HRV_RMSSD_ms", "hrv_rmssd", "hrv", "overnight_hrv"]),
        errors="coerce",
    )

    df["Daily_Morning_Weight_kg"] = pd.to_numeric(
        get_source_series(["Daily_Morning_Weight_kg", "weight_kg", "weight"]),
        errors="coerce",
    )
    raw_body_fat = pd.to_numeric(
        get_source_series(["raw_body_fat", "fat_ratio", "body_fat_percentage", "body_fat", "fat_percentage"]),
        errors="coerce",
    )

    df["Resting_Systolic_Blood_Pressure_mmHg"] = pd.to_numeric(
        get_source_series(["Resting_Systolic_Blood_Pressure_mmHg", "systolic", "systolic_bp", "blood_pressure_systolic"]),
        errors="coerce",
    )
    df["Resting_Diastolic_Blood_Pressure_mmHg"] = pd.to_numeric(
        get_source_series(["Resting_Diastolic_Blood_Pressure_mmHg", "diastolic", "diastolic_bp", "blood_pressure_diastolic"]),
        errors="coerce",
    )
    df["Pulse_Wave_Velocity_m_s"] = pd.to_numeric(
        get_source_series(["Pulse_Wave_Velocity_m_s", "pulse_wave_velocity", "pwv", "pulse_wave_velocity_m_s"]),
        errors="coerce",
    )

    # 5. Tier 1 Derived Metrics (Calculated on Full History)
    df["Running_Distance_28d_Total_km"] = (
        df["Daily_Running_Distance_km"].rolling(window=28, min_periods=1).sum().round(2)
    )
    df["Resting_Heart_Rate_7d_Average_bpm"] = (
        df["Overnight_Resting_Heart_Rate_bpm"].rolling(window=7, min_periods=1).mean().round(1)
    )
    df["HRV_RMSSD_7d_Average_ms"] = (
        df["Overnight_HRV_RMSSD_ms"].rolling(window=7, min_periods=1).mean().round(1)
    )
    df["Body_Fat_Percentage_7d_Average"] = (
        raw_body_fat.rolling(window=7, min_periods=1).mean().round(1)
    )

    # 6. Tier 2 Non-Overlapping Baseline HRV Z-Score
    shifted_hrv = df["Overnight_HRV_RMSSD_ms"].shift(7)
    baseline_60d_mean = shifted_hrv.rolling(window=60, min_periods=30).mean()
    baseline_60d_std = shifted_hrv.rolling(window=60, min_periods=30).std().replace(0, np.nan)

    df["HRV_RMSSD_7d_Average_vs_Previous_60d_Baseline_ZScore"] = (
        (df["HRV_RMSSD_7d_Average_ms"] - baseline_60d_mean) / baseline_60d_std
    ).round(2)

    # 7. Exact Output Schema Ordering & 730-Day Slicing
    output_schema = [
        "Date_YYYY_MM_DD",
        "Daily_Running_Distance_km",
        "Daily_Running_Duration_min",
        "Daily_Walking_Distance_km",
        "Daily_Strength_Duration_min",
        "Daily_Steps_Count",
        "Running_Distance_28d_Total_km",
        "Garmin_7d_Training_Load_Sum",
        "Garmin_VO2_Max_ml_kg_min",
        "Lactate_Threshold_Pace_decimal_min_km",
        "Lactate_Threshold_Heart_Rate_bpm",
        "Overnight_Sleep_Duration_min",
        "Sleep_Start_Time_HH_MM",
        "Sleep_End_Time_HH_MM",
        "Overnight_Resting_Heart_Rate_bpm",
        "Resting_Heart_Rate_7d_Average_bpm",
        "Overnight_HRV_RMSSD_ms",
        "HRV_RMSSD_7d_Average_ms",
        "HRV_RMSSD_7d_Average_vs_Previous_60d_Baseline_ZScore",
        "Daily_Morning_Weight_kg",
        "Body_Fat_Percentage_7d_Average",
        "Resting_Systolic_Blood_Pressure_mmHg",
        "Resting_Diastolic_Blood_Pressure_mmHg",
        "Pulse_Wave_Velocity_m_s",
    ]

    integer_columns = [
        "Daily_Running_Duration_min",
        "Daily_Strength_Duration_min",
        "Daily_Steps_Count",
        "Garmin_7d_Training_Load_Sum",
        "Lactate_Threshold_Heart_Rate_bpm",
        "Overnight_Sleep_Duration_min",
        "Overnight_Resting_Heart_Rate_bpm",
        "Overnight_HRV_RMSSD_ms",
        "Resting_Systolic_Blood_Pressure_mmHg",
        "Resting_Diastolic_Blood_Pressure_mmHg",
    ]

    for col in integer_columns:
        df[col] = df[col].round().astype("Int64")

    export_df = df[output_schema].tail(DAYS_TO_EXPORT).copy()

    # 8. Row 1 Comment Header & Local CSV Export
    header_string = f"# Context: Male, Age: {AGE}, Height: {HEIGHT_CM} cm, Max HR: {MAX_HR} bpm\n"
    csv_body = export_df.to_csv(index=False, na_rep="")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(header_string)
        f.write(csv_body)

    print(f"Generated {OUTPUT_FILE} with {len(export_df)} daily rows.")

    # 9. Upload to Google Drive
    upload_quantified_self_to_drive(OUTPUT_FILE, drive_service)


if __name__ == "__main__":
    build_quantified_self_dataset()
