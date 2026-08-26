import os
import json
import base64
import logging
from garminconnect import Garmin
from config import GARMIN_TOKENS, GARMIN_EMAIL, GARMIN_PASSWORD

logger = logging.getLogger(__name__)

class GarminClient:
    def __init__(self):
        self.token_base64 = GARMIN_TOKENS
        self.email = GARMIN_EMAIL
        self.password = GARMIN_PASSWORD
        self.client = None
        self._init_session()

    def _init_session(self):
        try:
            if self.token_base64:
                token_json = base64.b64decode(self.token_base64).decode("utf-8")
                token_dict = json.loads(token_json)
                self.client = Garmin()
                self.client.login(token_dict)
                logger.info("Authenticated with Garmin using token.")
            elif self.email and self.password:
                self.client = Garmin(self.email, self.password)
                self.client.login()
                logger.info("Authenticated with Garmin using credentials.")
            else:
                raise ValueError("Missing Garmin credentials or tokens.")
        except Exception as e:
            logger.error(f"Garmin session initialization failed: {e}")
            raise

    def get_stats(self, date_str):
        return self.client.get_user_summary(date_str)

    def get_sleep_data(self, date_str):
        return self.client.get_sleep_data(date_str)

    def get_rhr_data(self, date_str):
        return self.client.get_rhr_day_data(date_str)

    def get_hrv_data(self, date_str):
        return self.client.get_hrv_data(date_str)

    def get_activities(self, start_date=None, end_date=None, limit=2000):
        if isinstance(start_date, int):
            return self.client.get_activities(0, start_date)
        if start_date and end_date and isinstance(start_date, str) and isinstance(end_date, str):
            try:
                return self.client.get_activities_by_date(start_date, end_date)
            except Exception as e:
                logger.warning(f"get_activities_by_date failed, falling back to paginated search: {e}")
        return self.client.get_activities(0, limit)
