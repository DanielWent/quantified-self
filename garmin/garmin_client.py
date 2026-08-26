import base64
from datetime import date, datetime
import json
import logging
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional

# Ensure directory is on sys.path for direct imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import GARMIN_EMAIL, GARMIN_PASSWORD, GARMIN_TOKENS
import garminconnect
import garth

logger = logging.getLogger(__name__)


def _check_for_429(e: Exception) -> None:
    """Helper to instantly kill the script if a 429 Too Many Requests is detected."""
    error_str = str(e).lower()
    if "429" in error_str or "too many requests" in error_str:
        print("\n" + "=" * 60)
        print("🚨 RATE LIMIT (429) DETECTED! 🚨")
        print("Stopping script immediately to prevent extending the ban.")
        response = getattr(
            e, "response", getattr(getattr(e, "__cause__", None), "response", None)
        )
        if response is not None:
            print("\n=== RATE LIMIT HEADERS ===")
            print(f"Retry-After: {response.headers.get('Retry-After', 'Not provided')}")
            print(
                f"X-RateLimit-Reset: {response.headers.get('X-RateLimit-Reset', 'Not provided')}"
            )
            print(f"All Headers: {dict(response.headers)}")
        else:
            print("\n(Could not automatically extract headers from the error object.)")
            print("Default to waiting 24 hours to be safe.")
        print("=" * 60 + "\n")
        sys.exit(1)


class GarminClient:
    def __init__(
        self,
        token_base64: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        profile_name: str = "default",
        manual_name: Optional[str] = None,
        manual_dob: Optional[str] = None,
        manual_gender: Optional[str] = None,
    ):
        self.token_base64 = token_base64 or GARMIN_TOKENS
        self.email = email or GARMIN_EMAIL
        self.password = password or GARMIN_PASSWORD
        self.profile_name = profile_name

        self.manual_name = manual_name or os.getenv("USER_NAME")
        self.manual_dob = manual_dob or os.getenv("USER_DOB")
        self.manual_gender = manual_gender or os.getenv("USER_GENDER")

        self.session_dir = Path(f"~/.garth/{self.profile_name}").expanduser()
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.token_file = self.session_dir / "tokens.json"

        self.client = None
        self._authenticated = False

        self.user_full_name = None
        self.user_age = None
        self.user_gender = None

        self._init_session()

    def _init_session(self) -> None:
        try:
            self.client = garminconnect.Garmin(self.email or "", self.password or "")
            self.client.garth = garth.Client(domain="garmin.com")

            # 1. Base64 or JSON token in environment variable
            if self.token_base64:
                try:
                    token_json = base64.b64decode(self.token_base64).decode("utf-8")
                except Exception:
                    token_json = self.token_base64

                try:
                    token_dict = json.loads(token_json)
                    self.client.login(token_dict)
                except Exception:
                    self.client.garth.loads(token_json)

                self._authenticated = True
                logger.info("Authenticated with Garmin using environment token.")
                self._fetch_user_profile_info()
                return

            # 2. Token file on disk
            if self.token_file.exists():
                try:
                    with open(self.token_file, "r", encoding="utf-8") as f:
                        saved_tokens = f.read().strip()
                    self.client.garth.loads(saved_tokens)
                    self._authenticated = True
                    logger.info(f"Resumed session successfully from {self.token_file}")
                    self._fetch_user_profile_info()
                    return
                except Exception as e:
                    _check_for_429(e)
                    logger.warning(f"Failed to resume session from disk: {e}")

            # 3. Email and password login
            if self.email and self.password:
                self.client.login()
                self._authenticated = True
                logger.info(f"Authenticated successfully as {self.email} (Fresh Login)")
                self._fetch_user_profile_info()
                self.save_session()
            else:
                raise ValueError("Missing Garmin credentials or tokens.")
        except Exception as e:
            _check_for_429(e)
            logger.error(f"Garmin session initialization failed: {e}")
            raise

    def save_session(self) -> None:
        """Saves current Garth OAuth tokens to disk."""
        try:
            with open(self.token_file, "w", encoding="utf-8") as f:
                f.write(self.client.garth.dumps())
            logger.debug(f"Saved session tokens to {self.token_file}")
        except Exception as e:
            logger.error(f"Failed to save session tokens: {e}")

    def _fetch_user_profile_info(self) -> None:
        if not getattr(self.client, "display_name", None):
            try:
                sp = self.client.connectapi("/userprofile-service/socialProfile")
                if sp and isinstance(sp, dict) and sp.get("displayName"):
                    self.client.display_name = sp["displayName"]
            except Exception as e:
                _check_for_429(e)
                logger.debug(f"Could not force-fetch display name: {e}")

        if self.manual_name:
            self.user_full_name = self.manual_name
        if self.manual_gender:
            self.user_gender = self.manual_gender

        if self.manual_dob:
            try:
                dob = datetime.strptime(self.manual_dob, "%Y-%m-%d").date()
                today = date.today()
                self.user_age = round((today - dob).days / 365.25, 1)
            except ValueError:
                logger.warning(f"Invalid format for manual_dob: {self.manual_dob}. Use YYYY-MM-DD.")

        try:
            if not self.user_full_name:
                display_name = getattr(self.client, "display_name", None)
                if display_name:
                    social_profile = self.client.get_social_profile(display_name)
                    if social_profile and isinstance(social_profile, dict):
                        self.user_full_name = social_profile.get("fullName")

            if not self.user_age:
                user_settings = self.client.get_user_settings()
                if user_settings and isinstance(user_settings, dict) and "userData" in user_settings:
                    dob_str = user_settings["userData"].get("birthDate")
                    if dob_str:
                        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
                        today = date.today()
                        self.user_age = round((today - dob).days / 365.25, 1)

            if not self.user_gender:
                user_settings = self.client.get_user_settings()
                if user_settings and isinstance(user_settings, dict) and "userData" in user_settings:
                    g_val = user_settings["userData"].get("gender")
                    if g_val:
                        self.user_gender = "Male" if str(g_val).upper() in ["M", "MALE"] else "Female"
        except Exception as e:
            _check_for_429(e)
            logger.debug(f"Error fetching user profile fallback: {e}")

    def safe_call(self, name: str, func, *args, delay: float = 0.5, **kwargs):
        try:
            if delay > 0:
                time.sleep(delay)
            return func(*args, **kwargs)
        except Exception as e:
            _check_for_429(e)
            logger.warning(f"Failed to fetch {name}: {e}")
            return None

    def get_user_profile(self) -> Dict[str, Any]:
        return {
            "user_name": self.user_full_name,
            "user_age": self.user_age,
            "user_gender": self.user_gender,
        }

    def get_stats(self, date_str: str):
        return self.safe_call("User Summary", self.client.get_user_summary, date_str)

    def get_body_composition(self, date_str: str):
        return self.safe_call("Body Composition", self.client.get_body_composition, date_str, date_str)

    def get_sleep_data(self, date_str: str):
        return self.safe_call("Sleep Data", self.client.get_sleep_data, date_str)

    def get_rhr_data(self, date_str: str):
        return self.safe_call("RHR Data", self.client.get_rhr_day_data, date_str)

    def get_hrv_data(self, date_str: str):
        return self.safe_call("HRV Data", self.client.get_hrv_data, date_str)

    def get_blood_pressure(self, date_str: str):
        return self.safe_call("Blood Pressure", self.client.get_blood_pressure, date_str)

    def get_training_status(self, date_str: str):
        return self.safe_call("Training Status Standard", self.client.get_training_status, date_str)

    def get_training_status_modern(self, date_str: str):
        url = f"metrics-service/metrics/trainingstatus/aggregated/{date_str}"
        return self.safe_call("Training Status Modern", self.client.connectapi, url)

    def get_lactate_direct(self):
        return self.safe_call("Lactate Direct", self.client.connectapi, "biometric-service/biometric/latestLactateThreshold")

    def get_lactate_range_hr(self, date_str: str):
        url = f"biometric-service/stats/lactateThresholdHeartRate/range/{date_str}/{date_str}"
        params = {"aggregationStrategy": "LATEST", "sport": "RUNNING"}
        return self.safe_call("Lactate Range HR", self.client.connectapi, url, params=params)

    def get_lactate_range_speed(self, date_str: str):
        url = f"biometric-service/stats/lactateThresholdSpeed/range/{date_str}/{date_str}"
        params = {"aggregationStrategy": "LATEST", "sport": "RUNNING"}
        return self.safe_call("Lactate Range Speed", self.client.connectapi, url, params=params)

    def get_training_readiness(self, date_str: str):
        return self.safe_call("Training Readiness", self.client.get_training_readiness, date_str)

    def get_activities(self, start_date: Optional[str] = None, end_date: Optional[str] = None, limit: int = 2000):
        if start_date and end_date and isinstance(start_date, str) and isinstance(end_date, str):
            try:
                return self.safe_call("Activities by Date", self.client.get_activities_by_date, start_date, end_date) or []
            except Exception as e:
                _check_for_429(e)
                logger.warning(f"get_activities_by_date failed: {e}")
        return self.safe_call("Activities Paginated", self.client.get_activities, 0, limit) or []

    def get_activity_details(self, activity_id: Any):
        if hasattr(self.client, "get_activity"):
            act = self.safe_call(f"Activity {activity_id} Details", self.client.get_activity, activity_id)
            if act:
                return act
        return self.safe_call(f"Activity {activity_id} ConnectAPI", self.client.connectapi, f"activity-service/activity/{activity_id}")

    def get_activity_weather(self, activity_id: Any):
        return self.safe_call(f"Activity {activity_id} Weather", self.client.get_activity_weather, activity_id)

    def get_activity_hr_zones(self, activity_id: Any):
        zones = self.safe_call(f"Activity {activity_id} HR Zones", self.client.get_activity_hr_in_timezones, activity_id)
        if zones is None:
            zones = self.safe_call(f"Activity {activity_id} HR Zones ConnectAPI", self.client.connectapi, f"activity-service/activity/{activity_id}/hrTimeInZones")
        return zones

    def get_activity_power_zones(self, activity_id: Any):
        return self.safe_call(f"Activity {activity_id} Power Zones", self.client.connectapi, f"activity-service/activity/{activity_id}/powerTimeInZones")

    def fetch_daily_payloads(self, date_str: str) -> Dict[str, Any]:
        """Fetches all daily raw payloads sequentially with rate-limit spacing."""
        summary = self.get_stats(date_str)
        stats = self.get_body_composition(date_str)
        sleep = self.get_sleep_data(date_str)
        hrv = self.get_hrv_data(date_str)
        bp = self.get_blood_pressure(date_str)
        ts_std = self.get_training_status(date_str)
        ts_modern = self.get_training_status_modern(date_str)
        lactate_direct = self.get_lactate_direct()
        lactate_hr = self.get_lactate_range_hr(date_str)
        lactate_spd = self.get_lactate_range_speed(date_str)
        readiness = self.get_training_readiness(date_str)

        return {
            "summary": summary,
            "stats": stats,
            "sleep_data": sleep,
            "hrv_payload": hrv,
            "bp_payload": bp,
            "training_status_std": ts_std,
            "training_status_modern": ts_modern,
            "lactate_data": lactate_direct,
            "lactate_range_hr": lactate_hr,
            "lactate_range_speed": lactate_spd,
            "readiness_data": readiness,
        }

    def fetch_activity_payloads(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Fetches full details, weather, and zone breakdowns for a single activity."""
        act_id = activity.get("activityId")
        full_act = None
        weather = None
        hr_zones = None
        power_zones = None

        if act_id:
            full_act = self.get_activity_details(act_id)
            weather = self.get_activity_weather(act_id)
            hr_zones = self.get_activity_hr_zones(act_id)
            power_zones = self.get_activity_power_zones(act_id)

        return {
            "activity": activity,
            "full_activity": full_act or activity,
            "weather_data": weather,
            "hr_zones": hr_zones,
            "power_zones": power_zones,
        }
