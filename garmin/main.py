import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from sync_garmin import sync_garmin_data, DAYS_TO_SYNC

def main(days: int = None):
    sync_garmin_data(days=days)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        days_input = int(sys.argv[1])
    else:
        days_input = DAYS_TO_SYNC
    main(days=days_input)
