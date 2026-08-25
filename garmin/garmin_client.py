import logging
import os
from typing import Any, Dict, List, Optional
import garth
from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

logger = logging.getLogger(__name__)

class GarminClient:
    def __init__(self, email: Optional[str] = None, password: Optional[str] = None, tokenstore: Optional[str] = None):
        self.email = email
        self.password = password
        self.tokenstore = os.path.expanduser(tokenstore) if tokenstore else None
        self.client: Optional[Garmin] = None

    def login(self) -> None:
        try:
            if self.tokenstore and os.path.exists(self.tokenstore) and os.listdir(self.tokenstore):
                logger.info(f"Resuming Garth session from {self.tokenstore}")
                garth.resume(self.tokenstore)
                self.client = Garmin()
                self.client.login()
                logger.info("Successfully resumed Garmin session.")
                return

            if self.email and self.password:
                logger.info("Logging into Garmin Connect with email/password...")
                self.client = Garmin(self.email, self.password)
                self.client.login()
                if self.tokenstore:
                    os.makedirs(self.tokenstore, exist_ok=True)
                    garth.save(self.tokenstore)
                    logger.info(f"Saved session tokens to {self.tokenstore}")
                return

            raise GarminConnectAuthenticationError("Missing credentials or valid token store.")
        except Exception as e:
            logger.error(f"Garmin authentication failed: {e}")
            raise

    def get_user_summary(self, date_str: str) -> Dict[str, Any]:
        return self.client.get_user_summary(date_str)

    def get_sleep_data(self, date_str: str) -> Dict[str, Any]:
        return self.client.get_sleep_data(date_str)

    def get_hrv_data(self, date_str: str) -> Dict[str, Any]:
        return self.client.get_hrv_data(date_str)

    def get_activities(self, start: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        return self.client.get_activities(start, limit)
