import os
import garth
from garminconnect import Garmin
from dotenv import load_dotenv

load_dotenv()

email = os.getenv("GARMIN_EMAIL")
password = os.getenv("GARMIN_PASSWORD")
tokenstore = os.getenv("GARMIN_TOKENS_PATH", ".garmin_tokens")
token_dir = os.path.expanduser(tokenstore)

if not email or not password:
    raise ValueError("GARMIN_EMAIL and GARMIN_PASSWORD are required.")

os.makedirs(token_dir, exist_ok=True)
client = Garmin(email, password)
client.login()
garth.save(token_dir)
print(f"Session successfully initialized in {token_dir}")
