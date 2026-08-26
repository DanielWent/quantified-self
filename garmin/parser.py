import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def _safe_round(value: Optional[float], decimals: int = 2) -> Optional[float]:
    if value is None:
        return None
    try:
        return round(float(value), decimals)
    except (ValueError, TypeError):
        return None


def _format_pace(speed_mps: Optional[float]) -> Optional[str]:
    if not speed_mps or speed_mps <= 0:
        return None
    try:
        pace_sec_per_km = 1000.0 / float(speed_mps)
        minutes = int(pace_sec_per_km // 60)
        seconds = int(pace_sec_per_km % 60)
        return f"{minutes:02d}:{seconds:02d}"
    except (ValueError, TypeError, ZeroDivisionError):
        return None


def parse_daily_data(
    target_date: str,
    summary: Dict[str, Any],
    sleep: Dict[str, Any],
    hrv: Dict[str, Any],
    respiration: Dict[str, Any],
    spo2: Dict[str, Any],
    training_status: Dict[str, Any],
    max_metrics: Dict[str, Any],
) -> Dict[str, Any]:
    daily_sleep = sleep.get("dailySleepDTO", {}) if sleep else {}
    sleep_scores = daily_sleep.get("sleepScores", {}) if daily_sleep else {}
    overall_sleep_score = sleep_scores.get("overall", {}) if sleep_scores else {}
    hrv_summary = hrv.get("hrvSummary", {}) if hrv else {}

    # Distance conversion: meters to km
    distance_meters = summary.get("totalDistanceMeters")
    distance_km = (
        _safe_round(distance_meters / 1000.0, 2) if distance_meters is not None else None
    )

    # Stress durations: seconds to minutes
    rest_stress_s = summary.get("restStressDuration")
    low_stress_s = summary.get("lowStressDuration")
    med_stress_s = summary.get("mediumStressDuration")
    high_stress_s = summary.get("highStressDuration")

    # Sleep durations: seconds to hours
    sleep_time_s = daily_sleep.get("sleepTimeSeconds")
    deep_sleep_s = daily_sleep.get("deepSleepSeconds")
    light_sleep_s = daily_sleep.get("lightSleepSeconds")
    rem_sleep_s = daily_sleep.get("remSleepSeconds")
    awake_sleep_s = daily_sleep.get("awakeSleepSeconds")

    # Respiration extraction
    lowest_resp = summary.get("lowestRespirationValue") or respiration.get(
        "lowestRespirationValue"
    )
    highest_resp = summary.get("highestRespirationValue") or respiration.get(
        "highestRespirationValue"
    )
    avg_waking_resp = summary.get("avgWakingRespirationValue") or respiration.get(
        "avgWakingRespirationValue"
    )
    avg_sleep_resp = (
        daily_sleep.get("averageRespirationValue")
        or sleep.get("averageRespirationValue")
        or respiration.get("avgSleepRespirationValue")
    )

    # SpO2 extraction
    avg_spo2 = (
        summary.get("averageSpo2")
        or daily_sleep.get("averageSpO2Value")
        or spo2.get("averageSpO2")
    )
    lowest_spo2 = (
        summary.get("lowestSpo2")
        or daily_sleep.get("lowestSpO2Value")
        or spo2.get("lowestSpO2")
    )

    # VO2 Max extraction
    vo2_max = None
    if training_status:
        most_recent_vo2 = training_status.get("mostRecentVO2Max", {})
        if isinstance(most_recent_vo2, dict):
            vo2_max = most_recent_vo2.get("generic", {}).get(
                "vo2MaxValue"
            ) or most_recent_vo2.get("running", {}).get("vo2MaxValue")

    if vo2_max is None and max_metrics:
        if isinstance(max_metrics, list) and len(max_metrics) > 0:
            vo2_max = max_metrics[0].get("generic", {}).get("vo2MaxPreciseValue")
        elif isinstance(max_metrics, dict):
            vo2_max = max_metrics.get("generic", {}).get("vo2MaxPreciseValue")

    if vo2_max is None:
        vo2_max = summary.get("vo2MaxValue")

    # Active and Total Kilocalories
    active_kcal = summary.get("activeKilocalories")
    bmr_kcal = summary.get("bmrKilocalories")
    total_kcal = summary.get("totalKilocalories")
    if total_kcal is None and active_kcal is not None and bmr_kcal is not None:
        total_kcal = active_kcal + bmr_kcal

    return {
        "Date": target_date,
        "Total Steps": summary.get("totalSteps"),
        "Daily Step Goal": summary.get("dailyStepGoal"),
        "Total Distance (km)": distance_km,
        "Resting Heart Rate (bpm)": summary.get("restingHeartRate"),
        "Min Heart Rate (bpm)": summary.get("minHeartRate"),
        "Max Heart Rate (bpm)": summary.get("maxHeartRate"),
        "Average Stress Level": summary.get("averageStressLevel"),
        "Max Stress Level": summary.get("maxStressLevel"),
        "Rest Stress Duration (min)": _safe_round(rest_stress_s / 60.0, 1)
        if rest_stress_s is not None
        else None,
        "Low Stress Duration (min)": _safe_round(low_stress_s / 60.0, 1)
        if low_stress_s is not None
        else None,
        "Medium Stress Duration (min)": _safe_round(med_stress_s / 60.0, 1)
        if med_stress_s is not None
        else None,
        "High Stress Duration (min)": _safe_round(high_stress_s / 60.0, 1)
        if high_stress_s is not None
        else None,
        "Sleep Duration (hrs)": _safe_round(sleep_time_s / 3600.0, 2)
        if sleep_time_s is not None
        else None,
        "Deep Sleep (hrs)": _safe_round(deep_sleep_s / 3600.0, 2)
        if deep_sleep_s is not None
        else None,
        "Light Sleep (hrs)": _safe_round(light_sleep_s / 3600.0, 2)
        if light_sleep_s is not None
        else None,
        "REM Sleep (hrs)": _safe_round(rem_sleep_s / 3600.0, 2)
        if rem_sleep_s is not None
        else None,
        "Awake (hrs)": _safe_round(awake_sleep_s / 3600.0, 2)
        if awake_sleep_s is not None
        else None,
        "Sleep Score": overall_sleep_score.get("value"),
        "Sleep Quality": overall_sleep_score.get("qualifierKey"),
        "Overnight Avg HRV (ms)": hrv_summary.get("lastNightAvg"),
        "Overnight 5-Min High HRV (ms)": hrv_summary.get("lastNight5MinHigh"),
        "HRV Status": hrv_summary.get("status"),
        "Body Battery Lowest": summary.get("bodyBatteryLowestValue"),
        "Body Battery Highest": summary.get("bodyBatteryHighestValue"),
        "Body Battery Charged": summary.get("bodyBatteryChargedValue"),
        "Body Battery Drained": summary.get("bodyBatteryDrainedValue"),
        "Active Kilocalories (kcal)": active_kcal,
        "Total Kilocalories (kcal)": total_kcal,
        "Floors Ascended": summary.get("floorsAscended"),
        "Floors Descended": summary.get("floorsDescended"),
        "Running VO2 Max": _safe_round(vo2_max, 1),
        "Lowest Respiration (brpm)": lowest_resp,
        "Highest Respiration (brpm)": highest_resp,
        "Avg Waking Respiration (brpm)": avg_waking_resp,
        "Avg Overnight Respiration (brpm)": avg_sleep_resp,
        "Avg SpO2 (%)": avg_spo2,
        "Lowest SpO2 (%)": lowest_spo2,
    }


def parse_activity(activity: Dict[str, Any]) -> Dict[str, Any]:
    activity_type = activity.get("activityType", {})
    if isinstance(activity_type, dict):
        type_key = activity_type.get("typeKey", "")
    else:
        type_key = str(activity_type)

    distance_m = activity.get("distance")
    distance_km = _safe_round(distance_m / 1000.0, 2) if distance_m is not None else None

    duration_s = activity.get("duration")
    duration_min = _safe_round(duration_s / 60.0, 2) if duration_s is not None else None

    elapsed_duration_s = activity.get("elapsedDuration")
    elapsed_duration_min = (
        _safe_round(elapsed_duration_s / 60.0, 2)
        if elapsed_duration_s is not None
        else None
    )

    moving_duration_s = activity.get("movingDuration")
    moving_duration_min = (
        _safe_round(moving_duration_s / 60.0, 2)
        if moving_duration_s is not None
        else None
    )

    avg_speed_mps = activity.get("averageSpeed")
    avg_speed_kmh = (
        _safe_round(avg_speed_mps * 3.6, 2) if avg_speed_mps is not None else None
    )

    max_speed_mps = activity.get("maxSpeed")
    max_speed_kmh = (
        _safe_round(max_speed_mps * 3.6, 2) if max_speed_mps is not None else None
    )

    avg_cadence = activity.get("averageRunningCadenceInStepsPerMinute") or activity.get(
        "averageCadence"
    )
    max_cadence = activity.get("maxRunningCadenceInStepsPerMinute") or activity.get(
        "maxCadence"
    )

    stride_length = activity.get("avgStrideLength")
    if stride_length is not None and stride_length > 10:
        stride_length = stride_length / 100.0
    stride_length_m = _safe_round(stride_length, 2)

    return {
        "Activity ID": activity.get("activityId"),
        "Activity Name": activity.get("activityName"),
        "Activity Type": type_key,
        "Start Time": activity.get("startTimeLocal") or activity.get("startTimeGMT"),
        "Distance (km)": distance_km,
        "Duration (min)": duration_min,
        "Elapsed Duration (min)": elapsed_duration_min,
        "Moving Duration (min)": moving_duration_min,
        "Average Speed (km/h)": avg_speed_kmh,
        "Max Speed (km/h)": max_speed_kmh,
        "Average Pace (min/km)": _format_pace(avg_speed_mps),
        "Average Heart Rate (bpm)": _safe_round(activity.get("averageHR"), 0),
        "Max Heart Rate (bpm)": _safe_round(activity.get("maxHR"), 0),
        "Average Cadence (spm)": _safe_round(avg_cadence, 0),
        "Max Cadence (spm)": _safe_round(max_cadence, 0),
        "Calories (kcal)": activity.get("calories"),
        "Total Elevation Gain (m)": _safe_round(activity.get("elevationGain"), 1),
        "Total Elevation Loss (m)": _safe_round(activity.get("elevationLoss"), 1),
        "Min Elevation (m)": _safe_round(activity.get("minElevation"), 1),
        "Max Elevation (m)": _safe_round(activity.get("maxElevation"), 1),
        "Average Stride Length (m)": stride_length_m,
        "Aerobic Training Effect": _safe_round(activity.get("aerobicTrainingEffect"), 1),
        "Anaerobic Training Effect": _safe_round(activity.get("anaerobicTrainingEffect"), 1),
        "VO2 Max": _safe_round(activity.get("vO2MaxValue"), 1),
        "Steps": activity.get("steps"),
    }
