import os
import re
from typing import Optional, Union
import numpy as np
import pandas as pd

# ==========================================
# Static Demographic Configuration
# ==========================================
AGE: int = 40
HEIGHT_CM: int = 185
MAX_HR: int = 185

OUTPUT_FILE: str = "quantified_self_data.csv"
DAYS_TO_EXPORT: int = 730


def parse_pace_to_decimal(pace_val: Union[str, float, int, None]) -> Optional[float]:
    """Converts MM:SS string or numeric pace representation to decimal minutes."""
    if pd.isna(pace_val) or pace_val == "" or pace_val is None:
        return np.nan
    pace_str = str(pace_val).strip()
    if ":" in pace_str:
        parts = pace_str.split(":")
        try:
            minutes = float(parts[0])
            seconds = float(parts[1])
            return round(minutes + (seconds / 60.0), 3)
        except (ValueError, IndexError):
            return np.nan
    try:
        val = float(pace_str)
        return round(val, 3) if val > 0 else np.nan
    except ValueError:
        return np.nan


def parse_time_to_hh_mm(time_val: Union[str, pd.Timestamp, None]) -> Optional[str]:
    """Formats sleep start/end timestamps into strict 24-hour HH:MM strings."""
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


def load_standardized_data(file_path: str) -> pd.DataFrame:
    """Loads a CSV and standardizes the date column to Date_YYYY_MM_DD."""
    if not os.path.exists(file_path):
        return pd.DataFrame(columns=["Date_YYYY_MM_DD"])

    df = pd.read_csv(file_path)
    if df.empty:
        return pd.DataFrame(columns=["Date_YYYY_MM_DD"])

    date_col = next(
        (c for c in df.columns if c.lower() in ["date", "date_yyyy_mm_dd", "day"]),
        df.columns[0],
    )
    df["Date_YYYY_MM_DD"] = pd.to_datetime(df[date_col]).dt.strftime("%Y-%m-%d")
    return df


def build_quantified_self_dataset(
    garmin_path: str = "garmin_data.csv",
    withings_path: str = "withings_data.csv",
    output_path: str = OUTPUT_FILE,
) -> None:
    garmin_df = load_standardized_data(garmin_path)
    withings_df = load_standardized_data(withings_path)

    if garmin_df.empty and withings_df.empty:
        raise ValueError(f"No source data found at {garmin_path} or {withings_path}")

    # Merge on Date across entire historical timeline
    merged = pd.merge(garmin_df, withings_df, on="Date_YYYY_MM_DD", how="outer")
    merged["Date_YYYY_MM_DD"] = pd.to_datetime(merged["Date_YYYY_MM_DD"])
    merged = merged.sort_values("Date_YYYY_MM_DD").reset_index(drop=True)

    # Reindex over full continuous daily date range (1 row = 1 calendar day)
    full_dates = pd.date_range(
        start=merged["Date_YYYY_MM_DD"].min(),
        end=merged["Date_YYYY_MM_DD"].max(),
        freq="D",
    )
    df = (
        merged.set_index("Date_YYYY_MM_DD")
        .reindex(full_dates)
        .rename_axis("Date_YYYY_MM_DD")
        .reset_index()
    )
    df["Date_YYYY_MM_DD"] = df["Date_YYYY_MM_DD"].dt.strftime("%Y-%m-%d")

    def get_column(candidates, default_val=np.nan):
        for candidate in candidates:
            for col in df.columns:
                if col.lower() == candidate.lower():
                    return df[col]
        return pd.Series(default_val, index=df.index)

    # ----------------------------------------------------
    # Raw Input Pass-Throughs & Normalization
    # ----------------------------------------------------
    df["Daily_Running_Distance_km"] = pd.to_numeric(
        get_column(
            [
                "Daily_Running_Distance_km",
                "running_distance_km",
                "running_distance",
                "run_distance",
            ]
        ),
        errors="coerce",
    )
    df["Daily_Running_Duration_min"] = pd.to_numeric(
        get_column(
            [
                "Daily_Running_Duration_min",
                "running_duration_min",
                "running_duration",
                "run_duration",
            ]
        ),
        errors="coerce",
    )
    df["Daily_Walking_Distance_km"] = pd.to_numeric(
        get_column(
            [
                "Daily_Walking_Distance_km",
                "walking_distance_km",
                "walking_distance",
                "walk_distance",
            ]
        ),
        errors="coerce",
    )
    df["Daily_Strength_Duration_min"] = pd.to_numeric(
        get_column(
            [
                "Daily_Strength_Duration_min",
                "strength_duration_min",
                "strength_duration",
            ]
        ),
        errors="coerce",
    )
    df["Daily_Steps_Count"] = pd.to_numeric(
        get_column(["Daily_Steps_Count", "steps", "step_count", "total_steps"]),
        errors="coerce",
    )
    df["Garmin_7d_Training_Load_Sum"] = pd.to_numeric(
        get_column(
            [
                "Garmin_7d_Training_Load_Sum",
                "training_load_7d",
                "training_load",
                "training_load_sum",
            ]
        ),
        errors="coerce",
    )
    df["Garmin_VO2_Max_ml_kg_min"] = pd.to_numeric(
        get_column(
            ["Garmin_VO2_Max_ml_kg_min", "vo2_max", "vo2max", "garmin_vo2_max"]
        ),
        errors="coerce",
    )

    raw_pace = get_column(
        [
            "Lactate_Threshold_Pace_decimal_min_km",
            "lactate_threshold_pace",
            "lt_pace",
            "threshold_pace",
        ]
    )
    df["Lactate_Threshold_Pace_decimal_min_km"] = (
        raw_pace.apply(parse_pace_to_decimal).astype(float).round(2)
    )

    df["Lactate_Threshold_Heart_Rate_bpm"] = pd.to_numeric(
        get_column(
            [
                "Lactate_Threshold_Heart_Rate_bpm",
                "lactate_threshold_hr",
                "lt_hr",
                "threshold_heart_rate",
            ]
        ),
        errors="coerce",
    )
    df["Overnight_Sleep_Duration_min"] = pd.to_numeric(
        get_column(
            [
                "Overnight_Sleep_Duration_min",
                "sleep_duration_min",
                "sleep_duration",
                "total_sleep_minutes",
            ]
        ),
        errors="coerce",
    )

    raw_start = get_column(
        ["Sleep_Start_Time_HH_MM", "sleep_start_time", "sleep_start"]
    )
    raw_end = get_column(["Sleep_End_Time_HH_MM", "sleep_end_time", "sleep_end"])
    df["Sleep_Start_Time_HH_MM"] = raw_start.apply(parse_time_to_hh_mm)
    df["Sleep_End_Time_HH_MM"] = raw_end.apply(parse_time_to_hh_mm)

    df["Overnight_Resting_Heart_Rate_bpm"] = pd.to_numeric(
        get_column(
            [
                "Overnight_Resting_Heart_Rate_bpm",
                "resting_heart_rate",
                "rhr",
                "resting_hr",
            ]
        ),
        errors="coerce",
    )
    df["Overnight_HRV_RMSSD_ms"] = pd.to_numeric(
        get_column(["Overnight_HRV_RMSSD_ms", "hrv_rmssd", "hrv", "overnight_hrv"]),
        errors="coerce",
    )

    df["Daily_Morning_Weight_kg"] = pd.to_numeric(
        get_column(["Daily_Morning_Weight_kg", "weight_kg", "weight"]),
        errors="coerce",
    )
    raw_body_fat = pd.to_numeric(
        get_column(
            [
                "raw_body_fat",
                "fat_ratio",
                "body_fat_percentage",
                "body_fat",
                "fat_percentage",
            ]
        ),
        errors="coerce",
    )

    df["Resting_Systolic_Blood_Pressure_mmHg"] = pd.to_numeric(
        get_column(
            [
                "Resting_Systolic_Blood_Pressure_mmHg",
                "systolic",
                "systolic_bp",
                "blood_pressure_systolic",
            ]
        ),
        errors="coerce",
    )
    df["Resting_Diastolic_Blood_Pressure_mmHg"] = pd.to_numeric(
        get_column(
            [
                "Resting_Diastolic_Blood_Pressure_mmHg",
                "diastolic",
                "diastolic_bp",
                "blood_pressure_diastolic",
            ]
        ),
        errors="coerce",
    )
    df["Pulse_Wave_Velocity_m_s"] = pd.to_numeric(
        get_column(
            [
                "Pulse_Wave_Velocity_m_s",
                "pulse_wave_velocity",
                "pwv",
                "pulse_wave_velocity_m_s",
            ]
        ),
        errors="coerce",
    )

    # ----------------------------------------------------
    # Tier 1 Derived Metrics (Full Historical Calculation)
    # ----------------------------------------------------
    df["Running_Distance_28d_Total_km"] = (
        df["Daily_Running_Distance_km"]
        .rolling(window=28, min_periods=1)
        .sum()
        .round(2)
    )

    df["Resting_Heart_Rate_7d_Average_bpm"] = (
        df["Overnight_Resting_Heart_Rate_bpm"]
        .rolling(window=7, min_periods=1)
        .mean()
        .round(1)
    )

    df["HRV_RMSSD_7d_Average_ms"] = (
        df["Overnight_HRV_RMSSD_ms"]
        .rolling(window=7, min_periods=1)
        .mean()
        .round(1)
    )

    df["Body_Fat_Percentage_7d_Average"] = (
        raw_body_fat.rolling(window=7, min_periods=1).mean().round(1)
    )

    # ----------------------------------------------------
    # Tier 2 Non-Overlapping Baseline HRV Z-Score
    # ----------------------------------------------------
    shifted_hrv = df["Overnight_HRV_RMSSD_ms"].shift(7)
    baseline_60d_mean = shifted_hrv.rolling(window=60, min_periods=30).mean()
    baseline_60d_std = shifted_hrv.rolling(window=60, min_periods=30).std().replace(0, np.nan)

    df["HRV_RMSSD_7d_Average_vs_Previous_60d_Baseline_ZScore"] = (
        (df["HRV_RMSSD_7d_Average_ms"] - baseline_60d_mean) / baseline_60d_std
    ).round(2)

    # ----------------------------------------------------
    # Schema Ordering & Tail 730 Slicing
    # ----------------------------------------------------
    schema_order = [
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

    export_df = df[schema_order].tail(DAYS_TO_EXPORT).copy()

    # ----------------------------------------------------
    # Row 1 Demographic Header Injection & Export
    # ----------------------------------------------------
    header_line = f"# Context: Male, Age: {AGE}, Height: {HEIGHT_CM} cm, Max HR: {MAX_HR} bpm\n"
    csv_body = export_df.to_csv(index=False, na_rep="")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header_line)
        f.write(csv_body)


if __name__ == "__main__":
    build_quantified_self_dataset()
