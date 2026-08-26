import os
import logging
from datetime import datetime, date
from garminconnect import (
    Garmin,
    GarminConnectConnectionError,
    GarminConnectAuthenticationError,
    GarminConnectTooManyRequestsError,
)
from garmin.config import GARMIN_EMAIL, GARMIN_PASSWORD, GARMIN_TOKEN_STORE
from garmin.exceptions import GarminAuthException, GarminSyncException

logger = logging.getLogger(__name__)


class GarminClient:
    def __init__(self):
        self.email = GARMIN_EMAIL
        self.password = GARMIN_PASSWORD
        self.token_store = os.path.expanduser(GARMIN_TOKEN_STORE)
        self.client = None

    def login(self):
        try:
            if os.path.exists(self.token_store):
                logger.info(f"Logging in with token store at: {self.token_store}")
                self.client = Garmin()
                self.client.login(self.token_store)
            else:
                logger.info("Logging in with email and password")
                self.client = Garmin(self.email, self.password)
                self.client.login()
                os.makedirs(os.path.dirname(self.token_store), exist_ok=True)
                self.client.garth.dump(self.token_store)
            logger.info("Garmin authentication successful")
        except (
            GarminConnectAuthenticationError,
            GarminConnectTooManyRequestsError,
        ) as exc:
            logger.error(f"Authentication failed: {exc}")
            raise GarminAuthException(f"Failed to authenticate with Garmin: {exc}") from exc
        except Exception as exc:
            logger.error(f"Unexpected error during login: {exc}")
            raise GarminAuthException(f"Login error: {exc}") from exc

    def get_user_summary(self, target_date: str):
        try:
            return self.client.get_user_summary(target_date) or {}
        except Exception as exc:
            logger.warning(f"Could not retrieve user summary for {target_date}: {exc}")
            return {}

    def get_sleep_data(self, target_date: str):
        try:
            return self.client.get_sleep_data(target_date) or {}
        except Exception as exc:
            logger.warning(f"Could not retrieve sleep data for {target_date}: {exc}")
            return {}

    def get_hrv_data(self, target_date: str):
        try:
            return self.client.get_hrv_data(target_date) or {}
        except Exception as exc:
            logger.warning(f"Could not retrieve HRV data for {target_date}: {exc}")
            return {}

    def get_respiration_data(self, target_date: str):
        try:
            return self.client.get_respiration_data(target_date) or {}
        except Exception as exc:
            logger.warning(f"Could not retrieve respiration data for {target_date}: {exc}")
            return {}

    def get_spo2_data(self, target_date: str):
        try:
            return self.client.get_spo2_data(target_date) or {}
        except Exception as exc:
            logger.warning(f"Could not retrieve SpO2 data for {target_date}: {exc}")
            return {}

    def get_training_status(self, target_date: str):
        try:
            return self.client.get_training_status(target_date) or {}
        except Exception as exc:
            logger.warning(f"Could not retrieve training status for {target_date}: {exc}")
            return {}

    def get_max_metrics(self, target_date: str):
        try:
            return self.client.get_max_metrics(target_date) or {}
        except Exception as exc:
            logger.warning(f"Could not retrieve max metrics for {target_date}: {exc}")
            return {}

    def get_activities_by_date(self, start_date: str, end_date: str):
        try:
            return self.client.get_activities_by_date(start_date, end_date) or []
        except Exception as exc:
            logger.warning(
                f"Could not retrieve activities between {start_date} and {end_date}: {exc}"
            )
            return []
