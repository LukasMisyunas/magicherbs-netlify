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
PHOTO_MAIN_MENU = "main_menu.jpg"
PHOTO_FAQ = "faq.jpg"
PHOTO_DELIVERY = "delivery.jpg"
PHOTO_ABOUT = "about.jpg"
PHOTO_CONTACTS = "contacts.jpg"

TEXTS_FILE = Path(__file__).parent / "texts.json"
FAQ_FILE = Path(__file__).parent / "faq.json"
DELIVERY_FILE = Path(__file__).parent / "delivery.json"
ABOUT_FILE = Path(__file__).parent / "about.json"
CONTACTS_FILE = Path(__file__).parent / "contacts.json"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("bot")


def get_photo(filename: str):
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

# ===================== ДОСТАВКА =====================
DEFAULT_DELIVERY = {
    "d_shipping": {
        "title": "📦 Доставка",
        "answer": (
            "📦 *Способы доставки*\n\n"
            "🚚 *Стандартная* — бесплатно\n"
            "Срок: 3–5 рабочих дней\n\n"
            "✈️ *Экспресс* — 500 ₽\n"
            "Срок: 1–2 рабочих дня\n\n"
            "🎁 *Бонус:* от 10 000 ₽ — скидка и бесплатная доставка"
        ),
    },
    "d_payment": {
        "title": "💳 Оплата",
        "answer": (
            "💳 *Способы оплаты*\n\n"
            "▸ 💳 OzonPay\n"
            "▸ 💳 CloudPayments — Visa, Mastercard, МИР\n"
            "▸ 💳 Robokassa — СБП, карты, кошельки\n"
            "▸ 💳 ЮKassa — карта, ЮMoney, SberPay"
        ),
    },
}

# ===================== О БРЕНДЕ =====================
DEFAULT_ABOUT = {
    "a_history": {
        "title": "✨ История",
        "answer": (
            "✨ *Наша история*\n\n"
            "MagicHerbs — семейный бренд, часть научно-производственного комплекса "
            "с более чем *20-летней историей* на рынке."
        ),
    },
    "a_raw": {
        "title": "🌿 Сырьё",
        "answer": (
            "🌿 *Наше сырьё*\n\n"
            "▸ Только дикорастущие травы и растения\n"
            "▸ Собираем в экологических заповедниках Сибири\n"
            "▸ От Горного Алтая до севера Томской области\n"
            "▸ Производство — прямо в месте произрастания сырья"
        ),
    },
    "a_mission": {
        "title": "🎯 Миссия",
        "answer": (
            "🎯 *Наша миссия*\n\n"
            "Сохранить человечество в здоровом, не видоизменённом виде:\n\n"
            "🌱 Натуральные концентраты из дикорастущего сырья\n"
            "❌ Вместо синтетических препаратов"
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


# ===================== ЗАГРУЗКА =====================
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
DELIVERY = load_json(DELIVERY_FILE, DEFAULT_DELIVERY)
ABOUT = load_json(ABOUT_FILE, DEFAULT_ABOUT)
CONTACTS = load_json(CONTACTS_FILE, DEFAULT_CONTACTS)


def get_text(key):
    return TEXTS.get(key, DEFAULT_TEXTS.get(key, ""))


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

editing_state = {}

# ID сообщений (для каждого пользователя)
menu_message_ids = {}    # главное меню
info_message_ids = {}    # инфо-сообщение (FAQ/Доставка/итд)


# ===================== КЛАВИАТУРЫ =====================

def main_menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
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
    )


def compact_questions_keyboard(items: dict, prefix: str):
    """Строит клавиатуру с вопросами. По 2-3 в ряд."""
    buttons = []
    row = []
    for key, item in items.items():
        row.append(InlineKeyboardButton(text=item["title"], callback_data=f"{prefix}{key}"))
        if len(row) >= 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    # Кнопка "Назад" — удаляет инфо-сообщение
    buttons.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="close_info")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ===================== ОТПРАВКА =====================

async def delete_info(user_id: int):
    """Удаляет инфо-сообщение, если оно есть."""
    old = info_message_ids.pop(user_id, None)
    if old:
        try:
            await bot.delete_message(user_id, old)
        except Exception:
            pass


async def send_main_menu(message_or_callback, user_id: int, edit: bool = False):
    """Отправляет главное меню. Сохраняет ID."""
    text = get_text("welcome")
    photo = get_photo(PHOTO_MAIN_MENU)

    try:
        if edit and isinstance(message_or_callback, CallbackQuery):
            # Редактировать текущее сообщение
            if photo:
                await message_or_callback.message.edit_caption(
                    caption=text,
                    parse_mode="Markdown",
                    reply_markup=main_menu_keyboard()
                )
            else:
                await message_or_callback.message.edit_text(
                    text,
                    parse_mode="Markdown",
                    reply_markup=main_menu_keyboard()
                )
            return message_or_callback.message.message_id
    except Exception as e:
        log.warning(f"Не удалось отредактировать главное меню: {e}")

    # Отправить новое
    try:
        if photo:
            msg = await bot.send_photo(
                user_id,
                photo,
                caption=text,
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        else:
            msg = await bot.send_message(
                user_id,
                text,
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        menu_message_ids[user_id] = msg.message_id
        return msg.message_id
    except Exception as e:
        log.error(f"Ошибка отправки главного меню: {e}")
        return None


async def send_info(user_id: int, text: str, keyboard):
    """Отправляет или обновляет инфо-сообщение ПОД главным меню."""
    old = info_message_ids.get(user_id)
    if old:
        try:
            await bot.edit_message_text(
                text,
                chat_id=user_id,
                message_id=old,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            return
        except Exception as e:
            log.warning(f"Не удалось обновить инфо: {e}")
            try:
                await bot.delete_message(user_id, old)
            except Exception:
                pass

    try:
        msg = await bot.send_message(
            user_id,
            text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        info_message_ids[user_id] = msg.message_id
    except Exception as e:
        log.error(f"Ошибка отправки инфо: {e}")


# ===================== /start =====================
@dp.message(Command("start"))
async def start_command(message: Message):
    user_id = message.from_user.id
    # Удаляем старое инфо
    await delete_info(user_id)
    # Удаляем старое меню (если было) — на случай перезапуска
    old_menu = menu_message_ids.pop(user_id, None)
    if old_menu:
        try:
            await bot.delete_message(user_id, old_menu)
        except Exception:
            pass
    # Отправляем главное меню
    await send_main_menu(message, user_id)


# ===================== ОТКРЫТИЕ РАЗДЕЛОВ =====================
# Все вызывают send_info — инфо-сообщение меняется под главным меню

@dp.callback_query(F.data == "open_faq")
async def open_faq(callback: CallbackQuery):
    await send_info(
        callback.from_user.id,
        "❓ *Часто задаваемые вопросы*\n\nВыберите вопрос 👇",
        compact_questions_keyboard(FAQ, "faq_")
    )
    try:
        await callback.answer()
    except Exception:
        pass


@dp.callback_query(F.data == "open_delivery")
async def open_delivery(callback: CallbackQuery):
    await send_info(
        callback.from_user.id,
        "🚚 *Доставка и оплата*\n\nВыберите раздел 👇",
        compact_questions_keyboard(DELIVERY, "del_")
    )
    try:
        await callback.answer()
    except Exception:
        pass


@dp.callback_query(F.data == "open_about")
async def open_about(callback: CallbackQuery):
    await send_info(
        callback.from_user.id,
        "🌲 *О бренде MagicHerbs*\n\nВыберите раздел 👇",
        compact_questions_keyboard(ABOUT, "ab_")
    )
    try:
        await callback.answer()
    except Exception:
        pass


@dp.callback_query(F.data == "open_contacts")
async def open_contacts(callback: CallbackQuery):
    await send_info(
        callback.from_user.id,
        "📞 *Контакты*\n\nВыберите раздел 👇",
        compact_questions_keyboard(CONTACTS, "ct_")
    )
    try:
        await callback.answer()
    except Exception:
        pass


# ===================== ОТВЕТЫ =====================
# При клике на вопрос — инфо-сообщение заменяется на ответ
# Клавиатура — те же вопросы + "Назад"

@dp.callback_query(F.data.startswith("faq_q_"))
async def faq_answer(callback: CallbackQuery):
    key = callback.data.replace("faq_", "")
    item = FAQ.get(key)
    if not item:
        await callback.answer("Не найдено", show_alert=True)
        return
    await send_info(
        callback.from_user.id,
        item["answer"],
        compact_questions_keyboard(FAQ, "faq_")
    )
    try:
        await callback.answer()
    except Exception:
        pass


@dp.callback_query(F.data.startswith("del_d_"))
async def delivery_answer(callback: CallbackQuery):
    key = callback.data.replace("del_", "")
    item = DELIVERY.get(key)
    if not item:
        await callback.answer("Не найдено", show_alert=True)
        return
    await send_info(
        callback.from_user.id,
        item["answer"],
        compact_questions_keyboard(DELIVERY, "del_")
    )
    try:
        await callback.answer()
    except Exception:
        pass


@dp.callback_query(F.data.startswith("ab_a_"))
async def about_answer(callback: CallbackQuery):
    key = callback.data.replace("ab_", "")
    item = ABOUT.get(key)
    if not item:
        await callback.answer("Не найдено", show_alert=True)
        return
    await send_info(
        callback.from_user.id,
        item["answer"],
        compact_questions_keyboard(ABOUT, "ab_")
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
    await send_info(
        callback.from_user.id,
        item["answer"],
        compact_questions_keyboard(CONTACTS, "ct_")
    )
    try:
        await callback.answer()
    except Exception:
        pass


# ===================== ЗАКРЫТИЕ ИНФО =====================
@dp.callback_query(F.data == "close_info")
async def close_info(callback: CallbackQuery):
    """Удаляет инфо-сообщение. Главное меню остаётся."""
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
            f"Менеджер свяжется с вами для уточнения деталей.",
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
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 Заказы", callback_data="admin_orders")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="✏️ Редактировать тексты", callback_data="admin_edit_texts")],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin_close")],
        ]
    )
    await message.answer(
        "🔧 *Админ-панель MagicHerbs*\n\nВыберите раздел:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "admin_orders")
async def admin_orders(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
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
        status_emoji = {
            "pending_payment": "⏳",
            "paid": "✅",
            "cancelled": "❌"
        }.get(order.get("status", ""), "❓")
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
        await callback.answer("Нет доступа", show_alert=True)
        return
    order_id = callback.data.replace("admin_order_", "")
    order = orders_db.get(order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    customer = order.get("customer", {})
    items = order.get("items", [])
    status = order.get("status", "unknown")
    status_text = {
        "pending_payment": "⏳ Ожидает оплаты",
        "paid": "✅ Оплачен",
        "cancelled": "❌ Отменён"
    }.get(status, status)
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
        await callback.answer("Нет доступа", show_alert=True)
        return
    order_id = callback.data.replace("admin_mark_paid_", "")
    order = orders_db.get(order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    order["status"] = "paid"
    await callback.answer("Заказ отмечен оплаченным")
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
        await callback.answer("Нет доступа", show_alert=True)
        return
    order_id = callback.data.replace("admin_mark_cancel_", "")
    order = orders_db.get(order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    order["status"] = "cancelled"
    await callback.answer("Заказ отменён")
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
        await callback.answer("Нет доступа", show_alert=True)
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


@dp.callback_query(F.data == "admin_edit_texts")
async def admin_edit_texts(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌿 Приветствие", callback_data="admin_edit_welcome")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")],
        ]
    )
    await callback.message.edit_text(
        "✏️ *Редактирование текстов*\n\nВыберите:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_edit_welcome")
async def admin_edit_welcome(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    editing_state[callback.from_user.id] = "welcome"
    current = get_text("welcome")
    preview = current[:500] + ("..." if len(current) > 500 else "")
    await callback.message.edit_text(
        f"✏️ *Редактирование: Приветствие*\n\n"
        f"*Текущий:*\n{preview}\n\n"
        f"Отправьте новый текст одним сообщением.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel_edit")]]
        )
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_cancel_edit")
async def admin_cancel_edit(callback: CallbackQuery):
    editing_state.pop(callback.from_user.id, None)
    await callback.answer("Отменено")
    await callback.message.edit_text(
        "✏️ Отменено.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]]
        )
    )


@dp.message(F.text & ~F.text.startswith("/"))
async def handle_text_edit(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    key = editing_state.get(message.from_user.id)
    if not key:
        return
    TEXTS[key] = message.text
    save_json(TEXTS_FILE, TEXTS)
    editing_state.pop(message.from_user.id, None)
    await message.answer(
        "✅ *Текст обновлён!*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ В админ-панель", callback_data="admin_back")]]
        )
    )


@dp.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 Заказы", callback_data="admin_orders")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="✏️ Редактировать тексты", callback_data="admin_edit_texts")],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin_close")],
        ]
    )
    await callback.message.edit_text(
        "🔧 *Админ-панель MagicHerbs*\n\nВыберите раздел:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_close")
async def admin_close(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
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
        log.info("💳 ЮKassa настроена — автоматическая оплата доступна")
    else:
        log.warning("💳 ЮKassa НЕ настроена — заказы уходят в ручной режим")
    await start_web_server()
    log.info("🚀 Бот запущен и готов к работе!")
    while True:
        try:
            await dp.start_polling(bot, skip_updates=True)
        except Exception as e:
            log.error(f"Ошибка polling: {e}")
            log.info("Перезапуск через 5 секунд...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            log.info("Бот остановлен вручную")
            break
        except Exception as e:
            log.error(f"Критическая ошибка: {e}")
            log.info("Перезапуск через 10 секунд...")
            import time
            time.sleep(10)