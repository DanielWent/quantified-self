from typing import Any, Dict

def parse_daily_summary(date_str: str, summary: Dict[str, Any], sleep: Dict[str, Any], hrv: Dict[str, Any]) -> Dict[str, Any]:
    sleep_dto = sleep.get("dailySleepDTO", {}) if sleep else {}
    hrv_summary = hrv.get("hrvSummary", {}) if hrv else {}
    
    return {
        "date": date_str,
        "total_steps": summary.get("totalSteps") if summary else None,
        "step_goal": summary.get("dailyStepGoal") if summary else None,
        "distance_meters": summary.get("totalDistanceMeters") if summary else None,
        "active_calories": summary.get("activeKilocalories") if summary else None,
        "resting_calories": summary.get("bmrKilocalories") if summary else None,
        "resting_hr": summary.get("restingHeartRate") if summary else None,
        "min_hr": summary.get("minHeartRate") if summary else None,
        "max_hr": summary.get("maxHeartRate") if summary else None,
        "avg_stress": summary.get("averageStressLevel") if summary else None,
        "vo2_max": summary.get("vo2MaxValue") if summary else None,
        "sleep_duration_seconds": sleep_dto.get("sleepTimeSeconds"),
        "sleep_score": sleep_dto.get("sleepScores", {}).get("overall", {}).get("value") if sleep_dto.get("sleepScores") else None,
        "deep_sleep_seconds": sleep_dto.get("deepSleepSeconds"),
        "light_sleep_seconds": sleep_dto.get("lightSleepSeconds"),
        "rem_sleep_seconds": sleep_dto.get("remSleepSeconds"),
        "hrv_weekly_avg": hrv_summary.get("weeklyAvg"),
        "hrv_last_night_avg": hrv_summary.get("lastNightAvg"),
        "hrv_status": hrv_summary.get("status")
    }

def parse_activity(activity: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "activity_id": activity.get("activityId"),
        "activity_name": activity.get("activityName"),
        "activity_type": activity.get("activityType", {}).get("typeKey"),
        "start_time_gmt": activity.get("startTimeGMT"),
        "duration_seconds": activity.get("duration"),
        "distance_meters": activity.get("distance"),
        "avg_speed_mps": activity.get("averageSpeed"),
        "max_speed_mps": activity.get("maxSpeed"),
        "avg_hr": activity.get("averageHR"),
        "max_hr": activity.get("maxHR"),
        "calories": activity.get("calories"),
        "elevation_gain_meters": activity.get("elevationGain"),
        "avg_cadence": activity.get("averageRunningCadenceInStepsPerMinute") or activity.get("averageBikingCadenceInRevPerMinute"),
        "aerobic_te": activity.get("aerobicTrainingEffect"),
        "anaerobic_te": activity.get("anaerobicTrainingEffect")
    }
