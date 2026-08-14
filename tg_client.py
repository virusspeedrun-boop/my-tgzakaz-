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
    try:
        async with client.conversation(bf, timeout=45) as conv:
            await conv.send_message("/cancel")
            await asyncio.sleep(1)
            await conv.send_message("/newbot")
            await conv.get_response()
            
            await conv.send_message("App Launch Bot")
            await conv.get_response()

            for _ in range(25):
                username = _make_nick(prefix, hash_len)
                await conv.send_message(username)
                
                res = await conv.get_response()
                raw_text = res.text if res and res.text else ""

                if "Done! Congratulations" in raw_text:
                    match = re.search(r"\d+:[A-Za-z0-9_-]{35,}", raw_text)
                    if match:
                        token = match.group(0)
                    break
                elif "already taken" in raw_text or "invalid" in raw_text:
                    continue

        if not token:
            await client.disconnect()
            return {"status": "error", "message": "ERR_NICK_GEN_FAILED"}

        await client.send_message(bf, "/cancel")
        await asyncio.sleep(2)
        await client.send_message(bf, "/newapp")
        await asyncio.sleep(2)
        await client.send_message(bf, f"@{username}")
        await asyncio.sleep(2)
        await client.send_message(bf, "Web Application")
        await asyncio.sleep(2)
        await client.send_message(bf, "Telegram Mini App")
        await asyncio.sleep(2)
        await client.send_message(bf, app_url)
        await asyncio.sleep(2)
        await client.send_message(bf, "main")
        await asyncio.sleep(3)

    except Exception as e:
        await client.disconnect()
        return {"status": "error", "message": f"ERR_DIALOG_CRASH: {str(e)}"}

    await client.disconnect()
    
    try:
        os.remove(session_path)
        os.remove(json_path)
    except Exception:
        pass

    return {"status": "success", "username": username, "token": token}
