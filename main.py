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

class FlowState(StatesGroup):
    set_url = State()
    set_hash = State()
    set_prefix = State()
    set_global_prefix = State()
    set_seo_start = State()

runtime = {
    "url": "https://example.com",
    "hash_len": 3
}

user_queue = {}

def has_access(msg: types.Message) -> bool:
    return msg.from_user.id in config.ALLOWED_USERS

def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚙️ Настройки софта"), KeyboardButton(text="📋 Список Дорвеев")],
            [KeyboardButton(text="🧬 Перехват Поиска (SEO)")]
        ],
        resize_keyboard=True
    )

@dp.message(Command("start"), has_access)
async def init_session(message: types.Message, state: FSMContext):
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
        "👋 **Система автоматизации и СЕО-перехвата готова к работе!**\n\n"
        "Вы можете отправлять файлы `.session` и `.json` группами или в `.zip` архиве.\n"
        "После загрузки перейдите в меню списка дорвеев для управления масками.",
        reply_markup=main_kb(),
        parse_mode="Markdown"
    )
@dp.message(F.text == "⚙️ Настройки софта", has_access)
async def route_settings(message: types.Message):
    out = (
        f"⚙️ **Текущие параметры автоматизации:**\n\n"
        f"🌐 **Mini App Домен:** `{runtime['url']}`\n"
        f"🔢 **Длина случайного хэша:** `{runtime['hash_len']}` символов"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить домен", callback_data="mod_url")],
        [InlineKeyboardButton(text="✏️ Изменить длину хэша", callback_data="mod_hash")]
    ])
    await message.answer(out, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "mod_url")
async def req_url(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправьте новый целевой URL-домен для привязки к Mini App:")
    await state.set_state(FlowState.set_url)
    await callback.answer()

@dp.message(FlowState.set_url, has_access)
async def commit_url(message: types.Message, state: FSMContext):
    val = message.text.strip()
    if not val.startswith(("http://", "https://")):
        await message.answer("Ошибка: URL должен начинаться с http:// или https://. Попробуйте еще раз.")
        return
    runtime["url"] = val
    await state.clear()
    await message.answer(f"✅ Домен успешно изменен на: `{val}`", parse_mode="Markdown", reply_markup=main_kb())

@dp.callback_query(F.data == "mod_hash")
async def req_hash(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Укажите длину генерируемого хэша (целое число от 2 до 10):")
    await state.set_state(FlowState.set_hash)
    await callback.answer()

@dp.message(FlowState.set_hash, has_access)
async def commit_hash(message: types.Message, state: FSMContext):
    try:
        num = int(message.text.strip())
        if not (2 <= num <= 10):
            raise ValueError
    except ValueError:
        await message.answer("Ошибка: введите корректное число от 2 до 10.")
        return
    runtime["hash_len"] = num
    await state.clear()
    await message.answer(f"✅ Длина хэша установлена на **{num}** символов.", parse_mode="Markdown", reply_markup=main_kb())

@dp.message(F.document, has_access)
async def handle_docs(message: types.Message):
    uid = message.from_user.id
    doc = message.document
    filename = doc.file_name
    base, ext = os.path.splitext(filename)

    if uid not in user_queue:
        user_queue[uid] = {}

    f_path = os.path.join(config.SESSIONS_DIR, filename)
    obj = await bot.get_file(doc.file_id)
    await bot.download_file(obj.file_path, f_path)

    if ext == '.zip':
        try:
            with zipfile.ZipFile(f_path, 'r') as zr:
                for item in zr.namelist():
                    if item.endswith('/'):
                        continue
                    p_name = os.path.basename(item)
                    m_base, m_ext = os.path.splitext(p_name)
                    if m_ext in ['.session', '.json']:
                        ex_path = os.path.join(config.SESSIONS_DIR, p_name)
                        with open(ex_path, "wb") as f:
                            f.write(zr.read(item))
                        if m_ext == '.session' and m_base not in user_queue[uid]:
                            user_queue[uid][m_base] = "qq"
            os.remove(f_path)
            await message.answer("📦 Архив успешно распакован! Все сессии добавлены в список дорвеев.", parse_mode="Markdown")
            return
        except Exception as e:
            await message.answer(f"❌ Ошибка при распаковке архива: {str(e)}")
            if os.path.exists(f_path): os.remove(f_path)
            return

    if ext not in ['.session', '.json']:
        if os.path.exists(f_path): os.remove(f_path)
        return

    if ext == '.session' and base not in user_queue[uid]:
        user_queue[uid].setdefault(base, "qq")

    await message.answer(f"📥 Загружен и сохранен файл: `{filename}`", parse_mode="Markdown")
@dp.message(F.text == "📋 Список Дорвеев", has_access)
async def list_doorways(message: types.Message):
    uid = message.from_user.id
    if uid not in user_queue or not user_queue[uid]:
        await message.answer("Ваш список дорвеев пуст. Отправьте файлы сессий или .zip архив.")
        return

    out = "📋 **Загруженные аккаунты и настройки масок:**\n\n"
    kb = []
    kb.append([InlineKeyboardButton(text="✏️ Задать общий префикс для ВСЕХ", callback_data="bulk_prefix")])
    
    for name, prefix in list(user_queue[uid].items()):
        out += f"▪️ Аккаунт: {name} ➔ Настройка: {prefix}\n"
        clean = name.replace("+", "")
        kb.append([InlineKeyboardButton(text=f"Префикс для {name}", callback_data=f"setname_{clean}")])

    kb.append([InlineKeyboardButton(text="🚀 Запустить генерацию по маскам", callback_data="run_gen")])
    kb.append([InlineKeyboardButton(text="🗑 Очистить весь список", callback_data="clear_queue")])
    
    await message.answer(out, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@dp.callback_query(F.data == "bulk_prefix")
async def req_bulk_prefix(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите общий префикс, который применится к каждому аккаунту:")
    await state.set_state(FlowState.set_global_prefix)
    await callback.answer()

@dp.message(FlowState.set_global_prefix, has_access)
async def commit_bulk_prefix(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    val = message.text.strip()
    if uid in user_queue and user_queue[uid]:
        for k in user_queue[uid].keys():
            user_queue[uid][k] = val
        await message.answer("✅ Общий префикс успешно применен!")
    await state.clear()
    await list_doorways(message)

@dp.callback_query(F.data == "clear_queue")
async def drop_queue(callback: types.CallbackQuery):
    uid = callback.from_user.id
    if uid in user_queue:
        for k in list(user_queue[uid].keys()):
            try:
                os.remove(os.path.join(config.SESSIONS_DIR, f"{k}.session"))
                os.remove(os.path.join(config.SESSIONS_DIR, f"{k}.json"))
            except Exception: pass
        user_queue[uid].clear()
    await callback.message.edit_text("🗑 Все загруженные файлы удалены, список очищен.")

@dp.callback_query(F.data.startswith("setname_"))
async def req_single_prefix(callback: types.CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    phone = callback.data.split("setname_")
    target = None
    if uid in user_queue:
        for k in user_queue[uid].keys():
            if k.replace("+", "") == phone:
                target = k
                break
    if not target:
        target = f"+{phone}" if not phone.startswith("+") else phone
        if uid not in user_queue: user_queue[uid] = {}
        user_queue[uid][target] = "qq"
    await state.set_state(FlowState.set_prefix)
    await state.update_data(target_session=target)
    await callback.message.answer(f"Введите префикс для сессии {target}:")
    await callback.answer()

@dp.message(FlowState.set_prefix, has_access)
async def commit_single_prefix(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    ctx = await state.get_data()
    target = ctx.get("target_session")
    val = message.text.strip()
    if uid not in user_queue: user_queue[uid] = {}
    user_queue[uid][target] = val
    await message.answer(f"✅ Префикс для {target} изменен на {val}")
    await state.clear()
    await list_doorways(message)

@dp.callback_query(F.data == "run_gen")
async def handle_gen(callback: types.CallbackQuery):
    uid = callback.from_user.id
    if uid not in user_queue or not user_queue[uid]:
        await callback.message.answer("Ошибка: список пуст. Сначала отправьте архив.")
        await callback.answer()
        return

    await callback.message.answer("🔄 Запуск генерации ботов по маскам...")
    job_stack = user_queue[uid].copy()
    await callback.answer()

    report = "📝 ОТЧЕТ ПО ЗАВЕРШЕНИЮ РАБОТЫ:\n\n"
    for name, prefix in job_stack.items():
        spath = os.path.join(config.SESSIONS_DIR, f"{name}.session")
        jpath = os.path.join(config.SESSIONS_DIR, f"{name}.json")
        await callback.message.answer(f"⏳ Обрабатываю сессию {name} с маской {prefix}...")
        
        try:
            res = await tg_client.register_bot_and_app(spath, jpath, prefix, runtime["hash_len"], runtime["url"])
            if res["status"] == "success":
                report += f"✅ {name} ➔ @{res['username']}\nТокен: {res['token']}\n\n"
            else:
                report += f"❌ {name} ➔ Ошибка: {res['message']}\n\n"
        except Exception as e:
            report += f"❌ {name} ➔ Системный сбой: {str(e)}\n\n"
        await asyncio.sleep(4)

    user_queue[uid].clear()
    await callback.message.answer(report, reply_markup=main_kb())

@dp.message(F.text == "🧬 Перехват Поиска (SEO)", has_access)
async def req_seo(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    if uid not in user_queue or not user_queue[uid]:
        await message.answer("Ошибка: сначала отправьте `.zip` архив с сессиями!")
        return
    await message.answer("🔗 **Режим СЕО-перехвата глобального поиска**\n\nОтправьте ключевое слово (основу бренда) без знака @ (например: `saversmode`):")
    await state.set_state(FlowState.set_seo_start)

@dp.message(FlowState.set_seo_start, has_access)
async def commit_seo(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    kw = message.text.strip().replace("@", "").lower()
    await state.clear()
    
    patterns = ["bot", "_bot", "robot", "rbot", "_robot", "tbot", "_tbot", "official_bot", "_official_bot"]
    job_stack = user_queue[uid].copy()
    
    await message.answer(f"🔄 Запуск СЕО-вывода в поиск для основы '{kw}'...")
    report = "📝 ОТЧЕТ ПО ЗАВЕРШЕНИЮ СЕО-ГЕНЕРАЦИИ:\n\n"
    
    for idx, name in enumerate(list(job_stack.keys())):
        spath = os.path.join(config.SESSIONS_DIR, f"{name}.session")
        jpath = os.path.join(config.SESSIONS_DIR, f"{name}.json")
        await message.answer(f"⏳ Создаю поисковый дорвей для сессии {name}...")
        
        loop = idx // len(patterns)
        sfx = patterns[idx % len(patterns)]
        mask = f"SEO:{kw}{sfx}" if loop == 0 else f"SEO:{kw}{loop}{sfx}"
        
        try:
            res = await tg_client.register_bot_and_app(spath, jpath, mask, runtime["hash_len"], runtime["url"])
            if res["status"] == "success":
                report += f"✅ {name} ➔ @{res['username']}\nТокен: {res['token']}\n\n"
            else:
                report += f"❌ {name} ➔ Ошибка: {res['message']}\n\n"
        except Exception as e:
            report += f"❌ {name} ➔ Системный сбой: {str(e)}\n\n"
        await asyncio.sleep(5)

    user_queue[uid].clear()
    await message.answer(report, reply_markup=main_kb())

async def webhook_handler(request):
    try:
        body = await request.json()
        await dp.feed_update(bot, types.Update(**body))
    except Exception as e: print(f"[!] Webhook error: {e}")
    return web.Response(text="OK")

async def boot(app):
    host_url = os.environ.get("RENDER_EXTERNAL_URL")
    if host_url: await bot.set_webhook(f"{host_url}/webhook", drop_pending_updates=True)

def main():
    app = web.Application()
    app.router.add_post('/webhook', webhook_handler)
    app.on_startup.append(boot)
    web.run_app(app, host='0.0.0.0', port=int(os.environ.get("PORT", 10000)), access_log=None)

if __name__ == "__main__": main()
