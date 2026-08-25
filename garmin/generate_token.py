import os
from garminconnect import Garmin
from dotenv import load_dotenv

load_dotenv()

email = os.getenv("GARMIN_EMAIL")
password = os.getenv("GARMIN_PASSWORD")
tokenstore = os.getenv("GARMIN_TOKENS_PATH", ".garmin_tokens")

client = Garmin(email, password)
client.login()
client.garth.dump(tokenstore)
print(f"Tokens saved to {tokenstore}")
