import os

BOT_TOKEN = "УКАЖИ_ТОКЕН_ГЛАВНОГО_УПРАВЛЯЮЩЕГО_BOT_ФАЗЕРА"
ALLOWED_USERS =  # ID пользователей через запятую

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")

os.makedirs(SESSIONS_DIR, exist_ok=True)
