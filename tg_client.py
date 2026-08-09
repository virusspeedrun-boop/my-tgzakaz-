import os
import json
import string
import random
import asyncio
import re
from telethon import TelegramClient

def generate_random_username(prefix: str, length: int) -> str:
    chars = string.ascii_lowercase + string.digits
    rand_hash = ''.join(random.choice(chars) for _ in range(length))
    return f"{prefix}{rand_hash}bot"

async def register_bot_and_app(session_path: str, json_path: str, prefix: str, hash_len: int, app_url: str):
    if not os.path.exists(json_path) or not os.path.exists(session_path):
        return {"status": "error", "message": "Файлы сессии повреждены или отсутствуют"}

    with open(json_path, 'r', encoding='utf-8') as f:
        try:
            acc_data = json.load(f)
        except Exception:
            return {"status": "error", "message": "Ошибка чтения конфигурационного JSON"}

    api_id = acc_data.get("api_id") or acc_data.get("app_id")
    api_hash = acc_data.get("api_hash") or acc_data.get("app_hash")

    if not api_id or not api_hash:
        return {"status": "error", "message": "В JSON отсутствуют параметры api_id/app_id или api_hash/app_hash"}

    try:
        client = TelegramClient(session_path, int(api_id), api_hash)
        await asyncio.wait_for(client.connect(), timeout=15)
    except asyncio.TimeoutError:
        return {"status": "error", "message": "Таймаут подключения к Telegram-клиенту"}
    except Exception as e:
        return {"status": "error", "message": f"Ошибка инициализации клиента: {str(e)}"}

    try:
        if not await client.is_user_authorized():
            await client.disconnect()
            return {"status": "error", "message": "Сессия невалидна или требует 2FA код"}
    except Exception as e:
        await client.disconnect()
        return {"status": "error", "message": f"Ошибка авторизации: {str(e)}"}

    bot_father = '@BotFather'
    try:
        token = "Не удалось извлечь автоматически"
        selected_username = None

        await client.send_message(bot_father, '/cancel')
        await asyncio.sleep(2)
        await client.send_message(bot_father, '/newbot')
        await asyncio.sleep(2)
        await client.send_message(bot_father, "App Launch Bot")
        await asyncio.sleep(2)

        for _ in range(20):
            selected_username = generate_random_username(prefix, hash_len)
            await client.send_message(bot_father, selected_username)
            await asyncio.sleep(3)

            # Безопасное чтение ответа через первую строчку сообщения
            messages = await client.get_messages(bot_father, limit=1)
            reply = messages[0].text if messages else ""

            if "Done! Congratulations" in reply:
                break
            elif "already taken" in reply or "invalid" in reply:
                continue

        await client.send_message(bot_father, '/newapp')
        await asyncio.sleep(2)
        await client.send_message(bot_father, f"@{selected_username}")
        await asyncio.sleep(2)
        await client.send_message(bot_father, "Web Application")
        await asyncio.sleep(2)
        await client.send_message(bot_father, "Telegram Mini App")
        await asyncio.sleep(2)
        await client.send_message(bot_father, app_url)
        await asyncio.sleep(2)
        await client.send_message(bot_father, "main")
        
        await asyncio.sleep(3)

        # Вытаскиваем токен чистой регуляркой из истории сообщений
        history = await client.get_messages(bot_father, limit=10)
        token_pattern = re.compile(r'\d+:[A-Za-z0-9_-]{35,}')

        if history:
            for msg in history:
                r_text = msg.text if msg and msg.text else ""
                match = token_pattern.search(r_text)
                if match:
                    token = match.group(0)
                    break

    except Exception as e:
        await client.disconnect()
        return {"status": "error", "message": f"Сбой во время диалога с BotFather: {str(e)}"}

    await client.disconnect()
    
    try:
        os.remove(session_path)
        os.remove(json_path)
    except Exception:
        pass

    # Исправлено: возвращаем ту же переменную selected_username, которая заполнялась в цикле
    return {"status": "success", "username": selected_username, "token": token}
