from typing import Any, Dict, List, Optional

def extract_vo2_max(summary: Optional[Dict[str, Any]], max_metrics: Any, training_status: Any) -> Optional[float]:
    # 1. Search max_metrics endpoint
    if max_metrics:
        if isinstance(max_metrics, list) and len(max_metrics) > 0:
            item = max_metrics[0]
            for key in ['generic', 'running', 'cycling']:
                if isinstance(item, dict) and key in item and item[key]:
                    val = item[key].get('vo2MaxPreciseValue') or item[key].get('vo2MaxValue')
                    if val is not None:
                        return float(val)
        elif isinstance(max_metrics, dict):
            for key in ['generic', 'running', 'cycling']:
                if key in max_metrics and max_metrics[key]:
                    val = max_metrics[key].get('vo2MaxPreciseValue') or max_metrics[key].get('vo2MaxValue')
                    if val is not None:
                        return float(val)

    # 2. Search training_status endpoint
    if training_status and isinstance(training_status, dict):
        most_recent = training_status.get('mostRecentVO2Max', {})
        for key in ['generic', 'running', 'cycling']:
            if key in most_recent and most_recent[key]:
                val = most_recent[key].get('vo2MaxPreciseValue') or most_recent[key].get('vo2MaxValue')
                if val is not None:
                    return float(val)

    # 3. Fallback to daily summary
    if summary:
        val = summary.get('vo2MaxValue') or summary.get('vo2Max')
        if val is not None:
            return float(val)

    return None

def parse_daily_summary(
    date_str: str,
    summary: Optional[Dict[str, Any]],
    sleep: Optional[Dict[str, Any]],
    hrv: Optional[Dict[str, Any]],
    body_battery: Optional[List[Dict[str, Any]]] = None,
    readiness: Optional[Dict[str, Any]] = None,
    respiration: Optional[Dict[str, Any]] = None,
    spo2: Optional[Dict[str, Any]] = None,
    max_metrics: Any = None,
    training_status: Any = None
) -> Dict[str, Any]:
    summary = summary or {}
    sleep_dto = sleep.get("dailySleepDTO", {}) if sleep else {}
    hrv_summary = hrv.get("hrvSummary", {}) if hrv else {}

    bb_charged = summary.get("bodyBatteryChargedValue")
    bb_drained = summary.get("bodyBatteryDrainedValue")
    bb_highest = summary.get("bodyBatteryHighestValue")
    bb_lowest = summary.get("bodyBatteryLowestValue")
    bb_most_recent = summary.get("bodyBatteryMostRecentValue")

    if body_battery and isinstance(body_battery, list) and len(body_battery) > 0:
        values = [b.get("charged", 0) for b in body_battery if isinstance(b, dict) and "charged" in b]
        if values and bb_charged is None:
            bb_charged = sum(values)

    active_cal = summary.get("activeKilocalories")
    bmr_cal = summary.get("bmrKilocalories")
    total_cal = summary.get("totalKilocalories")
    if total_cal is None and active_cal is not None and bmr_cal is not None:
        total_cal = active_cal + bmr_cal

    readiness_score = None
    readiness_level = None
    if readiness and isinstance(readiness, dict):
        readiness_score = readiness.get("score") or readiness.get("trainingReadinessScore")
        readiness_level = readiness.get("level") or readiness.get("trainingReadinessLevel")

    return {
        "date": date_str,
        "total_steps": summary.get("totalSteps"),
        "step_goal": summary.get("dailyStepGoal"),
        "total_distance_meters": summary.get("totalDistanceMeters"),
        "active_calories": active_cal,
        "resting_calories": bmr_cal,
        "total_calories": total_cal,
        "resting_hr": summary.get("restingHeartRate"),
        "min_hr": summary.get("minHeartRate"),
        "max_hr": summary.get("maxHeartRate"),
        "avg_stress": summary.get("averageStressLevel"),
        "max_stress": summary.get("maxStressLevel"),
        "stress_duration_seconds": summary.get("stressDuration"),
        "rest_stress_duration_seconds": summary.get("restStressDuration"),
        "activity_stress_duration_seconds": summary.get("activityStressDuration"),
        "low_stress_duration_seconds": summary.get("lowStressDuration"),
        "medium_stress_duration_seconds": summary.get("mediumStressDuration"),
        "high_stress_duration_seconds": summary.get("highStressDuration"),
        "body_battery_charged": bb_charged,
        "body_battery_drained": bb_drained,
        "body_battery_highest": bb_highest,
        "body_battery_lowest": bb_lowest,
        "body_battery_most_recent": bb_most_recent,
        "vo2_max": extract_vo2_max(summary, max_metrics, training_status),
        "training_readiness_score": readiness_score,
        "training_readiness_level": readiness_level,
        "sleep_duration_seconds": sleep_dto.get("sleepTimeSeconds"),
        "sleep_score": sleep_dto.get("sleepScores", {}).get("overall", {}).get("value") if sleep_dto.get("sleepScores") else None,
        "sleep_score_qualifier": sleep_dto.get("sleepScores", {}).get("overall", {}).get("qualifierKey") if sleep_dto.get("sleepScores") else None,
        "deep_sleep_seconds": sleep_dto.get("deepSleepSeconds"),
        "light_sleep_seconds": sleep_dto.get("lightSleepSeconds"),
        "rem_sleep_seconds": sleep_dto.get("remSleepSeconds"),
        "awake_sleep_seconds": sleep_dto.get("awakeSleepSeconds"),
        "avg_sleep_stress": sleep_dto.get("avgSleepStress"),
        "hrv_weekly_avg": hrv_summary.get("weeklyAvg"),
        "hrv_last_night_avg": hrv_summary.get("lastNightAvg"),
        "hrv_last_night_5min_high": hrv_summary.get("lastNight5MinHigh"),
        "hrv_status": hrv_summary.get("status"),
        "avg_waking_respiration": respiration.get("avgWakingRespirationValue") if respiration else None,
        "lowest_respiration": respiration.get("lowestRespirationValue") if respiration else None,
        "highest_respiration": respiration.get("highestRespirationValue") if respiration else None,
        "avg_sleep_respiration": respiration.get("avgSleepRespirationValue") if respiration else None,
        "avg_spo2": spo2.get("averageSpO2") if spo2 else None,
        "lowest_spo2": spo2.get("lowestSpO2") if spo2 else None,
    }

def parse_activity(activity: Dict[str, Any]) -> Dict[str, Any]:
    cadence = (
        activity.get("averageRunningCadenceInStepsPerMinute") or
        activity.get("averageBikingCadenceInRevPerMinute") or
        activity.get("averageSwimCadenceInStrokesPerMinute")
    )
    max_cadence = (
        activity.get("maxRunningCadenceInStepsPerMinute") or
        activity.get("maxBikingCadenceInRevPerMinute") or
        activity.get("maxSwimCadenceInStrokesPerMinute")
    )

    return {
        "activity_id": activity.get("activityId"),
        "activity_name": activity.get("activityName"),
        "activity_type": activity.get("activityType", {}).get("typeKey"),
        "start_time_gmt": activity.get("startTimeGMT"),
        "start_time_local": activity.get("startTimeLocal"),
        "duration_seconds": activity.get("duration"),
        "elapsed_duration_seconds": activity.get("elapsedDuration"),
        "moving_duration_seconds": activity.get("movingDuration"),
        "distance_meters": activity.get("distance"),
        "avg_speed_mps": activity.get("averageSpeed"),
        "max_speed_mps": activity.get("maxSpeed"),
        "avg_hr": activity.get("averageHR"),
        "max_hr": activity.get("maxHR"),
        "calories": activity.get("calories"),
        "bmr_calories": activity.get("bmrCalories"),
        "elevation_gain_meters": activity.get("elevationGain"),
        "elevation_loss_meters": activity.get("elevationLoss"),
        "min_elevation_meters": activity.get("minElevation"),
        "max_elevation_meters": activity.get("maxElevation"),
        "avg_cadence": cadence,
        "max_cadence": max_cadence,
        "avg_power": activity.get("avgPower"),
        "max_power": activity.get("maxPower"),
        "norm_power": activity.get("normPower"),
        "aerobic_te": activity.get("aerobicTrainingEffect"),
        "anaerobic_te": activity.get("anaerobicTrainingEffect"),
        "training_effect_label": activity.get("trainingEffectLabel"),
        "activity_training_load": activity.get("activityTrainingLoad"),
        "steps": activity.get("steps")
    }
