import os
import logging
from config import DAYS_TO_SYNC
from sync_garmin import sync_garmin_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        days = int(os.getenv("DAYS_TO_SYNC", DAYS_TO_SYNC))
    except (ValueError, TypeError):
        days = DAYS_TO_SYNC
    logger.info(f"Executing main Garmin sync routine for {days} days")
    sync_garmin_data(days=days)
