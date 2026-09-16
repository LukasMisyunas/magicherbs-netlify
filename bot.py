import asyncio
import json
import logging
import os
import hmac
import hashlib
import uuid
from urllib.parse import parse_qsl

from dotenv import load_dotenv
load_dotenv()

import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo,
    Message, CallbackQuery, FSInputFile
)
from aiogram.filters import Command
from aiogram import F
from pathlib import Path

# ===================== ПУТИ =====================
PHOTOS_DIR = Path(__file__).parent / "Photos"
PHOTOS_DIR.mkdir(exist_ok=True)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Файлы данных
TEXTS_FILE = DATA_DIR / "texts.json"
FAQ_FILE = DATA_DIR / "faq.json"
CONTACTS_FILE = DATA_DIR / "contacts.json"
PHOTOS_FILE = DATA_DIR / "photos.json"  # пути к фото разделов

# Стандартные имена фото (можно менять через админку)
DEFAULT_PHOTOS = {
    "main_menu": "main_menu.jpg",
    "faq": "faq.jpg",
    "delivery": "delivery.jpg",
    "about": "about.jpg",
    "contacts": "contacts.jpg",
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("bot")


# ===================== ФОТО =====================
PHOTOS = {}  # загружается ниже

def get_photo(filename: str):
    if not filename:
        return None
    try:
        path = PHOTOS_DIR / filename
        if path.exists():
            return FSInputFile(str(path))
    except Exception as e:
        log.error(f"Ошибка загрузки фото {filename}: {e}")
    return None


# ===================== ТЕКСТЫ =====================
DEFAULT_TEXTS = {
    "welcome": (
        "🌿 *Добро пожаловать в MagicHerbs!*\n\n"
        "🏔️ Натуральные нутрицевтики из Сибири\n"
        "✨ Создано природой — проверено наукой\n\n"
        "Выберите интересующий раздел 👇"
    ),
    "delivery": (
        "🚚 *Доставка и оплата*\n\n"
        "📦 *Способы доставки:*\n\n"
        "🚚 *Стандартная* — бесплатно\n"
        "Срок: 3–5 рабочих дней\n\n"
        "✈️ *Экспресс* — 500 ₽\n"
        "Срок: 1–2 рабочих дня\n\n"
        "🎁 *Бонус:* на заказы от 10 000 ₽ — скидка и бесплатная доставка\n\n"
        "💳 *Способы оплаты:*\n\n"
        "▸ 💳 OzonPay\n"
        "▸ 💳 CloudPayments — Visa, Mastercard, МИР\n"
        "▸ 💳 Robokassa — СБП, карты, кошельки\n"
        "▸ 💳 ЮKassa — карта, ЮMoney, SberPay"
    ),
    "about": (
        "🌲 *О бренде MagicHerbs*\n\n"
        "✨ *Наша история*\n"
        "MagicHerbs — семейный бренд, часть научно-производственного комплекса "
        "с более чем *20-летней историей* на рынке.\n\n"
        "🌿 *Наше сырьё*\n"
        "▸ Только дикорастущие травы и растения\n"
        "▸ Собираем в экологических заповедниках Сибири\n"
        "▸ От Горного Алтая до севера Томской области\n"
        "▸ Производство — прямо в месте произрастания сырья\n\n"
        "🎯 *Наша миссия*\n"
        "Сохранить человечество в здоровом, не видоизменённом виде:\n"
        "🌱 Натуральные концентраты из дикорастущего сырья\n"
        "❌ Вместо синтетических препаратов\n\n"
        "ℹ️ Подробнее — на mherbs.ru"
    ),
    "faq_intro": "❓ *Часто задаваемые вопросы*\n\nВыберите вопрос 👇",
    "contacts_intro": "📞 *Контакты*\n\nВыберите раздел 👇",
}

# ===================== FAQ =====================
DEFAULT_FAQ = {
    "q_natural": {
        "title": "🌿 Натуральный?",
        "answer": (
            "🌿 *Товар натуральный?*\n\n"
            "Да! Мы используем только дикорастущее сырьё Сибири и Алтая.\n\n"
            "✅ Никакого искусственно выращенного или китайского сырья\n"
            "✅ Только стеклянная тара, без пластика"
        ),
    },
    "q_unique": {
        "title": "✨ Уникальность?",
        "answer": (
            "✨ *В чём уникальность?*\n\n"
            "Уникальная вакуумная низкотемпературная технология экстракции:\n\n"
            "🔬 Сохраняет полезные вещества растений\n"
            "🚫 Без выпаривания в «кастрюлях»\n"
            "🚫 Без вредных реагентов и консервантов\n"
            "📊 Эффективность экстракции — до 99%"
        ),
    },
    "q_certs": {
        "title": "📜 Сертификаты?",
        "answer": (
            "📜 *Есть сертификаты?*\n\n"
            "Да, качество контролируется на всех этапах.\n\n"
            "🔍 Сертификаты — на сайте, раздел «Протоколы»."
        ),
    },
    "q_marketplaces": {
        "title": "🏪 Маркетплейсы?",
        "answer": (
            "🏪 *На маркетплейсах есть?*\n\n"
            "Нет! Мы принципиально не продаём продукцию:\n\n"
            "❌ На маркетплейсах\n"
            "❌ В массмаркетах\n\n"
            "💎 Только эксклюзивное качество и ограниченные объёмы"
        ),
    },
    "q_tracking": {
        "title": "📦 Отследить?",
        "answer": (
            "📦 *Как отследить заказ?*\n\n"
            "Трек-номер придёт на e-mail, указанный при оформлении."
        ),
    },
}

# ===================== КОНТАКТЫ =====================
DEFAULT_CONTACTS = {
    "c_phone": {
        "title": "📱 Телефон",
        "answer": (
            "📱 *Телефон и email*\n\n"
            "☎️ +7 900 922 4496\n"
            "✉️ magicherbs4you@yandex.ru"
        ),
    },
    "c_social": {
        "title": "🌐 Соцсети",
        "answer": (
            "🌐 *Социальные сети*\n\n"
            "▸ VK: vk.com/mherbs\n"
            "▸ Telegram: t.me/yegorogurtsov\n"
            "▸ WhatsApp: wa.me/79009224496"
        ),
    },
    "c_address": {
        "title": "📍 Адрес",
        "answer": (
            "📍 *Адрес*\n\n"
            "г. Томск\n\n"
            "💻 Сайт: mherbs.ru"
        ),
    },
}


# ===================== ЗАГРУЗКА / СОХРАНЕНИЕ =====================
def load_json(path, default):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.error(f"Ошибка загрузки {path.name}: {e}")
            return default.copy()
    else:
        save_json(path, default)
        return default.copy()


def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"Ошибка сохранения {path.name}: {e}")


TEXTS = load_json(TEXTS_FILE, DEFAULT_TEXTS)
FAQ = load_json(FAQ_FILE, DEFAULT_FAQ)
CONTACTS = load_json(CONTACTS_FILE, DEFAULT_CONTACTS)
PHOTOS = load_json(PHOTOS_FILE, DEFAULT_PHOTOS)


def get_text(key):
    return TEXTS.get(key, DEFAULT_TEXTS.get(key, ""))


def get_photo_name(key):
    return PHOTOS.get(key, DEFAULT_PHOTOS.get(key, ""))


# ===================== ENV =====================
BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
YOOKASSA_SHOP_ID = os.environ.get("YOOKASSA_SHOP_ID", "")
YOOKASSA_SECRET_KEY = os.environ.get("YOOKASSA_SECRET_KEY", "")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://magicherbsss.netlify.app/")
ORDER_SHARED_SECRET = os.environ["ORDER_SHARED_SECRET"]
PORT = int(os.environ.get("PORT", 8080))

bot = Bot(token=BOT_TOKEN, request_timeout=120)
dp = Dispatcher()
orders_db = {}
BOT_USERNAME = None

# Состояния
editing_state = {}       # {user_id: "welcome"/"delivery"/...}
adding_state = {}        # {user_id: {"type": "faq"/"contacts", "step": "title"/"answer"}}
editing_item = {}        # {user_id: {"type": "faq"/"contacts", "key": "q_natural", "field": "title"/"answer"}}
waiting_photo = {}       # {user_id: "faq"/"delivery"/...}
menu_message_ids = {}
info_message_ids = {}


# ===================== КЛАВИАТУРЫ =====================

def main_menu_keyboard(user_id: int = None):
    buttons = [
        [InlineKeyboardButton(text="🛒 Открыть каталог", web_app=WebAppInfo(url=WEBAPP_URL))],
        [
            InlineKeyboardButton(text="❓ FAQ", callback_data="open_faq"),
            InlineKeyboardButton(text="🚚 Доставка", callback_data="open_delivery"),
        ],
        [
            InlineKeyboardButton(text="🌲 О бренде", callback_data="open_about"),
            InlineKeyboardButton(text="📞 Контакты", callback_data="open_contacts"),
        ],
    ]
    if user_id == ADMIN_ID:
        buttons.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def questions_keyboard(items: dict, prefix: str, include_back: bool = False):
    """Компактные кнопки вопросов по 2 в ряд. + Закрыть (или Назад для FAQ)."""
    buttons = []
    row = []
    for key, item in items.items():
        row.append(InlineKeyboardButton(text=item["title"], callback_data=f"{prefix}{key}"))
        if len(row) >= 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    if include_back:
        # Первая кнопка после вопросов — Назад (удалить всё)
        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="close_info")])
    else:
        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="close_info")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def info_keyboard():
    """Просто кнопка Назад."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="close_info")]
        ]
    )


# ===================== ОТПРАВКА =====================

async def delete_info(user_id: int):
    old = info_message_ids.pop(user_id, None)
    if old:
        try:
            await bot.delete_message(user_id, old)
        except Exception:
            pass


async def send_main_menu(user_id: int):
    """Главное меню (фото + кнопки)."""
    text = get_text("welcome")
    photo_name = get_photo_name("main_menu")
    photo = get_photo(photo_name)
    keyboard = main_menu_keyboard(user_id)

    try:
        if photo:
            msg = await bot.send_photo(
                user_id,
                photo,
                caption=text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        else:
            msg = await bot.send_message(
                user_id,
                text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        menu_message_ids[user_id] = msg.message_id
        return msg.message_id
    except Exception as e:
        log.error(f"Ошибка главного меню: {e}")
        return None


async def send_info_with_photo(user_id: int, photo_key: str, text: str, keyboard):
    """Отправляет/обновляет инфо-сообщение с фото."""
    old = info_message_ids.get(user_id)
    if old:
        try:
            await bot.delete_message(user_id, old)
        except Exception:
            pass

    photo = get_photo(get_photo_name(photo_key))

    try:
        if photo:
            msg = await bot.send_photo(
                user_id,
                photo,
                caption=text[:1024],  # лимит caption
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            # Если текст длиннее 1024 — отдельным сообщением
            if len(text) > 1024:
                await bot.send_message(
                    user_id,
                    text,
                    parse_mode="Markdown"
                )
        else:
            msg = await bot.send_message(
                user_id,
                text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        info_message_ids[user_id] = msg.message_id
    except Exception as e:
        log.error(f"Ошибка инфо-сообщения: {e}")


async def edit_info_answer(user_id: int, text: str, keyboard):
    """Редактирует только текст инфо-сообщения (для FAQ/Контактов)."""
    old = info_message_ids.get(user_id)
    if not old:
        return

    try:
        await bot.edit_message_caption(
            chat_id=user_id,
            message_id=old,
            caption=text[:1024],
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception as e:
        log.warning(f"Не удалось edit_caption: {e}")
        try:
            await bot.edit_message_text(
                text=text[:4096],
                chat_id=user_id,
                message_id=old,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        except Exception as e2:
            log.error(f"Не удалось edit_text: {e2}")
            # Пересоздаём
            await send_info_with_photo(user_id, "faq", text, keyboard)


# ===================== /start =====================
@dp.message(Command("start"))
async def start_command(message: Message):
    user_id = message.from_user.id
    await delete_info(user_id)

    old_menu = menu_message_ids.pop(user_id, None)
    if old_menu:
        try:
            await bot.delete_message(user_id, old_menu)
        except Exception:
            pass

    await send_main_menu(user_id)


# ===================== FAQ =====================
@dp.callback_query(F.data == "open_faq")
async def open_faq(callback: CallbackQuery):
    await send_info_with_photo(
        callback.from_user.id,
        "faq",
        get_text("faq_intro"),
        questions_keyboard(FAQ, "faq_", include_back=True)
    )
    try:
        await callback.answer()
    except Exception:
        pass


@dp.callback_query(F.data.startswith("faq_q_"))
async def faq_answer(callback: CallbackQuery):
    key = callback.data.replace("faq_", "")
    item = FAQ.get(key)
    if not item:
        await callback.answer("Не найдено", show_alert=True)
        return
    await edit_info_answer(
        callback.from_user.id,
        item["answer"],
        questions_keyboard(FAQ, "faq_", include_back=True)
    )
    try:
        await callback.answer()
    except Exception:
        pass


# ===================== ДОСТАВКА =====================
@dp.callback_query(F.data == "open_delivery")
async def open_delivery(callback: CallbackQuery):
    await send_info_with_photo(
        callback.from_user.id,
        "delivery",
        get_text("delivery"),
        info_keyboard()
    )
    try:
        await callback.answer()
    except Exception:
        pass


# ===================== О БРЕНДЕ =====================
@dp.callback_query(F.data == "open_about")
async def open_about(callback: CallbackQuery):
    await send_info_with_photo(
        callback.from_user.id,
        "about",
        get_text("about"),
        info_keyboard()
    )
    try:
        await callback.answer()
    except Exception:
        pass


# ===================== КОНТАКТЫ =====================
@dp.callback_query(F.data == "open_contacts")
async def open_contacts(callback: CallbackQuery):
    await send_info_with_photo(
        callback.from_user.id,
        "contacts",
        get_text("contacts_intro"),
        questions_keyboard(CONTACTS, "ct_")
    )
    try:
        await callback.answer()
    except Exception:
        pass


@dp.callback_query(F.data.startswith("ct_c_"))
async def contacts_answer(callback: CallbackQuery):
    key = callback.data.replace("ct_", "")
    item = CONTACTS.get(key)
    if not item:
        await callback.answer("Не найдено", show_alert=True)
        return
    await edit_info_answer(
        callback.from_user.id,
        item["answer"],
        questions_keyboard(CONTACTS, "ct_")
    )
    try:
        await callback.answer()
    except Exception:
        pass


# ===================== ЗАКРЫТИЕ =====================
@dp.callback_query(F.data == "close_info")
async def close_info(callback: CallbackQuery):
    await delete_info(callback.from_user.id)
    try:
        await callback.answer()
    except Exception:
        pass


# ===================== ЗАКАЗЫ =====================
def esc_md(text: str) -> str:
    for ch in ("\\", "_", "*", "`", "["):
        text = text.replace(ch, "\\" + ch)
    return text


def verify_telegram_init_data(init_data: str, bot_token: str):
    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calculated_hash, received_hash):
            return None
        return parsed
    except Exception:
        return None


async def create_yookassa_payment(amount, order_id, user_id):
    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        return None
    url = "https://api.yookassa.ru/v3/payments"
    idempotence_key = str(uuid.uuid4())
    headers = {
        "Idempotence-Key": idempotence_key,
        "Content-Type": "application/json",
    }
    auth_header = aiohttp.BasicAuth(login=YOOKASSA_SHOP_ID, password=YOOKASSA_SECRET_KEY).encode()
    headers["Authorization"] = auth_header
    return_url = f"https://t.me/{BOT_USERNAME}" if BOT_USERNAME else "https://t.me/"
    payload = {
        "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
        "capture": True,
        "confirmation": {"type": "redirect", "return_url": return_url},
        "description": f"MagicHerbs — заказ #{order_id}",
        "metadata": {"order_id": order_id, "user_id": str(user_id)},
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                data = await resp.json()
                if resp.status in (200, 201):
                    return {
                        "confirmation_url": data["confirmation"]["confirmation_url"],
                        "payment_id": data["id"],
                    }
                log.warning("YooKassa create error: %s", data)
                return None
    except Exception:
        log.exception("YooKassa create exception")
        return None


@web.middleware
async def cors_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        resp = web.Response()
    else:
        resp = await handler(request)
    resp.headers["Access-Control-Allow-Origin"] = WEBAPP_URL.rstrip("/")
    resp.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Order-Secret"
    return resp


async def handle_order(request: web.Request):
    if request.headers.get("X-Order-Secret") != ORDER_SHARED_SECRET:
        return web.json_response({"ok": False, "error": "unauthorized"}, status=401)
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid json"}, status=400)
    init_data = body.get("init_data")
    verified = verify_telegram_init_data(init_data, BOT_TOKEN) if init_data else None
    if not verified:
        return web.json_response({"ok": False, "error": "invalid telegram init_data"}, status=401)
    user_data = json.loads(verified.get("user", "{}"))
    user_id = user_data.get("id")
    username = user_data.get("username", "")
    first_name = user_data.get("first_name", "")
    if not user_id:
        return web.json_response({"ok": False, "error": "no user id"}, status=400)
    order_id = body.get("order_id")
    amount = body.get("amount")
    customer = body.get("customer", {})
    items = body.get("items", [])
    if not order_id or not amount:
        return web.json_response({"ok": False, "error": "missing order_id/amount"}, status=400)
    orders_db[order_id] = {
        "user_id": user_id,
        "amount": amount,
        "status": "pending_payment",
        "customer": customer,
        "items": items,
        "delivery": body.get("delivery"),
        "payment": body.get("payment"),
    }
    if isinstance(items, list):
        items_lines = "\n".join(
            f"  • {esc_md(it.get('title', it.get('id', '?')))} — {it.get('qty', '?')} шт. × {it.get('price', '?')} ₽"
            for it in items
        )
    else:
        items_lines = esc_md(str(items))
    customer_lines = "\n".join(f"  {esc_md(str(k))}: {esc_md(str(v))}" for k, v in customer.items())
    payment_method = body.get("payment")
    if username:
        client_line = (
            f"👤 Клиент: {esc_md(first_name)}\n"
            f"🔗 Юзернейм: @{esc_md(username)}\n"
            f"🆔 ID: `{user_id}`\n"
        )
    else:
        client_line = (
            f"👤 Клиент: {esc_md(first_name)}\n"
            f"🔗 Юзернейм: нет\n"
            f"🆔 ID: `{user_id}`\n"
        )
    if payment_method == "yookassa":
        result = await create_yookassa_payment(amount, order_id, user_id)
        if result:
            orders_db[order_id]["yookassa_payment_id"] = result["payment_id"]
            try:
                await bot.send_message(
                    user_id,
                    f"💳 *Оплатите заказ*\n\n"
                    f"Сумма: *{amount} ₽*\n"
                    f"Номер заказа: `{order_id}`\n\n"
                    f"🔗 [Перейти к оплате]({result['confirmation_url']})",
                    parse_mode="Markdown",
                )
            except Exception:
                log.exception("Не удалось отправить клиенту")
            try:
                await bot.send_message(
                    ADMIN_ID,
                    f"🆕 *Новый заказ (ЮKassa)*\n\n"
                    f"Номер: `{order_id}`\n"
                    f"Сумма: *{amount} ₽*\n"
                    f"{client_line}\n"
                    f"Доставка: {esc_md(str(body.get('delivery', '—')))}\n\n"
                    f"*Контакты:*\n{customer_lines}\n\n"
                    f"*Товары:*\n{items_lines}",
                    parse_mode="Markdown",
                )
            except Exception:
                log.exception("Не удалось отправить админу")
            return web.json_response({"ok": True, "payment_url": result["confirmation_url"]})
    try:
        await bot.send_message(
            user_id,
            f"✅ *Заказ принят!*\n\n"
            f"Номер: `{order_id}`\n"
            f"Сумма: *{amount} ₽*\n\n"
            f"Менеджер свяжется с вами.",
            parse_mode="Markdown",
        )
    except Exception:
        log.exception("Не удалось отправить клиенту")
    try:
        await bot.send_message(
            ADMIN_ID,
            f"🆕 *Новый заказ*\n\n"
            f"Номер: `{order_id}`\n"
            f"Сумма: *{amount} ₽*\n"
            f"{client_line}\n"
            f"Доставка: {esc_md(str(body.get('delivery', '—')))}\n"
            f"Оплата: {esc_md(str(payment_method or '—'))}\n\n"
            f"*Контакты:*\n{customer_lines}\n\n"
            f"*Товары:*\n{items_lines}",
            parse_mode="Markdown",
        )
    except Exception:
        log.exception("Не удалось отправить админу")
    return web.json_response({"ok": True, "manual": True})


async def handle_yookassa_webhook(request: web.Request):
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False}, status=400)
    event = body.get("event")
    payment_obj = body.get("object", {})
    payment_id = payment_obj.get("id")
    metadata = payment_obj.get("metadata", {})
    order_id = metadata.get("order_id")
    log.info(f"ЮKassa webhook: event={event}, order_id={order_id}")
    if event == "payment.succeeded" and order_id:
        order = orders_db.get(order_id)
        if order:
            order["status"] = "paid"
            order["yookassa_payment_id"] = payment_id
            user_id = order.get("user_id")
            amount = order.get("amount")
            try:
                await bot.send_message(
                    user_id,
                    f"✅ *Оплата прошла!*\n\n"
                    f"Заказ `{order_id}` на *{amount} ₽* оплачен.",
                    parse_mode="Markdown",
                )
            except Exception:
                log.exception("Не удалось клиенту")
            try:
                await bot.send_message(
                    ADMIN_ID,
                    f"✅ *Оплата получена!*\n\n"
                    f"Заказ: `{order_id}`\n"
                    f"Сумма: *{amount} ₽*\n"
                    f"Клиент: ID `{user_id}`",
                    parse_mode="Markdown",
                )
            except Exception:
                log.exception("Не удалось админу")
    elif event == "payment.canceled" and order_id:
        order = orders_db.get(order_id)
        if order:
            order["status"] = "cancelled"
    return web.json_response({"ok": True})


# ===================== АДМИН-ПАНЕЛЬ =====================
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return
    await show_admin_panel(message.from_user.id)


async def show_admin_panel(user_id: int):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 Заказы", callback_data="admin_orders")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="📝 Тексты разделов", callback_data="admin_texts")],
            [InlineKeyboardButton(text="❓ Управление FAQ", callback_data="admin_faq")],
            [InlineKeyboardButton(text="📞 Управление Контактами", callback_data="admin_contacts")],
            [InlineKeyboardButton(text="🖼 Фото разделов", callback_data="admin_photos")],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin_close")],
        ]
    )
    await bot.send_message(
        user_id,
        "🔧 *Админ-панель MagicHerbs*\n\nВыберите раздел:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    # Очищаем состояния
    editing_state.pop(callback.from_user.id, None)
    adding_state.pop(callback.from_user.id, None)
    editing_item.pop(callback.from_user.id, None)
    waiting_photo.pop(callback.from_user.id, None)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 Заказы", callback_data="admin_orders")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="📝 Тексты разделов", callback_data="admin_texts")],
            [InlineKeyboardButton(text="❓ Управление FAQ", callback_data="admin_faq")],
            [InlineKeyboardButton(text="📞 Управление Контактами", callback_data="admin_contacts")],
            [InlineKeyboardButton(text="🖼 Фото разделов", callback_data="admin_photos")],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin_close")],
        ]
    )
    await callback.message.edit_text(
        "🔧 *Админ-панель MagicHerbs*\n\nВыберите раздел:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer()


# ---------- ЗАКАЗЫ ----------
@dp.callback_query(F.data == "admin_orders")
async def admin_orders(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    if not orders_db:
        await callback.message.edit_text(
            "📭 *Заказов пока нет.*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]]
            )
        )
        await callback.answer()
        return
    orders_list = list(orders_db.items())[-10:]
    orders_list.reverse()
    text = "📦 *Последние заказы:*\n\n"
    keyboard_buttons = []
    for order_id, order in orders_list:
        status_emoji = {"pending_payment": "⏳", "paid": "✅", "cancelled": "❌"}.get(order.get("status", ""), "❓")
        amount = order.get("amount", 0)
        short_id = order_id[-8:] if len(order_id) > 8 else order_id
        text += f"{status_emoji} `{short_id}` — {amount} ₽\n"
        keyboard_buttons.append([
            InlineKeyboardButton(text=f"{status_emoji} {short_id} ({amount}₽)", callback_data=f"admin_order_{order_id}")
        ])
    keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")])
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons))
    await callback.answer()


@dp.callback_query(F.data.startswith("admin_order_"))
async def admin_order_detail(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    order_id = callback.data.replace("admin_order_", "")
    order = orders_db.get(order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    customer = order.get("customer", {})
    items = order.get("items", [])
    status = order.get("status", "unknown")
    status_text = {"pending_payment": "⏳ Ожидает оплаты", "paid": "✅ Оплачен", "cancelled": "❌ Отменён"}.get(status, status)
    if isinstance(items, list):
        items_lines = "\n".join(
            f"  • {esc_md(it.get('title', it.get('id', '?')))} — {it.get('qty', '?')} шт. × {it.get('price', '?')} ₽"
            for it in items
        )
    else:
        items_lines = esc_md(str(items))
    customer_lines = "\n".join(f"  {esc_md(str(k))}: {esc_md(str(v))}" for k, v in customer.items())
    text = (
        f"📦 *Заказ* `{order_id}`\n\n"
        f"Статус: {status_text}\n"
        f"Сумма: *{order.get('amount', 0)} ₽*\n"
        f"Доставка: {esc_md(str(order.get('delivery', '—')))}\n"
        f"Оплата: {esc_md(str(order.get('payment', '—')))}\n\n"
        f"*Контакты:*\n{customer_lines}\n\n"
        f"*Товары:*\n{items_lines}"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отметить оплаченным", callback_data=f"admin_mark_paid_{order_id}")],
            [InlineKeyboardButton(text="❌ Отменить заказ", callback_data=f"admin_mark_cancel_{order_id}")],
            [InlineKeyboardButton(text="⬅️ К заказам", callback_data="admin_orders")],
        ]
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()


@dp.callback_query(F.data.startswith("admin_mark_paid_"))
async def admin_mark_paid(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    order_id = callback.data.replace("admin_mark_paid_", "")
    order = orders_db.get(order_id)
    if order:
        order["status"] = "paid"
    await callback.answer("Отмечено оплаченным")
    await callback.message.edit_text(
        f"✅ Заказ `{order_id}` отмечен как *оплаченный*.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ К заказам", callback_data="admin_orders")]]
        )
    )


@dp.callback_query(F.data.startswith("admin_mark_cancel_"))
async def admin_mark_cancel(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    order_id = callback.data.replace("admin_mark_cancel_", "")
    order = orders_db.get(order_id)
    if order:
        order["status"] = "cancelled"
    await callback.answer("Отменено")
    await callback.message.edit_text(
        f"❌ Заказ `{order_id}` отменён.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ К заказам", callback_data="admin_orders")]]
        )
    )


@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    total_orders = len(orders_db)
    paid_orders = sum(1 for o in orders_db.values() if o.get("status") == "paid")
    pending_orders = sum(1 for o in orders_db.values() if o.get("status") == "pending_payment")
    cancelled_orders = sum(1 for o in orders_db.values() if o.get("status") == "cancelled")
    total_revenue = sum(o.get("amount", 0) for o in orders_db.values() if o.get("status") == "paid")
    text = (
        f"📊 *Статистика MagicHerbs*\n\n"
        f"📦 Всего заказов: *{total_orders}*\n"
        f"✅ Оплачено: *{paid_orders}*\n"
        f"⏳ Ожидают: *{pending_orders}*\n"
        f"❌ Отменено: *{cancelled_orders}*\n\n"
        f"💰 Выручка: *{total_revenue} ₽*"
    )
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]]
        )
    )
    await callback.answer()


# ---------- ТЕКСТЫ РАЗДЕЛОВ ----------
@dp.callback_query(F.data == "admin_texts")
async def admin_texts(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌿 Приветствие", callback_data="admin_text_welcome")],
            [InlineKeyboardButton(text="🚚 Доставка", callback_data="admin_text_delivery")],
            [InlineKeyboardButton(text="🌲 О бренде", callback_data="admin_text_about")],
            [InlineKeyboardButton(text="❓ FAQ интро", callback_data="admin_text_faq_intro")],
            [InlineKeyboardButton(text="📞 Контакты интро", callback_data="admin_text_contacts_intro")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")],
        ]
    )
    await callback.message.edit_text(
        "📝 *Тексты разделов*\n\nВыберите, что редактировать:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("admin_text_"))
async def admin_text_choice(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    key = callback.data.replace("admin_text_", "")
    if key not in DEFAULT_TEXTS:
        await callback.answer("Раздел не найден", show_alert=True)
        return
    names = {
        "welcome": "Приветствие",
        "delivery": "Доставка",
        "about": "О бренде",
        "faq_intro": "FAQ (интро)",
        "contacts_intro": "Контакты (интро)",
    }
    editing_state[callback.from_user.id] = key
    current = get_text(key)
    preview = current[:500] + ("..." if len(current) > 500 else "")
    await callback.message.edit_text(
        f"✏️ *Редактирование: {names.get(key, key)}*\n\n"
        f"*Текущий текст:*\n{preview}\n\n"
        f"Отправьте новый текст одним сообщением.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")]]
        )
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_cancel")
async def admin_cancel(callback: CallbackQuery):
    editing_state.pop(callback.from_user.id, None)
    adding_state.pop(callback.from_user.id, None)
    editing_item.pop(callback.from_user.id, None)
    waiting_photo.pop(callback.from_user.id, None)
    await callback.answer("Отменено")
    await admin_back(callback)


# ---------- УПРАВЛЕНИЕ FAQ ----------
@dp.callback_query(F.data == "admin_faq")
async def admin_faq(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    text = "❓ *Управление FAQ*\n\nВсего вопросов: *" + str(len(FAQ)) + "*\n\nВыберите действие:"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить вопрос", callback_data="faq_add")],
            [InlineKeyboardButton(text="📋 Список вопросов", callback_data="faq_list")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")],
        ]
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()


@dp.callback_query(F.data == "faq_list")
async def faq_list(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    if not FAQ:
        await callback.answer("Пусто", show_alert=True)
        return
    buttons = []
    for key, item in FAQ.items():
        buttons.append([
            InlineKeyboardButton(text=item["title"][:40], callback_data=f"faq_edit_{key}")
        ])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_faq")])
    await callback.message.edit_text(
        "📋 *Список вопросов FAQ*\n\nВыберите для редактирования:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("faq_edit_"))
async def faq_edit(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    key = callback.data.replace("faq_edit_", "")
    item = FAQ.get(key)
    if not item:
        await callback.answer("Не найдено", show_alert=True)
        return
    text = (
        f"✏️ *Вопрос:* {item['title']}\n\n"
        f"*Ответ:*\n{item['answer'][:300]}...\n\n"
        f"Что редактируем?"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Название кнопки", callback_data=f"faq_edit_title_{key}")],
            [InlineKeyboardButton(text="📝 Ответ", callback_data=f"faq_edit_answer_{key}")],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"faq_delete_{key}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="faq_list")],
        ]
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()


@dp.callback_query(F.data.startswith("faq_edit_title_"))
async def faq_edit_title(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    key = callback.data.replace("faq_edit_title_", "")
    editing_item[callback.from_user.id] = {"type": "faq", "key": key, "field": "title"}
    await callback.message.edit_text(
        f"✏️ Отправьте *новое название кнопки* для вопроса «{FAQ[key]['title']}»:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")]]
        )
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("faq_edit_answer_"))
async def faq_edit_answer(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    key = callback.data.replace("faq_edit_answer_", "")
    editing_item[callback.from_user.id] = {"type": "faq", "key": key, "field": "answer"}
    await callback.message.edit_text(
        f"✏️ Отправьте *новый ответ* для вопроса «{FAQ[key]['title']}»:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")]]
        )
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("faq_delete_"))
async def faq_delete(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    key = callback.data.replace("faq_delete_", "")
    if key in FAQ:
        del FAQ[key]
        save_json(FAQ_FILE, FAQ)
        await callback.answer("Удалено", show_alert=True)
    await admin_faq(callback)


@dp.callback_query(F.data == "faq_add")
async def faq_add(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    adding_state[callback.from_user.id] = {"type": "faq", "step": "title"}
    await callback.message.edit_text(
        "➕ *Новый вопрос FAQ*\n\nШаг 1/2: Отправьте *название кнопки* (например, «🌿 Натуральный?»):",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")]]
        )
    )
    await callback.answer()


# ---------- УПРАВЛЕНИЕ КОНТАКТАМИ ----------
@dp.callback_query(F.data == "admin_contacts")
async def admin_contacts(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    text = "📞 *Управление Контактами*\n\nВсего пунктов: *" + str(len(CONTACTS)) + "*\n\nВыберите действие:"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить пункт", callback_data="ct_add")],
            [InlineKeyboardButton(text="📋 Список пунктов", callback_data="ct_list")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")],
        ]
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()


@dp.callback_query(F.data == "ct_list")
async def ct_list(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    if not CONTACTS:
        await callback.answer("Пусто", show_alert=True)
        return
    buttons = []
    for key, item in CONTACTS.items():
        buttons.append([
            InlineKeyboardButton(text=item["title"][:40], callback_data=f"ct_edit_{key}")
        ])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_contacts")])
    await callback.message.edit_text(
        "📋 *Список пунктов Контактов*\n\nВыберите для редактирования:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("ct_edit_"))
async def ct_edit(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    key = callback.data.replace("ct_edit_", "")
    item = CONTACTS.get(key)
    if not item:
        await callback.answer("Не найдено", show_alert=True)
        return
    text = (
        f"✏️ *Пункт:* {item['title']}\n\n"
        f"*Ответ:*\n{item['answer'][:300]}...\n\n"
        f"Что редактируем?"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Название кнопки", callback_data=f"ct_edit_title_{key}")],
            [InlineKeyboardButton(text="📝 Ответ", callback_data=f"ct_edit_answer_{key}")],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"ct_delete_{key}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="ct_list")],
        ]
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()


@dp.callback_query(F.data.startswith("ct_edit_title_"))
async def ct_edit_title(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    key = callback.data.replace("ct_edit_title_", "")
    editing_item[callback.from_user.id] = {"type": "contacts", "key": key, "field": "title"}
    await callback.message.edit_text(
        f"✏️ Отправьте *новое название кнопки*:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")]]
        )
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("ct_edit_answer_"))
async def ct_edit_answer(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    key = callback.data.replace("ct_edit_answer_", "")
    editing_item[callback.from_user.id] = {"type": "contacts", "key": key, "field": "answer"}
    await callback.message.edit_text(
        f"✏️ Отправьте *новый ответ*:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")]]
        )
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("ct_delete_"))
async def ct_delete(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    key = callback.data.replace("ct_delete_", "")
    if key in CONTACTS:
        del CONTACTS[key]
        save_json(CONTACTS_FILE, CONTACTS)
        await callback.answer("Удалено", show_alert=True)
    await admin_contacts(callback)


@dp.callback_query(F.data == "ct_add")
async def ct_add(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    adding_state[callback.from_user.id] = {"type": "contacts", "step": "title"}
    await callback.message.edit_text(
        "➕ *Новый пункт Контактов*\n\nШаг 1/2: Отправьте *название кнопки*:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")]]
        )
    )
    await callback.answer()


# ---------- ФОТО РАЗДЕЛОВ ----------
@dp.callback_query(F.data == "admin_photos")
async def admin_photos(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="photo_main_menu")],
            [InlineKeyboardButton(text="❓ FAQ", callback_data="photo_faq")],
            [InlineKeyboardButton(text="🚚 Доставка", callback_data="photo_delivery")],
            [InlineKeyboardButton(text="🌲 О бренде", callback_data="photo_about")],
            [InlineKeyboardButton(text="📞 Контакты", callback_data="photo_contacts")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")],
        ]
    )
    await callback.message.edit_text(
        "🖼 *Фото разделов*\n\nВыберите раздел, чтобы заменить фото.\n\n"
        "Отправьте новое фото одним сообщением.",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("photo_"))
async def photo_choice(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    key = callback.data.replace("photo_", "")
    if key not in DEFAULT_PHOTOS:
        await callback.answer("Раздел не найден", show_alert=True)
        return
    waiting_photo[callback.from_user.id] = key
    names = {
        "main_menu": "Главное меню",
        "faq": "FAQ",
        "delivery": "Доставка",
        "about": "О бренде",
        "contacts": "Контакты",
    }
    await callback.message.edit_text(
        f"🖼 Замена фото: *{names.get(key, key)}*\n\n"
        f"Отправьте новое фото одним сообщением.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")]]
        )
    )
    await callback.answer()


# ---------- ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ (АДМИН) ----------
@dp.message(F.text & ~F.text.startswith("/"))
async def handle_admin_text(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    user_id = message.from_user.id

    # 1. Редактирование текстов разделов
    if user_id in editing_state:
        key = editing_state.pop(user_id)
        TEXTS[key] = message.text
        save_json(TEXTS_FILE, TEXTS)
        names = {
            "welcome": "Приветствие",
            "delivery": "Доставка",
            "about": "О бренде",
            "faq_intro": "FAQ (интро)",
            "contacts_intro": "Контакты (интро)",
        }
        await message.answer(
            f"✅ *Текст «{names.get(key, key)}» обновлён!*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅️ В админ-панель", callback_data="admin_back")]]
            )
        )
        return

    # 2. Редактирование элемента FAQ/Контактов
    if user_id in editing_item:
        info = editing_item.pop(user_id)
        typ = info["type"]
        key = info["key"]
        field = info["field"]
        data = FAQ if typ == "faq" else CONTACTS
        if key in data:
            data[key][field] = message.text
            save_json(FAQ_FILE if typ == "faq" else CONTACTS_FILE, data)
            await message.answer(
                f"✅ *{'Вопрос' if typ == 'faq' else 'Пункт'} обновлён!*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="⬅️ В админ-панель", callback_data="admin_back")]]
                )
            )
        return

    # 3. Добавление нового элемента FAQ/Контактов
    if user_id in adding_state:
        state = adding_state[user_id]
        typ = state["type"]
        step = state["step"]

        if step == "title":
            state["title"] = message.text
            state["step"] = "answer"
            adding_state[user_id] = state
            await message.answer(
                "Шаг 2/2: Отправьте *ответ* на этот вопрос/пункт:",
                parse_mode="Markdown"
            )
            return

        if step == "answer":
            title = state["title"]
            answer = message.text
            # Генерируем ключ
            new_key = f"{'q' if typ == 'faq' else 'c'}_{int(asyncio.get_event_loop().time() * 1000)}"
            data = FAQ if typ == "faq" else CONTACTS
            data[new_key] = {"title": title, "answer": answer}
            save_json(FAQ_FILE if typ == "faq" else CONTACTS_FILE, data)
            adding_state.pop(user_id, None)
            await message.answer(
                f"✅ *{'Вопрос' if typ == 'faq' else 'Пункт'} добавлен!*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="⬅️ В админ-панель", callback_data="admin_back")]]
                )
            )
            return


# ---------- ОБРАБОТКА ФОТО (АДМИН) ----------
@dp.message(F.photo)
async def handle_admin_photo(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    user_id = message.from_user.id
    if user_id not in waiting_photo:
        return

    key = waiting_photo.pop(user_id)
    try:
        # Скачиваем фото
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        new_filename = f"{key}_{photo.file_id}.jpg"
        file_path = PHOTOS_DIR / new_filename
        await bot.download_file(file.file_path, destination=str(file_path))

        # Обновляем путь
        PHOTOS[key] = new_filename
        save_json(PHOTOS_FILE, PHOTOS)

        names = {
            "main_menu": "Главное меню",
            "faq": "FAQ",
            "delivery": "Доставка",
            "about": "О бренде",
            "contacts": "Контакты",
        }
        await message.answer(
            f"✅ *Фото «{names.get(key, key)}» обновлено!*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅️ В админ-панель", callback_data="admin_back")]]
            )
        )
    except Exception as e:
        log.exception(f"Ошибка загрузки фото: {e}")
        await message.answer(f"❌ Ошибка: {e}")


@dp.callback_query(F.data == "admin_close")
async def admin_close(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer()


# ===================== WEB СЕРВЕР =====================
async def start_web_server():
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_post("/webhook/order", handle_order)
    app.router.add_post("/webhook/yookassa", handle_yookassa_webhook)
    app.router.add_options("/webhook/order", lambda r: web.Response())
    app.router.add_options("/webhook/yookassa", lambda r: web.Response())
    app.router.add_get("/health", lambda r: web.json_response({"ok": True}))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    log.info(f"🌐 HTTP сервер запущен на порту {PORT}")


# ===================== MAIN =====================
async def main():
    global BOT_USERNAME
    try:
        me = await bot.get_me()
        BOT_USERNAME = me.username
        log.info(f"🤖 Бот: @{BOT_USERNAME}")
    except Exception as e:
        log.error(f"Не удалось получить информацию о боте: {e}")
        return
    if YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY:
        log.info("💳 ЮKassa настроена")
    else:
        log.warning("💳 ЮKassa НЕ настроена")
    await start_web_server()
    log.info("🚀 Бот запущен!")
    while True:
        try:
            await dp.start_polling(bot, skip_updates=True)
        except Exception as e:
            log.error(f"Ошибка polling: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            break
        except Exception as e:
            log.error(f"Критическая ошибка: {e}")
            import time
            time.sleep(10)