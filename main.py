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
            [KeyboardButton(text="⚙️ Настройки софта"), KeyboardButton(text="📋 Список Дорвеев")]
        ],
        resize_keyboard=True
    )

@dp.message(Command("start"), check_permission)
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    if uid not in user_queue:
        user_queue[uid] = {}
        
    msg = await message.answer("🛸 *Инициализация системы...* [ ░/░░░░░░░░░ ]", parse_mode="Markdown")
    await asyncio.sleep(0.4)
    await msg.edit_text("🛸 *Синхронизация с серверами...* [ ███░░░░░░ ]", parse_mode="Markdown")
    await asyncio.sleep(0.4)
    await msg.edit_text("🛸 *Авторизация разработчика @xhevn...* [ ██████░░░ ]", parse_mode="Markdown")
    await asyncio.sleep(0.4)
    await msg.edit_text("⚡ *Доступ открыт! Добро пожаловать, @xhevn!* [ █████████ ]", parse_mode="Markdown")
    await asyncio.sleep(0.5)
    await msg.delete()
    
    await message.answer(
        "👋 **Система автоматизации создания ботов готова к работе!**\n\n"
        "Вы можете отправлять файлы `.session` и `.json` группами или в `.zip` архиве.\n"
        "После загрузки перейдите в меню списка дорвеев для управления масками.",
        reply_markup=build_main_keyboard(),
        parse_mode="Markdown"
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
            await message.answer("📦 Архив успешно распакован! Все сессии добавлены в список дорвеев.", parse_mode="Markdown")
            return
        except Exception as e:
            await message.answer(f"❌ Ошибка при распаковке архива: {str(e)}")
            if os.path.exists(target_path): os.remove(target_path)
            return

    if ext not in ['.session', '.json']:
        if os.path.exists(target_path): os.remove(target_path)
        return

    if ext == '.session' and base not in user_queue[uid]:
        user_queue[uid].setdefault(base, "qq")

    await message.answer(f"📥 Загружен и сохранен файл: `{filename}`", parse_mode="Markdown")
@dp.message(F.text == "📋 Список Дорвеев", check_permission)
async def show_queue(message: types.Message):
    uid = message.from_user.id
    if uid not in user_queue or not user_queue[uid]:
        await message.answer("Ваш список дорвеев пуст. Отправьте файлы сессий или .zip архив.")
        return

    text = "📋 **Загруженные аккаунты и настройки масок:**\n\n"
    kb_list = []
    kb_list.append([InlineKeyboardButton(text="✏️ Задать общий префикс для ВСЕХ", callback_data="set_global_prefix")])
    
    current_items = list(user_queue[uid].items())
    for name, prefix in current_items:
        text += f"▪️ Аккаунт: {name} ➔ Настройка: {prefix}\n"
        clean_name = name.replace("+", "")
        kb_list.append([InlineKeyboardButton(text=f"Префикс для {name}", callback_data=f"setname_{clean_name}")])

    kb_list.append([InlineKeyboardButton(text="🚀 Запустить генерацию по маскам", callback_data="start_normal_gen")])
    kb_list.append([InlineKeyboardButton(text="🗑 Очистить весь список", callback_data="flush_queue")])
    
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_list), parse_mode="Markdown")

@dp.callback_query(F.data == "set_global_prefix")
async def init_global_prefix(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите общий префикс, который применится к каждому аккаунту:")
    await state.set_state(BotSettings.waiting_for_global_prefix)
    await callback.answer()

@dp.message(BotSettings.waiting_for_global_prefix, check_permission)
async def commit_global_prefix(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    new_prefix = message.text.strip()
    if uid in user_queue and user_queue[uid]:
        for name in user_queue[uid].keys():
            user_queue[uid][name] = new_prefix
        await message.answer("✅ Общий префикс успешно применен!")
    await state.clear()
    await show_queue(message)

@dp.callback_query(F.data == "flush_queue")
async def flush_user_queue(callback: types.CallbackQuery):
    uid = callback.from_user.id
    if uid in user_queue:
        for name in list(user_queue[uid].keys()):
            try:
                os.remove(os.path.join(config.SESSIONS_DIR, f"{name}.session"))
                os.remove(os.path.join(config.SESSIONS_DIR, f"{name}.json"))
            except Exception: pass
        user_queue[uid].clear()
    await callback.message.edit_text("🗑 Все загруженные файлы удалены, список очищен.")

@dp.callback_query(F.data.startswith("setname_"))
async def init_prefix_change(callback: types.CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    target_phone = callback.data.split("setname_")
    session_target = None
    if uid in user_queue:
        for k in user_queue[uid].keys():
            if k.replace("+", "") == target_phone:
                session_target = k
                break
    if not session_target:
        session_target = f"+{target_phone}" if not target_phone.startswith("+") else target_phone
        if uid not in user_queue: user_queue[uid] = {}
        user_queue[uid][session_target] = "qq"
    await state.set_state(BotSettings.waiting_for_prefix)
    await state.update_data(target_session=session_target)
    await callback.message.answer(f"Введите префикс для сессии {session_target}:")
    await callback.answer()

@dp.message(BotSettings.waiting_for_prefix, check_permission)
async def commit_prefix_change(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    user_data = await state.get_data()
    target = user_data.get("target_session")
    new_prefix = message.text.strip()
    if uid not in user_queue: user_queue[uid] = {}
    user_queue[uid][target] = new_prefix
    await message.answer(f"✅ Префикс для {target} изменен на {new_prefix}")
    await state.clear()
    await show_queue(message)

@dp.callback_query(F.data == "start_normal_gen")
async def process_normal_generation(callback: types.CallbackQuery):
    uid = callback.from_user.id
    if uid not in user_queue or not user_queue[uid]:
        await callback.message.answer("Ошибка: список пуст. Сначала отправьте архив.")
        await callback.answer()
        return

    await callback.message.answer("🔄 Запуск генерации ботов по маскам...")
    tasks_to_process = user_queue[uid].copy()
    await callback.answer()

    final_report = "📝 ОТЧЕТ ПО ЗАВЕРШЕНИЮ РАБОТЫ:\n\n"
    for name, prefix in tasks_to_process.items():
        spath = os.path.join(config.SESSIONS_DIR, f"{name}.session")
        jpath = os.path.join(config.SESSIONS_DIR, f"{name}.json")
        await callback.message.answer(f"⏳ Обрабатываю сессию {name} с маской {prefix}...")
        
        try:
            res = await tg_client.register_bot_and_app(
                session_path=spath,
                json_path=jpath,
                prefix=prefix,
                hash_len=runtime_settings["hash_len"],
                app_url=runtime_settings["url"]
            )
            if res["status"] == "success":
                final_report += f"✅ {name} ➔ @{res['username']}\nТокен: {res['token']}\n\n"
            else:
                final_report += f"❌ {name} ➔ Ошибка: {res['message']}\n\n"
        except Exception as e:
            final_report += f"❌ {name} ➔ Системный сбой: {str(e)}\n\n"
        await asyncio.sleep(5)

    user_queue[uid].clear()
    await callback.message.answer(final_report, reply_markup=build_main_keyboard())

async def handle_webhook(request):
    try:
        data = await request.json()
        await dp.feed_update(bot, types.Update(**data))
    except Exception as e: print(f"[-] Ошибка вебхука: {e}")
    return web.Response(text="OK")

async def on_startup(app):
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_url: await bot.set_webhook(f"{render_url}/webhook", drop_pending_updates=True)

def main():
    app = web.Application()
    app.router.add_post('/webhook', handle_webhook)
    app.on_startup.append(on_startup)
    web.run_app(app, host='0.0.0.0', port=int(os.environ.get("PORT", 10000)), access_log=None)

if __name__ == "__main__": main()
