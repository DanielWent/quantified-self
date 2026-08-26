import logging

logger = logging.getLogger(__name__)

def parse_garmin_data(date_str, stats, sleep, rhr, hrv, activities=None):
    parsed = {
        "date": date_str,
        "steps": 0,
        "distance_meters": 0.0,
        "vo2_max": None,
        "resting_heart_rate": None,
        "hrv_avg": None,
        "sleep_duration_seconds": 0,
        "sleep_score": None,
        "activities": []
    }

    if stats and isinstance(stats, dict):
        parsed["steps"] = stats.get("totalSteps") or stats.get("steps") or 0
        parsed["distance_meters"] = float(stats.get("totalDistanceMeters") or 0.0)
        parsed["vo2_max"] = stats.get("vo2MaxValue") or stats.get("generic", {}).get("vo2MaxValue")

    if sleep and isinstance(sleep, dict):
        daily_sleep_dto = sleep.get("dailySleepDTO") or {}
        parsed["sleep_duration_seconds"] = daily_sleep_dto.get("sleepTimeSeconds") or 0
        parsed["sleep_score"] = daily_sleep_dto.get("sleepScores", {}).get("overall", {}).get("value")

    if rhr and isinstance(rhr, dict):
        parsed["resting_heart_rate"] = (
            rhr.get("restingHeartRate") or
            rhr.get("allMetrics", {}).get("metricsMap", {}).get("WELLNESS_RESTING_HEART_RATE", [{}])[0].get("value")
        )

    if hrv and isinstance(hrv, dict):
        hrv_summary = hrv.get("hrvSummary") or {}
        parsed["hrv_avg"] = hrv_summary.get("weeklyAvg") or hrv_summary.get("lastNightAvg")

    if activities and isinstance(activities, list):
        for act in activities:
            if isinstance(act, dict):
                start_time = act.get("startTimeLocal") or act.get("startTimeGMT") or ""
                if start_time.startswith(date_str):
                    parsed["activities"].append({
                        "activity_id": act.get("activityId"),
                        "name": act.get("activityName"),
                        "type": act.get("activityType", {}).get("typeKey"),
                        "distance_meters": act.get("distance"),
                        "duration_seconds": act.get("duration"),
                        "average_hr": act.get("averageHR"),
                        "max_hr": act.get("maxHR"),
                        "avg_pace_meter_per_sec": act.get("averageSpeed")
                    })

    return parsed
