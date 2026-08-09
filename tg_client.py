import os
import json
import asyncio
import re
from telethon import TelegramClient

def get_seo_username(keyword: str, index: int) -> str:
    # Список самых популярных комбинаций для вывода дорвеев в топ поиска Telegram
    suffixes = [
        "bot",
        "_bot",
        "robot",
        "rbot",
        "_robot",
        "tbot",
        "_tbot",
        "official_bot",
        "_official_bot",
        "launch_bot"
    ]
    # Если аккаунтов больше, чем вариантов, запускаем круг заново, добавляя случайную цифру
    loop_num = index // len(suffixes)
    suffix_item = suffixes[index % len(suffixes)]
    
    if loop_num == 0:
        return f"{keyword}{suffix_item}"
    else:
        return f"{keyword}{loop_num}{suffix_item}"

async def register_bot_and_app(session_path: str, json_path: str, keyword: str, app_url: str, index_num: int):
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
        
        # Получаем уникальный поисковый юзернейм для этого аккаунта по его индексу в очереди
        target_username = get_seo_username(keyword, index_num)

        await client.send_message(bot_father, '/cancel')
        await asyncio.sleep(2)
        await client.send_message(bot_father, '/newbot')
        await asyncio.sleep(2)
        
        # Название бота в поиске (Ключевое слово капсом для максимального SEO-эффекта)
        await client.send_message(bot_father, f"{keyword.upper()} | Official Bot")
        await asyncio.sleep(2)

        # Отправляем сгенерированное поисковое имя
        await client.send_message(bot_father, target_username)
        await asyncio.sleep(3)

        # Проверяем ответ от BotFather
        messages = await client.get_messages(bot_father, limit=1)
        reply = messages[0].text if messages and len(messages) > 0 else ""

        # Если имя вдруг уже кем-то занято, софт добавит в конец случайное число, чтобы забить свободную нишу
        if "already taken" in reply or "invalid" in reply:
            for _ in range(5):
                rand_num = random.randint(10, 99)
                target_username = f"{keyword}{rand_num}bot"
                await client.send_message(bot_father, target_username)
                await asyncio.sleep(3)
                
                check_msg = await client.get_messages(bot_father, limit=1)
                reply = check_msg[0].text if check_msg and len(check_msg) > 0 else ""
                if "Done! Congratulations" in reply:
                    break

        # Привязываем Mini App домен
        await client.send_message(bot_father, '/newapp')
        await asyncio.sleep(2)
        await client.send_message(bot_father, f"@{target_username}")
        await asyncio.sleep(2)
        await client.send_message(bot_father, "Web Application")
        await asyncio.sleep(2)
        await client.send_message(bot_father, f"SEO Дорвей-перенаправление проекта {keyword.upper()}")
        await asyncio.sleep(2)
        await client.send_message(bot_father, app_url)
        await asyncio.sleep(2)
        await client.send_message(bot_father, "main")
        await asyncio.sleep(3)

        # Вытаскиваем готовый токен регулярным выражением из последних 10 сообщений диалога
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

    return {"status": "success", "username": target_username, "token": token}
