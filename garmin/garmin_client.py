import logging
from garminconnect import Garmin

try:
    from exceptions import GarminAuthError
except ImportError:
    try:
        from garmin.exceptions import GarminAuthError
    except ImportError:
        class GarminAuthError(Exception):
            pass

logger = logging.getLogger(__name__)

class GarminClient:
    def __init__(self, email: str, password: str, tokenstore_path: str = None):
        try:
            self.client = Garmin(email=email, password=password)
            if tokenstore_path:
                self.client.login(tokenstore_path)
            else:
                self.client.login()
        except Exception as e:
            raise GarminAuthError(f"Failed to authenticate with Garmin Connect: {e}")

    def get_user_profile(self) -> dict:
        """Fetches profile info (Name, Gender, Birth Date)."""
        try:
            return self.client.get_user_profile() or {}
        except Exception as e:
            logger.warning(f"Could not fetch user profile: {e}")
            return {}

    def get_user_settings(self) -> dict:
        """Fetches user biometrics including max heart rate."""
        try:
            if hasattr(self.client, "garth") and hasattr(self.client.garth, "connectapi"):
                return self.client.garth.connectapi("/userprofile-service/userprofile/user-settings") or {}
            return {}
        except Exception as e:
            logger.warning(f"Could not fetch user settings: {e}")
            return {}

    def get_daily_summary(self, date_str: str) -> dict:
        """Fetches daily summary data (steps, resting HR, stress, sleep)."""
        try:
            return self.client.get_user_summary(date_str) or {}
        except Exception as e:
            logger.error(f"Failed to fetch daily summary for {date_str}: {e}")
            return {}

    def get_max_metrics(self, date_str: str):
        """Fetches VO2 Max metrics for a specific date."""
        try:
            return self.client.get_max_metrics(date_str) or []
        except Exception as e:
            logger.warning(f"Could not fetch VO2 max metrics for {date_str}: {e}")
            return []
