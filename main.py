import os
import asyncio
import zipfile
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiohttp import web

import config
import tg_client

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

class BotSettings(StatesGroup):
    waiting_for_url = State()
    waiting_for_hash = State()
    waiting_for_prefix = State()
    waiting_for_global_prefix = State()
    waiting_for_doorway_target = State()

runtime_settings = {
    "url": "https://example.com",
    "hash_len": 3,
    "doorway_target": "xhevn"
}

user_queue = {}

def check_permission(message: types.Message) -> bool:
    return message.from_user.id in config.ALLOWED_USERS

def build_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚙️ Настройки софта"), KeyboardButton(text="📋 Моя очередь")],
            [KeyboardButton(text="🚀 Запустить генерацию")]
        ],
        resize_keyboard=True
    )

@dp.message(Command("start"), check_permission)
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    if uid not in user_queue:
        user_queue[uid] = {}
        
    await message.answer(
        "Система автоматического создания поисковых SEO-дорвеев готова.\n\n"
        "Вы можете отправлять файлы .session и .json в .zip архиве.\n"
        "После загрузки перейдите в меню настроек для указания ключевого слова.",
        reply_markup=build_main_keyboard()
    )
@dp.message(F.text == "⚙️ Настройки софта", check_permission)
async def show_settings(message: types.Message):
    text = (
        f"⚙️ **Текущие параметры автоматизации:**\n\n"
        f"🌐 **Mini App Домен:** `{runtime_settings['url']}`\n"
        f"🔑 **Ключевое слово для поиска:** `{runtime_settings['doorway_target']}`\n\n"
        f"*_При генерации софт автоматически подставит комбинации bot, _bot, robot, rbot, _official_bot и т.д._*"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить домен Mini App", callback_data="change_url")],
        [InlineKeyboardButton(text="🔗 Задать ключевое слово (Поиск)", callback_data="change_doorway")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "change_url")
async def process_change_url(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправьте новый целевой URL-домен для привязки к Mini App:")
    await state.set_state(BotSettings.waiting_for_url)
    await callback.answer()

@dp.message(BotSettings.waiting_for_url, check_permission)
async def update_url(message: types.Message, state: FSMContext):
    url = message.text.strip()
    if not url.startswith(("http://", "https://")):
        await message.answer("Ошибка: URL должен начинаться с http:// или https://. Попробуйте еще раз.")
        return
    runtime_settings["url"] = url
    await state.clear()
    await message.answer(f"✅ Домен успешно изменен на: `{url}`", parse_mode="Markdown", reply_markup=build_main_keyboard())

@dp.callback_query(F.data == "change_doorway")
async def process_change_doorway(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправьте ключевое слово (основу) для генерации дорвеев (например: `xhevn` без знака @):")
    await state.set_state(BotSettings.waiting_for_doorway_target)
    await callback.answer()

@dp.message(BotSettings.waiting_for_doorway_target, check_permission)
async def update_doorway_target(message: types.Message, state: FSMContext):
    target = message.text.strip().replace("@", "")
    runtime_settings["doorway_target"] = target
    await state.clear()
    await message.answer(f"✅ Ключевая SEO-основа изменена на: `{target}`", parse_mode="Markdown", reply_markup=build_main_keyboard())

@dp.message(F.document, check_permission)
async def catch_documents(message: types.Message):
    uid = message.from_user.id
    doc = message.document
    filename = doc.file_name
    base, ext = os.path.splitext(filename)

    if uid not in user_queue:
        user_queue[uid] = {}

    target_path = os.path.join(config.SESSIONS_DIR, filename)
    file_info = await bot.get_file(doc.file_id)
    await bot.download_file(file_info.file_path, target_path)

    if ext == '.zip':
        try:
            with zipfile.ZipFile(target_path, 'r') as zip_ref:
                for member in zip_ref.namelist():
                    if member.endswith('/'):
                        continue
                    pure_filename = os.path.basename(member)
                    m_base, m_ext = os.path.splitext(pure_filename)
                    if m_ext in ['.session', '.json']:
                        extracted_path = os.path.join(config.SESSIONS_DIR, pure_filename)
                        with open(extracted_path, "wb") as f:
                            f.write(zip_ref.read(member))
                        if m_ext == '.session' and m_base not in user_queue[uid]:
                            user_queue[uid][m_base] = "qq"
            os.remove(target_path)
            await message.answer("📦 Архив успешно распакован! Все сессии добавлены в очередь.", parse_mode="Markdown")
            return
        except Exception as e:
            await message.answer(f"❌ Ошибка при распаковке архива: {str(e)}")
            if os.path.exists(target_path): os.remove(target_path)
            return

    if ext == '.session' and base not in user_queue[uid]:
        user_queue[uid][base] = "qq"

    await message.answer(f"📥 Загружен и сохранен файл: {filename}")
@dp.message(F.text == "📋 Моя очередь", check_permission)
async def show_queue(message: types.Message):
    uid = message.from_user.id
    if uid not in user_queue or not user_queue[uid]:
        await message.answer("Ваша очередь пуста. Отправьте файлы сессий в .zip архиве.")
        return

    text = "📋 **Загруженные аккаунты в очереди:**\n\n"
    kb_list = []
    
    current_items = list(user_queue[uid].items())
    for idx, (name, prefix) in enumerate(current_items):
        text += f"▪️ Аккаунт: {name}\n"

    kb_list.append([InlineKeyboardButton(text="🗑 Очистить всю очередь", callback_data="flush_queue")])
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_list), parse_mode="Markdown")

@dp.callback_query(F.data == "flush_queue")
async def flush_user_queue(callback: types.CallbackQuery):
    uid = callback.from_user.id
    if uid in user_queue:
        for name in list(user_queue[uid].keys()):
            try:
                os.remove(os.path.join(config.SESSIONS_DIR, f"{name}.session"))
                os.remove(os.path.join(config.SESSIONS_DIR, f"{name}.json"))
            except Exception:
                pass
        user_queue[uid].clear()
    await callback.message.edit_text("🗑 Все загруженные файлы удалены, очередь очищена.")

@dp.message(F.text == "🚀 Запустить генерацию", check_permission)
async def process_generation(message: types.Message):
    uid = message.from_user.id
    if uid not in user_queue or not user_queue[uid]:
        await message.answer("Ошибка: нет доступных сессий для обработки.")
        return

    await message.answer("🔄 Запуск массового вывода дорвеев в глобальный поиск Telegram. Пожалуйста, ожидайте...")
    tasks_to_process = user_queue[uid].copy()
    user_queue[uid].clear()

    final_report = "📝 ОТЧЕТ ПО ЗАВЕРШЕНИЮ СЕО-ГЕНЕРАЦИИ:\n\n"
    
    # Порядковый номер аккаунта для распределения разных комбинаций юзернеймов
    acc_index = 0
    
    for name, prefix in tasks_to_process.items():
        spath = os.path.join(config.SESSIONS_DIR, f"{name}.session")
        jpath = os.path.join(config.SESSIONS_DIR, f"{name}.json")
        await message.answer(f"⏳ Вывожу в топ аккаунт {name}...")
        
        try:
            res = await tg_client.register_bot_and_app(
                session_path=spath,
                json_path=jpath,
                keyword=runtime_settings["doorway_target"],
                app_url=runtime_settings["url"],
                index_num=acc_index
            )
            if res["status"] == "success":
                final_report += f"✅ {name} ➔ @{res['username']}\nТокен: {res['token']}\n\n"
            else:
                final_report += f"❌ {name} ➔ Ошибка: {res['message']}\n\n"
        except Exception as e:
            final_report += f"❌ {name} ➔ Системный сбой: {str(e)}\n\n"
        
        acc_index += 1
        await asyncio.sleep(5)

    await message.answer(final_report, reply_markup=build_main_keyboard())

async def handle_webhook(request):
    try:
        data = await request.json()
        update = types.Update(**data)
        await dp.feed_update(bot, update)
    except Exception as e:
        print(f"[-] Ошибка обработки вебхука: {e}")
    return web.Response(text="OK")

async def on_startup(app):
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_url:
        webhook_url = f"{render_url}/webhook"
        await bot.set_webhook(webhook_url, drop_pending_updates=True)
        print(f"[+] Установлен вебхук на: {webhook_url}")

def main():
    app = web.Application()
    app.router.add_post('/webhook', handle_webhook)
    app.on_startup.append(on_startup)
    
    port = int(os.environ.get("PORT", 10000))
    print(f"[*] Старт сервера вебхуков на порту {port}")
    web.run_app(app, host='0.0.0.0', port=port, access_log=None)

if __name__ == "__main__":
    main()
