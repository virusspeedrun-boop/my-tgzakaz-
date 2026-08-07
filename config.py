import os

BOT_TOKEN = "8307051627:AAFnXTHGcZSn4Hyt08d8HVPf9poMeUIG8xE"

allowed_raw = os.environ.get("ALLOWED_USERS", "8310775460")
ALLOWED_USERS = [int(x.strip()) for x in allowed_raw.split(",") if x.strip().isdigit()]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")

os.makedirs(SESSIONS_DIR, exist_ok=True)
