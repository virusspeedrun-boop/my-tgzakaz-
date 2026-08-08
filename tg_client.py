import os
import json
import string
import random
import asyncio
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

    # Универсальное считывание: ищет и api_id, и app_id
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
        await client.send_message(bot_father, '/cancel')
        await asyncio.sleep(2)
        await client.send_message(bot_father, '/newbot')
        await asyncio.sleep(2)
        await client.send_message(bot_father, "App Launch Bot")
        await asyncio.sleep(2)

        token = None
        selected_username = None
        
        for _ in range(20):
            selected_username = generate_random_username(prefix, hash_len)
            await client.send_message(bot_father, selected_username)
            await asyncio.sleep(3)

            messages = await client.get_messages(bot_father, limit=1)
            reply = messages.text if messages else ""

            if "Done! Congratulations" in reply:
                try:
                    for line in reply.split("\n"):
                        if ":" in line and len(line) > 30:
                            token = line.strip()
                            break
                except Exception:
                    token = "Ошибка извлечения токена"
                break
            elif "already taken" in reply or "invalid" in reply:
                continue

        if not token:
            await client.disconnect()
            return {"status": "error", "message": "Превышено число попыток генерации свободного юзернейма"}

        await client.send_message(bot_father, '/newapp')
        await asyncio.sleep(2)
        await client.send_message(bot_father, f"@{selected_username}")
        await asyncio.sleep(2)
        await client.send_message(bot_father, "Web Application")
        await asyncio.sleep(2)
        await client.send_message(bot_father, "Mini App Description")
        await asyncio.sleep(2)
        await client.send_message(bot_father, app_url)
        await asyncio.sleep(2)
        await client.send_message(bot_father, "main")
        await asyncio.sleep(3)

    except Exception as e:
        await client.disconnect()
        return {"status": "error", "message": f"Сбой во время диалога с BotFather: {str(e)}"}

    await client.disconnect()
    
    try:
        os.remove(session_path)
        os.remove(json_path)
    except Exception:
        pass

    return {"status": "success", "username": selected_username, "token": token}
