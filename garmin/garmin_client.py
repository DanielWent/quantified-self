import os
from garminconnect import Garmin, GarminConnectAuthenticationError

class GarminSyncClient:
    def __init__(self, email: str = None, password: str = None, tokenstore_path: str = None):
        self.email = email or os.getenv("GARMIN_EMAIL")
        self.password = password or os.getenv("GARMIN_PASSWORD")
        self.tokenstore = tokenstore_path or os.getenv("GARMIN_TOKENS_PATH", ".garmin_tokens")
        self.client = None

    def login(self):
        try:
            if os.path.exists(self.tokenstore):
                self.client = Garmin()
                self.client.login(self.tokenstore)
            else:
                self.client = Garmin(self.email, self.password)
                self.client.login()
                self.client.garth.dump(self.tokenstore)
        except Exception as e:
            raise GarminConnectAuthenticationError(f"Authentication failed: {e}")

    def get_stats(self, date_str: str) -> dict:
        return self.client.get_user_summary(date_str)

    def get_sleep(self, date_str: str) -> dict:
        return self.client.get_sleep_data(date_str)

    def get_hrv(self, date_str: str) -> dict:
        return self.client.get_hrv_data(date_str)

    def get_body_battery(self, date_str: str) -> list:
        return self.client.get_body_battery(date_str)

    def get_activities(self, start_date: str, limit: int = 50) -> list:
        return self.client.get_activities(0, limit)
