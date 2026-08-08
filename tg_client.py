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
        selected_username = "Бот уже создан"

        # Запрашиваем список токенов
        await client.send_message(bot_father, '/token')
        await asyncio.sleep(3)
        
        # Забираем сообщение с инлайн-кнопками ботов
        messages = await client.get_messages(bot_father, limit=1)
        if messages and messages[0].reply_markup:
            # Нажимаем на самую первую кнопку (это наш созданный бот)
            try:
                await messages[0].click(0)
                await asyncio.sleep(3)
                
                # Читаем прилетевший токен
                token_msgs = await client.get_messages(bot_father, limit=1)
                reply = token_msgs[0].text if token_msgs else ""
                
                for line in reply.split("\n"):
                    clean_line = line.strip()
                    if ":" in clean_line and len(clean_line) > 40 and not clean_line.startswith("Use"):
                        token = clean_line
                        break
            except Exception:
                pass

        # Если кнопка не нажалась, ищем токен по истории сообщений
        if token == "Не удалось извлечь автоматически":
            all_msgs = await client.get_messages(bot_father, limit=15)
            for m in all_msgs:
                reply = m.text if m and m.text else ""
                if ":" in reply and "Use this token" not in reply:
                    for line in reply.split("\n"):
                        clean_line = line.strip()
                        if ":" in clean_line and len(clean_line) > 40 and not clean_line.startswith("Use"):
                            token = clean_line
                            break
                if token != "Не удалось извлечь автоматически":
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

    return {"status": "success", "username": selected_username, "token": token}
