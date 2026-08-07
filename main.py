import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

import config
import tg_client

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

class BotSettings(StatesGroup):
    waiting_for_url = State()
    waiting_for_hash = State()
    waiting_for_prefix = State()

runtime_settings = {
    "url": "https://example.com",
    "hash_len": 3
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
        "Система автоматизации создания ботов готова к работе.\n\n"
        "Вы можете отправлять файлы .session и .json (по одному или группами).\n"
        "После загрузки перейдите в меню для распределения префиксов.",
        reply_markup=build_main_keyboard()
    )

@dp.message(F.text == "⚙️ Настройки софта", check_permission)
async def show_settings(message: types.Message):
    text = (
        f"⚙️ **Текущие параметры автоматизации:**\n\n"
        f"🌐 **Mini App Домен:** `{runtime_settings['url']}`\n"
        f"🔢 **Длина случайного хэша:** `{runtime_settings['hash_len']}` символов"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить домен", callback_data="change_url")],
        [InlineKeyboardButton(text="✏️ Изменить длину хэша", callback_data="change_hash")]
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

@dp.callback_query(F.data == "change_hash")
async def process_change_hash(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Укажите длину генерируемого хэша (целое число от 2 до 10):")
    await state.set_state(BotSettings.waiting_for_hash)
    await callback.answer()

@dp.message(BotSettings.waiting_for_hash, check_permission)
async def update_hash(message: types.Message, state: FSMContext):
    try:
        val = int(message.text.strip())
        if not (2 <= val <= 10):
            raise ValueError
    except ValueError:
        await message.answer("Ошибка: введите корректное число от 2 до 10.")
        return
    runtime_settings["hash_len"] = val
    await state.clear()
    await message.answer(f"✅ Длина хэша установлена на **{val}** символов.", parse_mode="Markdown", reply_markup=build_main_keyboard())

@dp.message(F.document, check_permission)
async def catch_documents(message: types.Message):
    uid = message.from_user.id
    doc = message.document
    filename = doc.file_name
    base, ext = os.path.splitext(filename)

    if ext not in ['.session', '.json']:
        return

    if uid not in user_queue:
        user_queue[uid] = {}

    target_path = os.path.join(config.SESSIONS_DIR, filename)
    file_info = await bot.get_file(doc.file_id)
    await bot.download_file(file_info.file_path, target_path)

    if ext == '.session' and base not in user_queue[uid]:
        user_queue[uid][base] = "qq"

    await message.answer(f"📥 Загружен и сохранен файл: `{filename}`", parse_mode="Markdown")

@dp.message(F.text == "📋 Моя очередь", check_permission)
async def show_queue(message: types.Message):
    uid = message.from_user.id
    if uid not in user_queue or not user_queue[uid]:
        await message.answer("Ваша очередь пуста. Отправьте файлы сессий.")
        return

    text = "📋 **Загруженные аккаунты и настройки масок:**\n\n"
    kb_list = []
    for name, prefix in user_queue[uid].items():
        text += f"▪️ Аккаунт: `{name}` ➔ Префикс: **{prefix}**\n"
        kb_list.append([InlineKeyboardButton(text=f"Префикс для {name}", callback_data=f"setpref_{name}")])

    kb_list.append([InlineKeyboardButton(text="🗑 Очистить всю очередь", callback_data="flush_queue")])
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_list), parse_mode="Markdown")

@dp.callback_query(F.data == "flush_queue")
async def flush_user_queue(callback: types.CallbackQuery):
    uid = callback.from_user.id
    if uid in user_queue:
        for name in user_queue[uid].keys():
            try:
                os.remove(os.path.join(config.SESSIONS_DIR, f"{name}.session"))
                os.remove(os.path.join(config.SESSIONS_DIR, f"{name}.json"))
            except Exception:
                pass
        user_queue[uid].clear()
    await callback.message.edit_text("🗑 Все загруженные файлы удалены, очередь очищена.")

@dp.callback_query(F.data.startswith("setpref_"))
async def init_prefix_change(callback: types.CallbackQuery, state: FSMContext):
    session_target = callback.data.split("setpref_")
    await state.set_state(BotSettings.waiting_for_prefix)
    await state.update_data(target_session=session_target)
    await callback.message.answer(f"Введите строку префикса для сессии `{session_target}` (буквы, цифры, `_`):")
    await callback.answer()

@dp.message(BotSettings.waiting_for_prefix, check_permission)
async def commit_prefix_change(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    user_data = await state.get_data()
    target = user_data.get("target_session")
    new_prefix = message.text.strip()

    if uid in user_queue and target in user_queue[uid]:
        user_queue[uid][target] = new_prefix
        await message.answer(f"✅ Префикс для `{target}` успешно изменен на **{new_prefix}**")
        
    await state.clear()
    await show_queue(message)

@dp.message(F.text == "🚀 Запустить генерацию", check_permission)
async def process_generation(message: types.Message):
    uid = message.from_user.id
    if uid not in user_queue or not user_queue[uid]:
        await message.answer("Ошибка: нет доступных сессий для обработки.")
        return

    await message.answer("🔄 Запуск процессов автоматизации через BotFather. Пожалуйста, ожидайте...")
    tasks_to_process = user_queue[uid].copy()
    user_queue[uid].clear()

    final_report = "📝 **ОТЧЕТ ПО ЗАВЕРШЕНИЮ РАБОТЫ:**\n\n"
    for name, prefix in tasks_to_process.items():
        spath = os.path.join(config.SESSIONS_DIR, f"{name}.session")
        jpath = os.path.join(config.SESSIONS_DIR, f"{name}.json")
        await message.answer(f"⏳ Начинаю обработку сессии `{name}` с префиксом `{prefix}`...")
        
        try:
            res = await tg_client.register_bot_and_app(
                session_path=spath,
                json_path=jpath,
                prefix=prefix,
                hash_len=runtime_settings["hash_len"],
                app_url=runtime_settings["url"]
            )
            if res["status"] == "success":
                final_report += f"✅ `{name}` ➔ @{res['username']}\nТокен: `{res['token']}`\n\n"
            else:
                final_report += f"❌ `{name}` ➔ Ошибка: {res['message']}\n\n"
        except Exception as e:
            final_report += f"❌ `{name}` ➔ Системный сбой: {str(e)}\n\n"
        await asyncio.sleep(5)

    await message.answer(final_report, parse_mode="Markdown", reply_markup=build_main_keyboard())

async def main():
    server = await asyncio.start_server(lambda r, w: None, '0.0.0.0', int(os.environ.get("PORT", 10000)))
    print("[+] Бот успешно запущен в облаке!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
