from datetime import datetime
import logging
from statistics import mean
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Full 21-point percentile scale provided by the ACSM guidelines
PERCENTILES = [
    1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 99
]

NORMATIVE_DATA = {
    "M": {
        25: [26.5, 31.8, 34.7, 36.7, 38.0, 39.0, 39.9, 41.0, 41.7, 42.6, 43.9, 44.8, 45.6, 46.8, 47.5, 48.5, 51.1, 51.8, 54.0, 55.5, 60.5],
        35: [26.5, 31.2, 33.8, 35.2, 36.7, 37.8, 38.7, 39.5, 40.7, 41.2, 42.4, 43.9, 44.1, 45.3, 46.0, 47.0, 48.3, 50.0, 51.7, 54.1, 58.3],
        45: [25.1, 29.4, 32.3, 33.8, 34.8, 35.9, 36.7, 37.6, 38.4, 39.5, 40.1, 41.0, 42.4, 43.1, 43.9, 44.9, 46.4, 48.2, 49.6, 52.5, 56.1],
        55: [22.8, 26.9, 29.4, 30.9, 32.0, 32.8, 33.8, 34.8, 35.5, 36.7, 37.1, 38.1, 39.0, 39.7, 41.0, 41.8, 43.3, 44.6, 46.8, 49.0, 54.0],
        65: [19.7, 23.6, 25.6, 27.3, 28.7, 29.5, 30.8, 31.6, 32.3, 33.0, 33.8, 34.9, 35.6, 36.7, 37.4, 38.3, 39.6, 41.0, 42.7, 45.7, 51.1],
        75: [18.2, 20.8, 23.0, 24.6, 25.7, 26.9, 28.0, 28.4, 29.4, 30.1, 30.9, 31.6, 32.4, 33.1, 33.9, 35.2, 36.7, 38.1, 39.5, 43.9, 49.6],
    },
    "F": {
        25: [23.7, 27.6, 29.5, 30.9, 32.3, 33.0, 34.1, 35.2, 36.1, 36.7, 37.8, 38.5, 39.5, 41.0, 41.1, 42.4, 43.9, 45.3, 46.8, 49.6, 54.5],
        35: [22.9, 25.9, 28.0, 29.4, 30.9, 32.0, 32.4, 33.8, 34.2, 35.2, 36.7, 36.9, 37.7, 38.5, 39.6, 41.0, 42.4, 43.9, 45.3, 47.4, 52.0],
        45: [22.2, 25.1, 26.6, 28.2, 29.4, 30.2, 31.1, 32.3, 32.8, 33.8, 34.5, 35.2, 35.9, 36.7, 38.1, 38.6, 39.6, 41.0, 43.1, 45.3, 51.1],
        55: [20.1, 23.0, 24.6, 25.8, 26.8, 28.0, 28.7, 29.4, 29.9, 30.9, 31.4, 32.3, 32.6, 33.3, 34.2, 35.2, 36.7, 37.0, 38.8, 41.0, 46.1],
        65: [19.5, 21.8, 23.0, 23.9, 24.6, 25.1, 25.9, 26.6, 27.3, 28.2, 28.8, 29.4, 29.7, 30.9, 31.1, 32.3, 32.7, 34.2, 35.9, 37.8, 42.4],
        75: [16.8, 19.6, 21.5, 22.2, 23.5, 24.2, 24.7, 25.3, 25.9, 26.7, 27.6, 28.0, 28.1, 29.4, 29.4, 29.8, 30.6, 32.3, 32.5, 37.2, 42.4],
    },
}


def interp_python(x: float, xp: List[float], fp: List[float]) -> float:
    if x <= xp[0]:
        return fp[0]
    if x >= xp[-1]:
        return fp[-1]
    for i in range(len(xp) - 1):
        if xp[i] <= x <= xp[i + 1]:
            if xp[i] == xp[i + 1]:
                return fp[i]
            weight = (x - xp[i]) / (xp[i + 1] - xp[i])
            return fp[i] + weight * (fp[i + 1] - fp[i])
    return fp[-1]


def calculate_exact_percentile(
    age: Optional[float], gender: Optional[str], vo2_max: Optional[float]
) -> Optional[float]:
    if age is None or gender is None or vo2_max is None:
        return None

    gender_norm = gender.upper()
    if gender_norm in ["MALE", "M"]:
        gender_key = "M"
    elif gender_norm in ["FEMALE", "F"]:
        gender_key = "F"
    else:
        return None

    data = NORMATIVE_DATA.get(gender_key)
    if not data:
        return None

    anchors = sorted(data.keys())
    if age <= anchors[0]:
        interpolated_thresholds = data[anchors[0]]
    elif age >= anchors[-1]:
        interpolated_thresholds = data[anchors[-1]]
    else:
        lower_anchor = anchors[0]
        upper_anchor = anchors[-1]
        for i in range(len(anchors) - 1):
            if anchors[i] <= age < anchors[i + 1]:
                lower_anchor = anchors[i]
                upper_anchor = anchors[i + 1]
                break
        weight = (age - lower_anchor) / (upper_anchor - lower_anchor)
        lower_thresholds = data[lower_anchor]
        upper_thresholds = data[upper_anchor]
        interpolated_thresholds = [
            l * (1 - weight) + u * weight
            for l, u in zip(lower_thresholds, upper_thresholds)
        ]

    exact_percentile = interp_python(vo2_max, interpolated_thresholds, PERCENTILES)
    return round(exact_percentile, 1)


def calculate_pace(speed_ms: Optional[float]) -> str:
    if not speed_ms or speed_ms <= 0:
        return ""
    try:
        sec_per_km = 1000.0 / float(speed_ms)
        p_min = int(sec_per_km // 60)
        p_sec = int(sec_per_km % 60)
        return f"{p_min}:{p_sec:02d}"
    except (ValueError, TypeError, ZeroDivisionError):
        return ""


def find_training_load(data: Any) -> Optional[int]:
    if not data:
        return None
    stack = [data]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for k in [
                "dailyTrainingLoadAcute",
                "acuteLoad",
                "sevenDayLoad",
                "timeInZoneLoad",
            ]:
                if k in current and current[k] is not None:
                    return int(round(current[k]))
            for value in current.values():
                if isinstance(value, (dict, list)):
                    stack.append(value)
        elif isinstance(current, list):
            for item in current:
                if isinstance(item, (dict, list)):
                    stack.append(item)
    return None


def find_training_load_focus(data: Any) -> Optional[str]:
    if not data:
        return None
    stack = [data]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for k in ["trainingBalanceFeedbackPhrase", "statusText"]:
                if k in current and current[k] is not None:
                    return str(current[k])
            for v in current.values():
                if isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(current, list):
            for item in current:
                if isinstance(item, (dict, list)):
                    stack.append(item)
    return None


def find_training_readiness(data: Any) -> Optional[int]:
    if not data:
        return None
    if isinstance(data, list) and len(data) > 0:
        for item in reversed(data):
            if isinstance(item, dict) and "score" in item and item["score"] is not None:
                try:
                    return int(item["score"])
                except (ValueError, TypeError):
                    pass

    stack = [data]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for k in ["trainingReadinessScore", "readinessScore", "score"]:
                if k in current and current[k] is not None:
                    try:
                        return int(current[k])
                    except (ValueError, TypeError):
                        pass
            for v in current.values():
                if isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(current, list):
            for item in current:
                if isinstance(item, (dict, list)):
                    stack.append(item)
    return None


def parse_garmin_daily_data(
    date_str: str,
    user_profile: Dict[str, Any],
    summary: Optional[Dict[str, Any]] = None,
    stats: Optional[Any] = None,
    sleep_data: Optional[Dict[str, Any]] = None,
    hrv_payload: Optional[Dict[str, Any]] = None,
    bp_payload: Optional[Any] = None,
    training_status_std: Optional[Dict[str, Any]] = None,
    training_status_modern: Optional[Dict[str, Any]] = None,
    lactate_data: Optional[Dict[str, Any]] = None,
    lactate_range_hr: Optional[List[Dict[str, Any]]] = None,
    lactate_range_speed: Optional[List[Dict[str, Any]]] = None,
    readiness_data: Optional[Any] = None,
    activities: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    summary = summary or {}
    sleep_data = sleep_data or {}
    training_status_std = training_status_std or {}

    user_name = user_profile.get("user_name", "")
    user_age = user_profile.get("user_age")
    user_gender = user_profile.get("user_gender", "")

    max_hr_hunt = int(round(211 - 0.64 * user_age)) if user_age else ""

    # VO2 Max extraction
    vo2_run = ""
    train_phrase = ""
    lactate_bpm = ""
    lactate_pace = ""

    if training_status_std:
        mr_vo2 = training_status_std.get("mostRecentVO2Max") or {}
        if mr_vo2.get("generic"):
            vo2_val = mr_vo2["generic"].get("vo2MaxPreciseValue", mr_vo2["generic"].get("vo2MaxValue"))
            if vo2_val is not None:
                try:
                    vo2_run = round(float(vo2_val), 1)
                except ValueError:
                    pass

        mr_ts = training_status_std.get("mostRecentTrainingStatus") or {}
        ts_data = mr_ts.get("latestTrainingStatusData") or {}
        if isinstance(ts_data, dict):
            for dev_data in ts_data.values():
                if isinstance(dev_data, dict):
                    train_phrase = dev_data.get("trainingStatusFeedbackPhrase") or ""
                    if train_phrase:
                        break

        if "lactateThresholdHeartRate" in mr_ts and mr_ts["lactateThresholdHeartRate"]:
            lactate_bpm = mr_ts["lactateThresholdHeartRate"]

    if lactate_data:
        if "heartRate" in lactate_data and lactate_data["heartRate"]:
            lactate_bpm = lactate_data["heartRate"]
        if "speed" in lactate_data and lactate_data["speed"]:
            lactate_pace = calculate_pace(lactate_data["speed"])

    if not lactate_bpm and lactate_range_hr and isinstance(lactate_range_hr, list):
        try:
            last_entry = lactate_range_hr[-1]
            if isinstance(last_entry, dict) and "value" in last_entry and last_entry["value"]:
                lactate_bpm = int(last_entry["value"])
        except Exception:
            pass

    if not lactate_pace and lactate_range_speed and isinstance(lactate_range_speed, list):
        try:
            last_entry = lactate_range_speed[-1]
            if isinstance(last_entry, dict) and "value" in last_entry:
                spd = last_entry["value"]
                if spd and spd > 0:
                    if spd < 1.0:
                        spd *= 10
                    lactate_pace = calculate_pace(spd)
        except Exception:
            pass

    vo2_max_percentile = ""
    if vo2_run != "":
        pct = calculate_exact_percentile(user_age, user_gender, float(vo2_run))
        if pct is not None:
            vo2_max_percentile = pct

    # Sleep extraction
    sleep_dto = sleep_data.get("dailySleepDTO") if isinstance(sleep_data, dict) else None
    if not sleep_dto and isinstance(sleep_data, dict):
        sleep_dto = sleep_data

    sleep_score = ""
    sleep_length = ""
    sleep_need = ""
    sleep_start_time = ""
    sleep_end_time = ""
    sleep_deep = ""
    sleep_light = ""
    sleep_rem = ""
    sleep_awake = ""
    overnight_pulse_ox = ""

    if sleep_dto:
        sleep_scores = sleep_dto.get("sleepScores") or {}
        val = sleep_scores.get("overall", {}).get("value")
        if val is not None:
            sleep_score = val

        sleep_need_obj = sleep_dto.get("sleepNeed")
        if isinstance(sleep_need_obj, dict):
            sleep_need = sleep_need_obj.get("actual", "")
        elif sleep_need_obj is not None:
            sleep_need = sleep_need_obj

        po = sleep_dto.get("averageSpO2Value")
        if po is not None:
            overnight_pulse_ox = po

        sleep_time_seconds = sleep_dto.get("sleepTimeSeconds")
        if sleep_time_seconds:
            sleep_length = round(sleep_time_seconds / 60)

        start_ts_local = sleep_dto.get("sleepStartTimestampLocal")
        end_ts_local = sleep_dto.get("sleepEndTimestampLocal")
        if start_ts_local:
            sleep_start_time = datetime.fromtimestamp(start_ts_local / 1000).strftime("%H:%M")
        if end_ts_local:
            sleep_end_time = datetime.fromtimestamp(end_ts_local / 1000).strftime("%H:%M")

        if sleep_dto.get("deepSleepSeconds") is not None:
            sleep_deep = sleep_dto.get("deepSleepSeconds") / 60
        if sleep_dto.get("lightSleepSeconds") is not None:
            sleep_light = sleep_dto.get("lightSleepSeconds") / 60
        if sleep_dto.get("remSleepSeconds") is not None:
            sleep_rem = sleep_dto.get("remSleepSeconds") / 60
        if sleep_dto.get("awakeSleepSeconds") is not None:
            sleep_awake = sleep_dto.get("awakeSleepSeconds") / 60

    # Summary metrics
    avg_stress = summary.get("averageStressLevel", "")
    bb_min = summary.get("bodyBatteryLowestValue", "")
    bb_max = summary.get("bodyBatteryHighestValue", "")
    bb_charged = summary.get("bodyBatteryChargedValue", "")
    bb_drained = summary.get("bodyBatteryDrainedValue", "")
    steps = summary.get("totalSteps", "")

    raw_floors = summary.get("floorsAscended") or summary.get("floorsClimbed")
    floors = ""
    if raw_floors is not None:
        try:
            floors = round(float(raw_floors))
        except (ValueError, TypeError):
            floors = raw_floors

    mod_min = summary.get("moderateIntensityMinutes", 0) or 0
    vig_min = summary.get("vigorousIntensityMinutes", 0) or 0
    intensity_min = (
        mod_min + 2 * vig_min
        if (summary.get("moderateIntensityMinutes") is not None or summary.get("vigorousIntensityMinutes") is not None)
        else ""
    )

    active_cal = summary.get("activeKilocalories")
    resting_cal = summary.get("bmrKilocalories")
    total_cal = ""
    if active_cal is not None or resting_cal is not None:
        total_cal = (active_cal or 0) + (resting_cal or 0)

    # Blood pressure
    bp_systolic = ""
    bp_diastolic = ""
    if bp_payload:
        readings = []
        try:
            if isinstance(bp_payload, dict) and "measurementSummaries" in bp_payload:
                summaries = bp_payload.get("measurementSummaries", [])
                if isinstance(summaries, list):
                    for s_item in summaries:
                        if isinstance(s_item, dict) and "measurements" in s_item:
                            batch = s_item["measurements"]
                            if isinstance(batch, list):
                                readings.extend(batch)
            elif isinstance(bp_payload, list):
                readings = bp_payload
            elif isinstance(bp_payload, dict) and "userDailyBloodPressureDTOList" in bp_payload:
                readings = bp_payload["userDailyBloodPressureDTOList"]

            if readings:
                sys_vals = [r["systolic"] for r in readings if isinstance(r, dict) and r.get("systolic")]
                dia_vals = [r["diastolic"] for r in readings if isinstance(r, dict) and r.get("diastolic")]
                if sys_vals:
                    bp_systolic = int(round(mean(sys_vals)))
                if dia_vals:
                    bp_diastolic = int(round(mean(dia_vals)))
        except Exception:
            pass

    seven_day_load = (
        find_training_load(training_status_modern)
        if training_status_modern
        else None
    )
    if seven_day_load is None and training_status_std:
        seven_day_load = find_training_load(training_status_std)
    if seven_day_load is None and summary:
        seven_day_load = find_training_load(summary)

    train_load_focus = find_training_load_focus(training_status_modern) or find_training_load_focus(training_status_std) or ""
    training_readiness = find_training_readiness(readiness_data)
    resting_hr = summary.get("restingHeartRate", "")

    overnight_hrv = ""
    hrv_status = ""
    if hrv_payload and hrv_payload.get("hrvSummary"):
        hrv_summary = hrv_payload["hrvSummary"]
        overnight_hrv = hrv_summary.get("lastNightAvg", "")
        hrv_status = hrv_summary.get("status", "")

    # Activity aggregations
    total_walking_dist = 0.0
    total_walking_dur = 0.0
    total_running_cnt = 0
    total_running_dist = 0.0
    total_running_dur = 0.0
    total_strength_dur = 0.0

    if activities:
        for act in activities:
            if not isinstance(act, dict):
                continue
            atype = act.get("activityType") or {}
            type_key = atype.get("typeKey", "")
            d_km = (act.get("distance") or 0) / 1000.0
            d_min = (act.get("duration") or 0) / 60.0

            if "walk" in type_key:
                total_walking_dist += d_km
                total_walking_dur += d_min
            elif "run" in type_key:
                total_running_cnt += 1
                total_running_dist += d_km
                total_running_dur += d_min
            elif "strength" in type_key:
                total_strength_dur += d_min

    return {
        "Date (YYYY-MM-DD)": date_str,
        "User Name": user_name,
        "User Age": user_age if user_age is not None else "",
        "User Gender": user_gender,
        "Physiological Maximum Heart Rate (bpm)": max_hr_hunt,
        "VO2 Max (ml/kg/min)": vo2_run,
        "VO2 Max Percentile (Age-Gender Adjusted)": vo2_max_percentile,
        "Lactate Threshold Pace (min/km)": lactate_pace,
        "Lactate Threshold Heart Rate (bpm)": lactate_bpm,
        "Garmin Sleep Score (0-100)": sleep_score,
        "Sleep Start Time": sleep_start_time,
        "Sleep End Time": sleep_end_time,
        "Deep Sleep (min)": sleep_deep,
        "Light Sleep (min)": sleep_light,
        "REM Sleep (min)": sleep_rem,
        "Awake Time (min)": sleep_awake,
        "Sleep Length (min)": sleep_length,
        "Sleep Need (min)": sleep_need,
        "Overnight Average Pulse Ox / SpO2 (%)": overnight_pulse_ox,
        "Garmin Average Stress Score (0-100)": avg_stress,
        "Daily Min Body Battery (0-100)": bb_min,
        "Daily Max Body Battery (0-100)": bb_max,
        "Body Battery Charged (0-100)": bb_charged,
        "Body Battery Drained (0-100)": bb_drained,
        "Daily Steps": steps,
        "Daily Floors Climbed": floors,
        "Daily Intensity Minutes": intensity_min,
        "Total Calories (kcal)": total_cal,
        "Systolic Blood Pressure (mmHg)": bp_systolic,
        "Diastolic Blood Pressure (mmHg)": bp_diastolic,
        "Garmin Training Load (7 Day Sum)": seven_day_load if seven_day_load is not None else "",
        "Garmin Training Load Focus": train_load_focus,
        "Morning Garmin Training Readiness (0-100)": training_readiness if training_readiness is not None else "",
        "Overnight Resting HR (bpm)": resting_hr,
        "Overnight HRV (ms)": overnight_hrv,
        "Garmin HRV Status (Text Label)": hrv_status,
        "Garmin Training Status (Text Label)": train_phrase,
        "Total Walking Distance (km)": round(total_walking_dist, 2),
        "Total Walking Duration (min)": round(total_walking_dur, 1),
        "Total Running Activities Count": total_running_cnt,
        "Total Running Distance (km)": round(total_running_dist, 2),
        "Total Running Duration (min)": round(total_running_dur, 1),
        "Total Strength Training Duration (min)": round(total_strength_dur, 1),
    }


def parse_garmin_activity_data(
    activity: Dict[str, Any],
    full_activity: Optional[Dict[str, Any]] = None,
    weather_data: Optional[Dict[str, Any]] = None,
    hr_zones: Optional[List[Dict[str, Any]]] = None,
    power_zones: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    full_act = full_activity or activity
    atype = activity.get("activityType") or {}
    type_key = atype.get("typeKey", "Unknown")

    act_id = activity.get("activityId")
    act_name = activity.get("activityName")
    act_start_local = activity.get("startTimeLocal") or ""

    date_str = act_start_local.split(" ")[0] if " " in act_start_local else act_start_local[:10]
    act_time_str = act_start_local.split(" ")[1][:5] if " " in act_start_local else ""

    dist_km = (activity.get("distance") or 0) / 1000.0
    dur_min = (activity.get("duration") or 0) / 60.0

    pace_str = ""
    if dist_km > 0 and dur_min > 0:
        pace_decimal = dur_min / dist_km
        p_min = int(pace_decimal)
        p_sec = int((pace_decimal - p_min) * 60)
        pace_str = f"{p_min}:{p_sec:02d}"

    gap_speed = activity.get("avgGradeAdjustedSpeed")
    gap_str = calculate_pace(gap_speed)

    avg_cadence = (
        full_act.get("averageRunningCadenceInStepsPerMinute")
        or full_act.get("averageBikingCadenceInRevPerMinute")
        or activity.get("averageRunningCadenceInStepsPerMinute")
    )
    stride_len = (
        full_act.get("avgStrideLength")
        or full_act.get("averageStrideLength")
        or full_act.get("strideLength")
        or activity.get("avgStrideLength")
        or activity.get("strideLength")
    )
    if stride_len and stride_len > 10:
        stride_len = stride_len / 100.0

    gct = (
        full_act.get("avgGroundContactTime")
        or full_act.get("averageGroundContactTime")
        or full_act.get("groundContactTime")
        or activity.get("avgGroundContactTime")
    )
    vert_osc = (
        full_act.get("avgVerticalOscillation")
        or full_act.get("averageVerticalOscillation")
        or full_act.get("verticalOscillation")
        or activity.get("avgVerticalOscillation")
    )

    training_load = full_act.get("activityTrainingLoad") or activity.get("activityTrainingLoad")
    max_power = full_act.get("maxPower") or activity.get("maxPower")
    norm_power = full_act.get("normPower") or activity.get("normPower")
    sweat_loss = full_act.get("waterEstimated") or activity.get("waterEstimated")

    aerobic_te = activity.get("aerobicTrainingEffect")
    anaerobic_te = activity.get("anaerobicTrainingEffect")
    aerobic_te_val = round(float(aerobic_te), 1) if aerobic_te is not None else ""
    anaerobic_te_val = round(float(anaerobic_te), 1) if anaerobic_te is not None else ""

    feels_like_temp = ""
    weather_condition = ""
    wind_speed_kmh = ""

    if weather_data and isinstance(weather_data, dict):
        raw_temp = (
            weather_data.get("issueApparentTemp")
            or weather_data.get("apparentTemp")
            or weather_data.get("feelsLikeTemp")
            or weather_data.get("issueTemp")
            or weather_data.get("temp")
            or weather_data.get("temperature")
        )
        if raw_temp is not None:
            try:
                w_temp = float(raw_temp)
                watch_temp_c = full_act.get("averageTemperature") or activity.get("averageTemperature")
                needs_conversion = False
                if watch_temp_c is not None:
                    if abs(w_temp - float(watch_temp_c)) > 8:
                        needs_conversion = True
                else:
                    if w_temp > 45 or w_temp < -15:
                        needs_conversion = True

                if needs_conversion:
                    w_temp = (w_temp - 32) * 5.0 / 9.0
                feels_like_temp = round(w_temp, 1)
            except (ValueError, TypeError):
                pass

        weather_type = weather_data.get("issueWeatherType") or weather_data.get("weatherTypeDTO") or {}
        if isinstance(weather_type, dict):
            weather_condition = weather_type.get("desc", "")

        raw_wind = weather_data.get("issueWindSpeed") or weather_data.get("windSpeed")
        if raw_wind is not None:
            try:
                wind_speed_kmh = round(float(raw_wind), 1)
            except (ValueError, TypeError):
                pass

    row = {
        "Activity ID": act_id,
        "Date (YYYY-MM-DD)": date_str,
        "Start Time (HH:MM)": act_time_str,
        "Activity Type": type_key,
        "Activity Name": act_name or "",
        "Distance (km)": round(dist_km, 2) if dist_km else 0,
        "Duration (min)": round(dur_min, 1) if dur_min else 0,
        "Avg Pace (min/km)": pace_str,
        "Average Grade Adjusted Pace (min/km)": gap_str,
        "Total Ascent (m)": int(activity.get("elevationGain")) if activity.get("elevationGain") else "",
        "Total Descent (m)": int(activity.get("elevationLoss")) if activity.get("elevationLoss") else "",
        "Feels Like Temperature (Celsius)": feels_like_temp,
        "Weather Condition": weather_condition,
        "Sustained Wind Speed (km/h)": wind_speed_kmh,
        "Avg HR (bpm)": int(activity.get("averageHR")) if activity.get("averageHR") else "",
        "Max HR (bpm)": int(activity.get("maxHR")) if activity.get("maxHR") else "",
        "Average Cadence (spm)": int(avg_cadence) if avg_cadence else "",
        "Average Stride Length (m)": round(stride_len, 2) if stride_len else "",
        "Average Ground Contact Time (ms)": int(gct) if gct else "",
        "Vertical Oscillation (cm)": round(vert_osc, 2) if vert_osc else "",
        "Aerobic Training Effect (0.0-5.0)": aerobic_te_val,
        "Anaerobic Training Effect (0.0-5.0)": anaerobic_te_val,
        "Activity Training Load": round(training_load, 1) if training_load else "",
        "Avg Power (Watts)": int(activity.get("avgPower") or activity.get("averageRunningPower") or 0) or "",
        "Max Power (Watts)": int(max_power) if max_power else "",
        "Normalized Power (Watts)": int(norm_power) if norm_power else "",
        "Estimated Sweat Loss (ml)": int(sweat_loss) if sweat_loss else "",
        "Garmin Training Effect Label": activity.get("trainingEffectLabel") or "",
    }

    # Populate HR Zones
    for i in range(1, 6):
        row[f"HR Zone {i} (min)"] = ""
    if hr_zones and isinstance(hr_zones, list):
        for i in range(1, 6):
            row[f"HR Zone {i} (min)"] = 0.0
        for z in hr_zones:
            if isinstance(z, dict):
                z_num = z.get("zoneNumber")
                z_secs = z.get("secsInZone", 0)
                if z_num and 1 <= z_num <= 5:
                    row[f"HR Zone {z_num} (min)"] = round(z_secs / 60.0, 2)

    # Populate Power Zones
    for i in range(1, 6):
        row[f"Power Zone {i} (min)"] = ""
    if power_zones and isinstance(power_zones, list):
        for i in range(1, 6):
            row[f"Power Zone {i} (min)"] = 0.0
        for z in power_zones:
            if isinstance(z, dict):
                z_num = z.get("zoneNumber")
                z_secs = z.get("secsInZone", 0)
                if z_num and 1 <= z_num <= 5:
                    row[f"Power Zone {z_num} (min)"] = round(z_secs / 60.0, 2)

    return row
