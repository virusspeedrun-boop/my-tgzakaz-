import os

# Вставь сюда токен твоего управляющего бота между кавычками
BOT_TOKEN = "8779018854:AAFE9h5II_4VLEIwbv9G8TGeHpCVlHjmrQ8"

# Вставь свой числовой ID без кавычек (например: 8310775460)
ALLOWED_USERS = [8310775460]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")

os.makedirs(SESSIONS_DIR, exist_ok=True)
