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
    selected_username = None
    token = None
    try:
        # ЗАПУСКАЕМ ЖИВОЙ ИНТЕРАКТИВНЫЙ ДИАЛОГ С BOTFATHER
        async with client.conversation(bot_father, timeout=60) as conv:
            # Сбрасываем старые зависшие команды
            await conv.send_message('/cancel')
            await asyncio.sleep(1)
            
            # Начинаем создание бота
            await conv.send_message('/newbot')
            await conv.get_response() # Ждем ответа "Alright, a new bot..."
            
            await conv.send_message("App Launch Bot")
            await conv.get_response() # Ждем ответа "Good. Now let's choose a username..."

            # Цикл подбора свободного юзернейма в реальном времени
            for _ in range(25):
                selected_username = generate_random_username(prefix, hash_len)
                await conv.send_message(selected_username)
                
                # Читаем точный живой ответ от BotFather
                response = await conv.get_response()
                reply_text = response.text if response and response.text else ""

                if "Done! Congratulations" in reply_text:
                    # Извлекаем токен из победного сообщения регуляркой
                    token_pattern = re.compile(r'\d+:[A-Za-z0-9_-]{35,}')
                    match = token_pattern.search(reply_text)
                    if match:
                        token = match.group(0)
                    break
                elif "already taken" in reply_text or "invalid" in reply_text:
                    continue

            if not token:
                await client.disconnect()
                return {"status": "error", "message": "Не удалось подобрать свободный юзернейм в BotFather"}

            # Начинаем привязку Web App (Mini App)
            await conv.send_message('/newapp')
            await conv.get_response() # Ждем ответа "Choose a bot..."
            
            await conv.send_message(f"@{selected_username}")
            await conv.get_response() # Ждем ответа "Please choose a title..."
            
            await conv.send_message("Web Application")
            await conv.get_response() # Ждем ответа "Please choose a description..."
            
            await conv.send_message("Telegram Mini App")
            await conv.get_response() # Ждем ответа "Please send the URL..."
            
            await conv.send_message(app_url)
            await conv.get_response() # Ждем ответа "Please choose a short name..."
            
            await conv.send_message("main")
            await conv.get_response() # Финальный ответ об успехе Mini App

    except Exception as e:
        await client.disconnect()
        return {"status": "error", "message": f"Сбой интерактива BotFather: {str(e)}"}

    await client.disconnect()
    
    try:
        os.remove(session_path)
        os.remove(json_path)
    except Exception: pass

    return {"status": "success", "username": selected_username, "token": token}
