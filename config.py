import os

BOT_TOKEN = "8307051627:AAFnXTHGcZSn4Hyt08d8HVPf9poMeUIG8xE"
ALLOWED_USERS = [8310775465, 8237762407]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")

os.makedirs(SESSIONS_DIR, exist_ok=True)
