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

# ===================== ЛОГГЕР =====================
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
    "faq_intro": (
        "❓ *Часто задаваемые вопросы*\n\n"
        "Выберите интересующий вопрос 👇"
    ),
    "delivery_intro": (
        "🚚 *Доставка и оплата*\n\n"
        "Выберите раздел 👇"
    ),
    "about_intro": (
        "🌲 *О бренде MagicHerbs*\n\n"
        "Выберите раздел 👇"
    ),
    "contacts_intro": (
        "📞 *Контакты*\n\n"
        "Выберите раздел 👇"
    ),
}

# ===================== FAQ =====================
DEFAULT_FAQ = {
    "q_natural": {
        "title": "🌿 Товар натуральный?",
        "answer": (
            "🌿 *Товар натуральный?*\n\n"
            "Да! Мы используем только дикорастущее сырьё Сибири и Алтая.\n\n"
            "✅ Никакого искусственно выращенного или китайского сырья\n"
            "✅ Только стеклянная тара, без пластика"
        ),
    },
    "q_unique": {
        "title": "✨ В чём уникальность?",
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
        "title": "📜 Есть сертификаты?",
        "answer": (
            "📜 *Есть сертификаты?*\n\n"
            "Да, качество контролируется на всех этапах.\n\n"
            "🔍 Сертификаты — на сайте, раздел «Протоколы»."
        ),
    },
    "q_marketplaces": {
        "title": "🏪 На маркетплейсах есть?",
        "answer": (
            "🏪 *На маркетплейсах есть?*\n\n"
            "Нет! Мы принципиально не продаём продукцию:\n\n"
            "❌ На маркетплейсах\n"
            "❌ В массмаркетах\n\n"
            "💎 Только эксклюзивное качество и ограниченные объёмы"
        ),
    },
    "q_tracking": {
        "title": "📦 Как отследить заказ?",
        "answer": (
            "📦 *Как отследить заказ?*\n\n"
            "Трек-номер придёт на e-mail, указанный при оформлении."
        ),
    },
}

# ===================== ДОСТАВКА =====================
DEFAULT_DELIVERY = {
    "d_shipping": {
        "title": "📦 Способы доставки",
        "answer": (
            "📦 *Способы доставки*\n\n"
            "🚚 *Стандартная* — бесплатно\n"
            "Срок: 3–5 рабочих дней\n\n"
            "✈️ *Экспресс* — 500 ₽\n"
            "Срок: 1–2 рабочих дня\n\n"
            "🎁 *Бонус:* на заказы от 10 000 ₽ — скидка и бесплатная доставка"
        ),
    },
    "d_payment": {
        "title": "💳 Способы оплаты",
        "answer": (
            "💳 *Способы оплаты*\n\n"
            "▸ 💳 OzonPay\n"
            "▸ 💳 CloudPayments — Visa, Mastercard, МИР\n"
            "▸ 💳 Robokassa — СБП, карты, электронные кошельки\n"
            "▸ 💳 ЮKassa — карта, ЮMoney, SberPay\n\n"
            "📱 Подробнее — на сайте, раздел «Доставка и оплата»"
        ),
    },
}

# ===================== О БРЕНДЕ =====================
DEFAULT_ABOUT = {
    "a_history": {
        "title": "✨ Наша история",
        "answer": (
            "✨ *Наша история*\n\n"
            "MagicHerbs — семейный бренд, часть научно-производственного комплекса "
            "с более чем *20-летней историей* на рынке."
        ),
    },
    "a_raw": {
        "title": "🌿 Наше сырьё",
        "answer": (
            "🌿 *Наше сырьё*\n\n"
            "▸ Только дикорастущие травы и растения\n"
            "▸ Собираем в экологических заповедниках Сибири\n"
            "▸ От Горного Алтая до севера Томской области\n"
            "▸ Производство — прямо в месте произрастания сырья\n"
            "▸ Сохраняем высокую концентрацию полезных веществ"
        ),
    },
    "a_mission": {
        "title": "🎯 Наша миссия",
        "answer": (
            "🎯 *Наша миссия*\n\n"
            "Сохранить человечество в здоровом, не видоизменённом виде:\n\n"
            "🌱 Натуральные концентраты из дикорастущего сырья\n"
            "❌ Вместо синтетических препаратов\n\n"
            "ℹ️ Подробнее — в разделах «О нас» и «Миссия» на mherbs.ru"
        ),
    },
}

# ===================== КОНТАКТЫ =====================
DEFAULT_CONTACTS = {
    "c_phone": {
        "title": "📱 Телефон и email",
        "answer": (
            "📱 *Телефон и email*\n\n"
            "☎️ +7 900 922 4496\n"
            "✉️ magicherbs4you@yandex.ru"
        ),
    },
    "c_social": {
        "title": "🌐 Социальные сети",
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
answer_message_ids = {}   # ID сообщения с ответом для каждого пользователя


# ===================== КЛАВИАТУРЫ =====================
def main_menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Открыть каталог", web_app=WebAppInfo(url=WEBAPP_URL))],
            [
                InlineKeyboardButton(text="❓ FAQ", callback_data="menu_faq"),
                InlineKeyboardButton(text="🚚 Доставка", callback_data="menu_delivery"),
            ],
            [
                InlineKeyboardButton(text="🌲 О бренде", callback_data="menu_about"),
                InlineKeyboardButton(text="📞 Контакты", callback_data="menu_contacts"),
            ],
        ]
    )


def submenu_keyboard(items: dict, prefix: str, back_to: str = "menu_back"):
    buttons = []
    for key, item in items.items():
        buttons.append([InlineKeyboardButton(text=item["title"], callback_data=f"{prefix}{key}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=back_to)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ===================== ОТПРАВКА =====================
async def send_with_questions(callback: CallbackQuery, photo_filename: str, intro_text: str, questions: dict, prefix: str, back_to: str = "menu_back"):
    """Отправляет фото + интро + кнопки вопросов. Удаляет старое сообщение с ответом."""
    try:
        if callback.message:
            await callback.message.delete()
    except Exception:
        pass

    # Удаляем старое сообщение с ответом
    old_answer_id = answer_message_ids.pop(callback.from_user.id, None)
    if old_answer_id:
        try:
            await bot.delete_message(callback.from_user.id, old_answer_id)
        except Exception:
            pass

    photo = get_photo(photo_filename)

    try:
        if photo:
            await bot.send_photo(
                callback.from_user.id,
                photo,
                caption=intro_text,
                parse_mode="Markdown",
                reply_markup=submenu_keyboard(questions, prefix, back_to)
            )
        else:
            await bot.send_message(
                callback.from_user.id,
                intro_text,
                parse_mode="Markdown",
                reply_markup=submenu_keyboard(questions, prefix, back_to)
            )
    except Exception as e:
        log.error(f"Ошибка отправки меню: {e}")


async def show_answer(callback: CallbackQuery, text: str):
    """Показывает ответ НИЖЕ меню. Если уже есть — редактирует его."""
    user_id = callback.from_user.id
    old_id = answer_message_ids.get(user_id)

    if old_id:
        try:
            await bot.edit_message_text(
                text,
                chat_id=user_id,
                message_id=old_id,
                parse_mode="Markdown"
            )
            return
        except Exception as e:
            log.warning(f"Не удалось отредактировать: {e}")
            try:
                await bot.delete_message(user_id, old_id)
            except Exception:
                pass

    try:
        msg = await bot.send_message(user_id, text, parse_mode="Markdown")
        answer_message_ids[user_id] = msg.message_id
    except Exception as e:
        log.error(f"Не удалось отправить ответ: {e}")


# ===================== /start =====================
@dp.message(Command("start"))
async def start_command(message: Message):
    try:
        # Удаляем старое сообщение с ответом
        old_answer_id = answer_message_ids.pop(message.from_user.id, None)
        if old_answer_id:
            try:
                await bot.delete_message(message.from_user.id, old_answer_id)
            except Exception:
                pass

        photo = get_photo(PHOTO_MAIN_MENU)
        if photo:
            await message.answer_photo(
                photo,
                caption=get_text("welcome"),
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        else:
            await message.answer(
                get_text("welcome"),
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
    except Exception as e:
        log.exception(f"Ошибка в /start: {e}")


# ===================== FAQ =====================
@dp.callback_query(F.data == "menu_faq")
async def menu_faq_handler(callback: CallbackQuery):
    await send_with_questions(callback, PHOTO_FAQ, get_text("faq_intro"), FAQ, "faq_", "menu_back")
    try:
        await callback.answer()
    except Exception:
        pass


@dp.callback_query(F.data.startswith("faq_q_"))
async def faq_answer_handler(callback: CallbackQuery):
    key = callback.data.replace("faq_", "")
    item = FAQ.get(key)
    if not item:
        await callback.answer("Не найдено", show_alert=True)
        return
    await show_answer(callback, item["answer"])
    try:
        await callback.answer()
    except Exception:
        pass


# ===================== ДОСТАВКА =====================
@dp.callback_query(F.data == "menu_delivery")
async def menu_delivery_handler(callback: CallbackQuery):
    await send_with_questions(callback, PHOTO_DELIVERY, get_text("delivery_intro"), DELIVERY, "del_", "menu_back")
    try:
        await callback.answer()
    except Exception:
        pass


@dp.callback_query(F.data.startswith("del_d_"))
async def delivery_answer_handler(callback: CallbackQuery):
    key = callback.data.replace("del_", "")
    item = DELIVERY.get(key)
    if not item:
        await callback.answer("Не найдено", show_alert=True)
        return
    await show_answer(callback, item["answer"])
    try:
        await callback.answer()
    except Exception:
        pass


# ===================== О БРЕНДЕ =====================
@dp.callback_query(F.data == "menu_about")
async def menu_about_handler(callback: CallbackQuery):
    await send_with_questions(callback, PHOTO_ABOUT, get_text("about_intro"), ABOUT, "ab_", "menu_back")
    try:
        await callback.answer()
    except Exception:
        pass


@dp.callback_query(F.data.startswith("ab_a_"))
async def about_answer_handler(callback: CallbackQuery):
    key = callback.data.replace("ab_", "")
    item = ABOUT.get(key)
    if not item:
        await callback.answer("Не найдено", show_alert=True)
        return
    await show_answer(callback, item["answer"])
    try:
        await callback.answer()
    except Exception:
        pass


# ===================== КОНТАКТЫ =====================
@dp.callback_query(F.data == "menu_contacts")
async def menu_contacts_handler(callback: CallbackQuery):
    await send_with_questions(callback, PHOTO_CONTACTS, get_text("contacts_intro"), CONTACTS, "ct_", "menu_back")
    try:
        await callback.answer()
    except Exception:
        pass


@dp.callback_query(F.data.startswith("ct_c_"))
async def contacts_answer_handler(callback: CallbackQuery):
    key = callback.data.replace("ct_", "")
    item = CONTACTS.get(key)
    if not item:
        await callback.answer("Не найдено", show_alert=True)
        return
    await show_answer(callback, item["answer"])
    try:
        await callback.answer()
    except Exception:
        pass


# ===================== НАЗАД =====================
@dp.callback_query(F.data == "menu_back")
async def menu_back_handler(callback: CallbackQuery):
    try:
        if callback.message:
            await callback.message.delete()
    except Exception:
        pass

    old_answer_id = answer_message_ids.pop(callback.from_user.id, None)
    if old_answer_id:
        try:
            await bot.delete_message(callback.from_user.id, old_answer_id)
        except Exception:
            pass

    photo = get_photo(PHOTO_MAIN_MENU)
    text = get_text("welcome")

    try:
        if photo:
            await bot.send_photo(
                callback.from_user.id,
                photo,
                caption=text,
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        else:
            await bot.send_message(
                callback.from_user.id,
                text,
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
    except Exception as e:
        log.error(f"Ошибка меню: {e}")
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
                    f"🔗 [Перейти к оплате]({result['confirmation_url']})\n\n"
                    f"После успешной оплаты вы автоматически получите подтверждение.",
                    parse_mode="Markdown",
                )
            except Exception:
                log.exception("Не удалось отправить сообщение клиенту")
            try:
                await bot.send_message(
                    ADMIN_ID,
                    f"🆕 *Новый заказ — ожидает оплаты (ЮKassa)*\n\n"
                    f"Номер: `{order_id}`\n"
                    f"Сумма: *{amount} ₽*\n"
                    f"{client_line}\n"
                    f"Доставка: {esc_md(str(body.get('delivery', '—')))}\n\n"
                    f"*Контакты клиента:*\n{customer_lines}\n\n"
                    f"*Товары:*\n{items_lines}",
                    parse_mode="Markdown",
                )
            except Exception:
                log.exception("Не удалось отправить сообщение админу")
            return web.json_response({"ok": True, "payment_url": result["confirmation_url"]})
    try:
        await bot.send_message(
            user_id,
            f"✅ *Заказ принят!*\n\n"
            f"Номер заказа: `{order_id}`\n"
            f"Сумма: *{amount} ₽*\n\n"
            f"Для оплаты и уточнения деталей с вами свяжется наш менеджер в ближайшее время.\n"
            f"Спасибо, что выбрали MagicHerbs! 🌲",
            parse_mode="Markdown",
        )
    except Exception:
        log.exception("Не удалось отправить сообщение клиенту")
    try:
        await bot.send_message(
            ADMIN_ID,
            f"🆕 *Новый заказ (ручная оплата)*\n\n"
            f"Номер: `{order_id}`\n"
            f"Сумма: *{amount} ₽*\n"
            f"{client_line}\n"
            f"Доставка: {esc_md(str(body.get('delivery', '—')))}\n"
            f"Оплата: {esc_md(str(payment_method or '—'))}\n\n"
            f"*Контакты клиента:*\n{customer_lines}\n\n"
            f"*Товары:*\n{items_lines}",
            parse_mode="Markdown",
        )
    except Exception:
        log.exception("Не удалось отправить сообщение админу")
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
                    f"Заказ `{order_id}` на сумму *{amount} ₽* успешно оплачен.\n"
                    f"Мы свяжемся с вами для уточнения доставки. Спасибо! 🌲",
                    parse_mode="Markdown",
                )
            except Exception:
                log.exception("Не удалось отправить клиенту")
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
                log.exception("Не удалось отправить админу")
    elif event == "payment.canceled" and order_id:
        order = orders_db.get(order_id)
        if order:
            order["status"] = "cancelled"
            log.info(f"Платёж отменён: {order_id}")
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
            [InlineKeyboardButton(text="🛒 Товары (в каталоге)", callback_data="admin_products_hint")],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin_close")],
        ]
    )
    await message.answer(
        "🔧 *Админ-панель MagicHerbs*\n\n"
        "Выберите раздел:",
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
        f"*Контакты клиента:*\n{customer_lines}\n\n"
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


@dp.callback_query(F.data == "admin_products_hint")
async def admin_products_hint(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.edit_text(
        "🛒 *Управление товарами*\n\n"
        "Товары редактируются в каталоге (Mini App).\n\n"
        "Откройте каталог через кнопку в /start.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]]
        )
    )
    await callback.answer()


# ===================== РЕДАКТИРОВАНИЕ ТЕКСТОВ =====================
@dp.callback_query(F.data == "admin_edit_texts")
async def admin_edit_texts(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌿 Приветствие", callback_data="admin_edit_welcome")],
            [InlineKeyboardButton(text="❓ FAQ (интро)", callback_data="admin_edit_faq_intro")],
            [InlineKeyboardButton(text="🚚 Доставка (интро)", callback_data="admin_edit_delivery_intro")],
            [InlineKeyboardButton(text="🌲 О бренде (интро)", callback_data="admin_edit_about_intro")],
            [InlineKeyboardButton(text="📞 Контакты (интро)", callback_data="admin_edit_contacts_intro")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")],
        ]
    )
    await callback.message.edit_text(
        "✏️ *Редактирование текстов*\n\n"
        "Выберите, что хотите изменить:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("admin_edit_"))
async def admin_edit_choice(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    key = callback.data.replace("admin_edit_", "")
    if key not in DEFAULT_TEXTS:
        await callback.answer("Раздел не найден", show_alert=True)
        return
    names = {
        "welcome": "Приветствие",
        "faq_intro": "FAQ (интро)",
        "delivery_intro": "Доставка (интро)",
        "about_intro": "О бренде (интро)",
        "contacts_intro": "Контакты (интро)",
    }
    editing_state[callback.from_user.id] = key
    current_text = get_text(key)
    preview = current_text[:500] + ("..." if len(current_text) > 500 else "")
    await callback.message.edit_text(
        f"✏️ *Редактирование: {names.get(key, key)}*\n\n"
        f"*Текущий текст:*\n{preview}\n\n"
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
        "✏️ Редактирование отменено.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_edit_texts")]]
        )
    )


@dp.message(F.text & ~F.text.startswith("/"))
async def handle_text_edit(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    key = editing_state.get(message.from_user.id)
    if not key:
        return
    new_text = message.text
    TEXTS[key] = new_text
    save_json(TEXTS_FILE, TEXTS)
    editing_state.pop(message.from_user.id, None)
    names = {
        "welcome": "Приветствие",
        "faq_intro": "FAQ (интро)",
        "delivery_intro": "Доставка (интро)",
        "about_intro": "О бренде (интро)",
        "contacts_intro": "Контакты (интро)",
    }
    await message.answer(
        f"✅ *Текст «{names.get(key, key)}» обновлён!*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Ещё", callback_data="admin_edit_texts")],
                [InlineKeyboardButton(text="⬅️ В админ-панель", callback_data="admin_back")],
            ]
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
            [InlineKeyboardButton(text="🛒 Товары (в каталоге)", callback_data="admin_products_hint")],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin_close")],
        ]
    )
    await callback.message.edit_text(
        "🔧 *Админ-панель MagicHerbs*\n\n"
        "Выберите раздел:",
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
