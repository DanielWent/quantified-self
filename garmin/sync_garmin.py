import sys
import logging
from garmin.main import main
from garmin.config import DAYS_TO_SYNC

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        days_to_process = int(sys.argv[1])
    else:
        days_to_process = DAYS_TO_SYNC

    logger.info(f"Executing Garmin sync for {days_to_process} days.")
    main(days=days_to_process)
