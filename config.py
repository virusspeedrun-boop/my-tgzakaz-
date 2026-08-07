import os

# Твой новый токен бота
BOT_TOKEN = "8307051627:AAFnXTHGcZSn4Hyt08d8HVPf9poMeUIG8xE"

# Твой точный Telegram ID с правильной цифрой на конце
ALLOWED_USERS = [8310775465]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")

os.makedirs(SESSIONS_DIR, exist_ok=True)
