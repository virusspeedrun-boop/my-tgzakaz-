import os
import json
import string
import random
import asyncio
import re
from telethon import TelegramClient

def _make_nick(prefix: str, length: int) -> str:
    src = string.ascii_lowercase + string.digits
    tail = "".join(random.choice(src) for _ in range(length))
    return f"{prefix}{tail}bot"

async def register_bot_and_app(session_path: str, json_path: str, prefix: str, hash_len: int, app_url: str):
    if not os.path.exists(json_path) or not os.path.exists(session_path):
        return {"status": "error", "message": "ERR_FILES_LOST"}

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception:
        return {"status": "error", "message": "ERR_JSON_READ"}

    api_id = meta.get("api_id") or meta.get("app_id")
    api_hash = meta.get("api_hash") or meta.get("app_hash")

    if not api_id or not api_hash:
        return {"status": "error", "message": "ERR_NO_CREDENTIALS"}

    try:
        client = TelegramClient(session_path, int(api_id), api_hash)
        await asyncio.wait_for(client.connect(), timeout=15)
    except asyncio.TimeoutError:
        return {"status": "error", "message": "ERR_TG_TIMEOUT"}
    except Exception as e:
        return {"status": "error", "message": f"ERR_CLIENT_INIT: {str(e)}"}

    try:
        if not await client.is_user_authorized():
            await client.disconnect()
            return {"status": "error", "message": "ERR_AUTH_REQUIRED"}
    except Exception as e:
        await client.disconnect()
        return {"status": "error", "message": f"ERR_SESSION_CHECK: {str(e)}"}

    bf = "@BotFather"
    username = None
    token = None
