import os
import json
import logging
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

def resolve_data_file(filename, subdirs=None):
    if os.path.exists(filename):
        return filename
    if subdirs:
        for subdir in subdirs:
            candidate = os.path.join(subdir, filename)
            if os.path.exists(candidate):
                return candidate
    return None

def load_json_file(primary_name, subdirs=None):
    filepath = resolve_data_file(primary_name, subdirs)
    if filepath and os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read {filepath}: {e}")
    return []

def calculate_quantified_self():
    try:
        days_to_sync = int(os.getenv("DAYS_TO_SYNC", 7))
    except (ValueError, TypeError):
        days_to_sync = 7

    logger.info(f"Generating Quantified Self aggregation for {days_to_sync} days...")

    garmin_records = load_json_file("garmin_data.json", ["garmin", "."])
    withings_records = load_json_file("withings_data.json", ["withings", "."])

    cutoff_date = (datetime.now() - timedelta(days=days_to_sync)).date().isoformat()

    filtered_garmin = [
        r for r in garmin_records
        if isinstance(r, dict) and r.get("date", "") >= cutoff_date
    ]
    filtered_withings = [
        r for r in withings_records
        if isinstance(r, dict) and r.get("date", "") >= cutoff_date
    ]

    total_steps = sum(r.get("steps", 0) for r in filtered_garmin)
    sleep_scores = [r.get("sleep_score") for r in filtered_garmin if r.get("sleep_score") is not None]
    rhr_values = [r.get("resting_heart_rate") for r in filtered_garmin if r.get("resting_heart_rate") is not None]
    hrv_values = [r.get("hrv_avg") for r in filtered_garmin if r.get("hrv_avg") is not None]

    weights = []
    fat_ratios = []
    for r in filtered_withings:
        measures = r.get("measures", {})
        if "weight_kg" in measures:
            weights.append(measures["weight_kg"])
        if "fat_ratio_pct" in measures:
            fat_ratios.append(measures["fat_ratio_pct"])

    summary = {
        "sync_window_days": days_to_sync,
        "start_date": cutoff_date,
        "garmin_days_recorded": len(filtered_garmin),
        "withings_days_recorded": len(filtered_withings),
        "metrics": {
            "total_steps": total_steps,
            "avg_daily_steps": (total_steps / len(filtered_garmin)) if filtered_garmin else 0,
            "avg_sleep_score": (sum(sleep_scores) / len(sleep_scores)) if sleep_scores else None,
            "avg_resting_heart_rate": (sum(rhr_values) / len(rhr_values)) if rhr_values else None,
            "avg_hrv": (sum(hrv_values) / len(hrv_values)) if hrv_values else None,
            "avg_weight_kg": (sum(weights) / len(weights)) if weights else None,
            "avg_fat_ratio_pct": (sum(fat_ratios) / len(fat_ratios)) if fat_ratios else None
        }
    }

    output_path = "quantified_self_summary.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    logger.info(f"Successfully generated {output_path} with {len(filtered_garmin)} Garmin and {len(filtered_withings)} Withings days processed.")

if __name__ == "__main__":
    calculate_quantified_self()
