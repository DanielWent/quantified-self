from datetime import datetime
import logging

logger = logging.getLogger(__name__)

MALE_VO2_NORMS = {
    (20, 29): [(36.4, 10), (39.5, 20), (41.7, 30), (43.8, 40), (45.7, 50), (48.0, 60), (51.1, 70), (54.0, 80), (58.6, 90), (62.0, 95)],
    (30, 39): [(34.6, 10), (37.4, 20), (39.5, 30), (41.5, 40), (43.9, 50), (46.0, 60), (48.9, 70), (52.5, 80), (56.5, 90), (60.0, 95)],
    (40, 49): [(31.8, 10), (34.6, 20), (36.8, 30), (39.0, 40), (41.0, 50), (43.4, 60), (46.0, 70), (49.4, 80), (53.8, 90), (57.5, 95)],
    (50, 59): [(28.4, 10), (31.1, 20), (33.3, 30), (35.2, 40), (37.1, 50), (39.5, 60), (42.0, 70), (45.3, 80), (49.7, 90), (53.5, 95)],
    (60, 99): [(23.7, 10), (26.5, 20), (28.3, 30), (30.3, 40), (32.2, 50), (34.5, 60), (37.2, 70), (40.3, 80), (44.8, 90), (48.5, 95)],
}

FEMALE_VO2_NORMS = {
    (20, 29): [(28.3, 10), (31.6, 20), (33.8, 30), (36.1, 40), (38.1, 50), (41.0, 60), (43.9, 70), (47.0, 80), (51.4, 90), (55.0, 95)],
    (30, 39): [(26.5, 10), (29.1, 20), (31.0, 30), (32.9, 40), (34.9, 50), (36.9, 60), (39.8, 70), (43.3, 80), (46.9, 90), (50.5, 95)],
    (40, 49): [(24.1, 10), (26.5, 20), (28.3, 30), (30.2, 40), (31.9, 50), (33.8, 60), (36.3, 70), (39.7, 80), (43.8, 90), (47.0, 95)],
    (50, 59): [(21.5, 10), (23.7, 20), (25.5, 30), (27.1, 40), (28.9, 50), (30.9, 60), (33.0, 70), (36.0, 80), (39.9, 90), (43.0, 95)],
    (60, 99): [(18.3, 10), (20.1, 20), (21.9, 30), (23.5, 40), (25.0, 50), (26.9, 60), (29.2, 70), (31.6, 80), (35.6, 90), (39.0, 95)],
}

def calculate_age(birth_date_str: str, target_date_str: str):
    if not birth_date_str:
        return ""
    try:
        birth_date = datetime.strptime(birth_date_str[:10], "%Y-%m-%d").date()
        target_date = datetime.strptime(target_date_str[:10], "%Y-%m-%d").date()
        return target_date.year - birth_date.year - ((target_date.month, target_date.day) < (birth_date.month, birth_date.day))
    except Exception as e:
        logger.warning(f"Failed to calculate age from '{birth_date_str}': {e}")
        return ""

def calculate_vo2_percentile(vo2_max, age, gender):
    if not vo2_max or not age or not isinstance(age, int):
        return ""
    
    norms = MALE_VO2_NORMS if str(gender).upper().startswith("M") else FEMALE_VO2_NORMS
    table = next((brackets for (min_age, max_age), brackets in norms.items() if min_age <= age <= max_age), None)
    if not table:
        return ""

    percentile = 5
    for threshold, rank in table:
        if float(vo2_max) >= threshold:
            percentile = rank
        else:
            break
    return percentile

def parse_garmin_day(summary: dict, profile: dict, settings: dict, max_metrics, target_date: str) -> dict:
    user_name = profile.get("fullName") or profile.get("userName") or ""
    gender = profile.get("gender") or settings.get("userData", {}).get("gender") or ""
    birth_date = profile.get("birthDate") or settings.get("userData", {}).get("birthDate")
    user_age = calculate_age(birth_date, target_date)

    max_hr = (
        settings.get("userData", {}).get("maxHeartRate")
        or settings.get("userHeartRateZones", {}).get("maxHeartRate")
        or profile.get("maxHeartRate")
        or summary.get("maxHeartRate")
        or ""
    )

    metric_entry = max_metrics[0] if isinstance(max_metrics, list) and max_metrics else (max_metrics if isinstance(max_metrics, dict) else {})
    generic_vo2 = metric_entry.get("generic", {}).get("vo2MaxPrecision") or metric_entry.get("generic", {}).get("vo2MaxValue")
    running_vo2 = metric_entry.get("running", {}).get("vo2MaxPrecision") or metric_entry.get("running", {}).get("vo2MaxValue")
    
    raw_vo2 = running_vo2 or generic_vo2 or summary.get("vo2Max")
    vo2_max = round(float(raw_vo2), 2) if raw_vo2 else ""
    vo2_percentile = calculate_vo2_percentile(vo2_max, user_age, gender)

    return {
        "Date": target_date,
        "User Name": user_name,
        "User Age": user_age,
        "User Gender": gender,
        "Physiological Maximum Heart Rate (bpm)": max_hr,
        "VO2 Max (ml/kg/min)": vo2_max,
        "VO2 Max Percentile (Age-Gender Adjusted)": vo2_percentile,
        "Total Steps": summary.get("totalSteps", ""),
        "Total Distance (m)": summary.get("totalDistanceMeters", ""),
        "Resting Heart Rate (bpm)": summary.get("restingHeartRate", ""),
        "Average Stress Level": summary.get("averageStressLevel", ""),
        "Sleep Duration (s)": summary.get("sleepingSeconds", ""),
        "Average Overnight HRV": summary.get("averageOvernightHrv", ""),
    }
