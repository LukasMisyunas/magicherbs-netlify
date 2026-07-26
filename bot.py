import asyncio
import json
import logging
import os
import hmac
import hashlib
import uuid
from urllib.parse import parse_qsl
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo,
    Message, CallbackQuery, FSInputFile, InputMediaPhoto
)
from aiogram.filters import Command
from aiogram import F
from pathlib import Path

# ===================== ПАПКА С ФОТО =====================
PHOTOS_DIR = Path(__file__).parent / "Photos"
PHOTO_MAIN_MENU = "main_menu.jpg"
PHOTO_FAQ = "faq.jpg"
PHOTO_DELIVERY = "delivery.jpg"
PHOTO_ABOUT = "about.jpg"
PHOTO_CONTACTS = "contacts.jpg"
PHOTO_CATALOG = "catalog.jpg"


def get_photo(filename: str):
    path = PHOTOS_DIR / filename
    if path.exists():
        return FSInputFile(str(path))
    return None


# ===================== ТЕКСТЫ С ЭМОДЗИ И ФОРМАТИРОВАНИЕМ =====================
FAQ_TEXT = (
    "❓ *Часто задаваемые вопросы*\n\n"
    "┌─────────────────────────┐\n"
    "│ *🌿 Товар натуральный?* │\n"
    "└─────────────────────────┘\n"
    "Да! Мы используем только дикорастущее сырьё Сибири и Алтая.\n"
    "✅ Никакого искусственно выращенного или китайского сырья\n"
    "✅ Только стеклянная тара, без пластика\n\n"
    
    "┌─────────────────────────┐\n"
    "│ *✨ В чём уникальность?* │\n"
    "└─────────────────────────┘\n"
    "Уникальная вакуумная низкотемпературная технология экстракции:\n"
    "🔬 Сохраняет полезные вещества растений\n"
    "🚫 Без выпаривания в «кастрюлях»\n"
    "🚫 Без вредных реагентов и консервантов\n"
    "📊 Эффективность экстракции — до 99%\n\n"
    
    "┌─────────────────────────┐\n"
    "│ *📜 Есть сертификаты?*  │\n"
    "└─────────────────────────┘\n"
    "Да, качество контролируется на всех этапах.\n"
    "🔍 Сертификаты — на сайте, раздел «Протоколы».\n\n"
    
    "┌─────────────────────────────┐\n"
    "│ *🏪 На маркетплейсах есть?* │\n"
    "└─────────────────────────────┘\n"
    "Нет! Мы принципиально не продаём продукцию:\n"
    "❌ На маркетплейсах\n"
    "❌ В массмаркетах\n"
    "💎 Только эксклюзивное качество и ограниченные объёмы\n\n"
    
    "┌─────────────────────────────┐\n"
    "│ *📦 Как отследить заказ?*  │\n"
    "└─────────────────────────────┘\n"
    "Трек-номер придёт на e-mail, указанный при оформлении.\n\n"
    
    "❓ Не нашли ответ? Напишите нам — кнопка «Контакты» ниже."
)

DELIVERY_TEXT = (
    "🚚 *Доставка и оплата*\n\n"
    "┌─────────────────────────────┐\n"
    "│   📦 *Способы доставки*     │\n"
    "└─────────────────────────────┘\n"
    "▸ 🚚 Стандартная — *бесплатно*, 3–5 рабочих дней\n"
    "▸ ✈️ Экспресс — *500 ₽*, 1–2 рабочих дня\n"
    "▸ 🎁 На заказы от *10 000 ₽* — скидка и бесплатная доставка\n\n"
    
    "┌─────────────────────────────┐\n"
    "│   💳 *Способы оплаты*       │\n"
    "└─────────────────────────────┘\n"
    "▸ 💳 OzonPay\n"
    "▸ 💳 CloudPayments (Visa/Mastercard/МИР)\n"
    "▸ 💳 Robokassa (СБП, карты, эл. кошельки)\n"
    "▸ 💳 ЮKassa (карта, ЮMoney, SberPay)\n\n"
    
    "📱 *Подробности* — на сайте, раздел «Доставка и оплата»"
)

ABOUT_TEXT = (
    "🌲 *О MagicHerbs*\n\n"
    "┌─────────────────────────────┐\n"
    "│   ✨ Наша история           │\n"
    "└─────────────────────────────┘\n"
    "MagicHerbs — семейный бренд, часть научно-производственного комплекса\n"
    "с более чем *20-летней историей* на рынке.\n\n"
    
    "┌─────────────────────────────┐\n"
    "│   🌿 Наше сырьё             │\n"
    "└─────────────────────────────┘\n"
    "▸ Только дикорастущие травы и растения\n"
    "▸ Собираем в экологических заповедниках Сибири\n"
    "▸ От Горного Алтая до севера Томской области\n"
    "▸ Производство — прямо в месте произрастания сырья\n"
    "▸ Сохраняем высокую концентрацию полезных веществ\n\n"
    
    "┌─────────────────────────────┐\n"
    "│   🎯 Наша миссия            │\n"
    "└─────────────────────────────┘\n"
    "Сохранить человечество в здоровом, не видоизменённом виде:\n"
    "🌱 Натуральные концентраты из дикорастущего сырья\n"
    "❌ Вместо синтетических препаратов\n\n"
    
    "ℹ️ Подробнее — в разделах «О нас» и «Миссия» на mherbs.ru"
)

CONTACTS_TEXT = (
    "📞 *Контакты*\n\n"
    "┌─────────────────────────────┐\n"
    "│   📍 Адрес                  │\n"
    "└─────────────────────────────┘\n"
    "г. Томск\n\n"
    
    "┌─────────────────────────────┐\n"
    "│   📱 Телефон                │\n"
    "└─────────────────────────────┘\n"
    "☎️ +7 900 922 4496\n\n"
    
    "┌─────────────────────────────┐\n"
    "│   ✉️ Email                  │\n"
    "└─────────────────────────────┘\n"
    "magicherbs4you@yandex.ru\n\n"
    
    "┌─────────────────────────────┐\n"
    "│   🌐 Социальные сети        │\n"
    "└─────────────────────────────┘\n"
    "▸ VK: vk.com/mherbs\n"
    "▸ Telegram: t.me/yegorogurtsov\n"
    "▸ WhatsApp: wa.me/79009224496\n\n"
    
    "┌─────────────────────────────┐\n"
    "│   💻 Сайт                   │\n"
    "└─────────────────────────────┘\n"
    "mherbs.ru"
)

WELCOME_TEXT = (
    "🌿 *Добро пожаловать в MagicHerbs!*\n\n"
    "🏔️ Натуральные нутрицевтики из Сибири\n"
    "✨ Создано природой — проверено наукой\n\n"
    "Выберите интересующий раздел 👇"
)


def main_menu_keyboard():
    """Главное меню с красивыми кнопками и иконками"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Открыть каталог", 
                    web_app=WebAppInfo(url=WEBAPP_URL)
                )
            ],
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


def back_keyboard():
    """Кнопка возврата в главное меню"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="menu_back")]
        ]
    )


def contacts_keyboard():
    """Кнопки для быстрого перехода по контактам"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📞 Позвонить", url="tel:+79009224496")],
            [InlineKeyboardButton(text="💬 Написать в WhatsApp", url="https://wa.me/79009224496")],
            [InlineKeyboardButton(text="✉️ Написать email", url="mailto:magicherbs4you@yandex.ru")],
            [InlineKeyboardButton(text="🌐 Перейти на сайт", url="https://mherbs.ru")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="menu_back")],
        ]
    )


# ===================== НАСТРОЙКИ =====================
BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])

YOOKASSA_SHOP_ID = os.environ.get("YOOKASSA_SHOP_ID", "")
YOOKASSA_SECRET_KEY = os.environ.get("YOOKASSA_SECRET_KEY", "")

WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://magicherbsss.netlify.app/")
ORDER_SHARED_SECRET = os.environ["ORDER_SHARED_SECRET"]
PORT = int(os.environ.get("PORT", 8080))

# ===================== ИНИЦИАЛИЗАЦИЯ =====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("bot")

bot = Bot(token=BOT_TOKEN, request_timeout=120)
dp = Dispatcher()
orders_db = {}
BOT_USERNAME = None


# ===================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====================
async def show_menu_section(
    callback: CallbackQuery, 
    text: str, 
    photo_filename: str, 
    keyboard: InlineKeyboardMarkup
):
    """Показывает раздел меню с фото и клавиатурой"""
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    photo = get_photo(photo_filename)
    if photo:
        await bot.send_photo(
            callback.from_user.id, 
            photo, 
            caption=text, 
            parse_mode="Markdown", 
            reply_markup=keyboard
        )
    else:
        await bot.send_message(
            callback.from_user.id, 
            text, 
            parse_mode="Markdown", 
            reply_markup=keyboard
        )
    await callback.answer()


def esc_md(text: str) -> str:
    """Экранирует спецсимволы Markdown"""
    for ch in ("\\", "_", "*", "`", "["):
        text = text.replace(ch, "\\" + ch)
    return text


def verify_telegram_init_data(init_data: str, bot_token: str):
    """Проверка подписи Telegram WebApp"""
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


# ===================== ЮKASSA ФУНКЦИИ =====================
async def create_yookassa_payment(amount, order_id, user_id):
    """Создаёт платёж в ЮKassa"""
    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        return None

    url = "https://api.yookassa.ru/v3/payments"
    idempotence_key = str(uuid.uuid4())
    headers = {"Idempotence-Key": idempotence_key, "Content-Type": "application/json"}
    auth = aiohttp.BasicAuth(login=YOOKASSA_SHOP_ID, password=YOOKASSA_SECRET_KEY)
    return_url = f"https://t.me/{BOT_USERNAME}" if BOT_USERNAME else "https://t.me/"

    payload = {
        "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
        "capture": True,
        "confirmation": {"type": "redirect", "return_url": return_url},
        "description": f"MagicHerbs — заказ #{order_id}",
        "metadata": {"order_id": order_id, "user_id": str(user_id)},
    }
    try:
        async with aiohttp.ClientSession(auth=auth) as session:
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


# ===================== WEBHOOK ОБРАБОТЧИКИ =====================
@web.middleware
async def cors_middleware(request: web.Request, handler):
    """CORS middleware для поддержки запросов с сайта"""
    if request.method == "OPTIONS":
        resp = web.Response()
    else:
        resp = await handler(request)
    resp.headers["Access-Control-Allow-Origin"] = WEBAPP_URL.rstrip("/")
    resp.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Order-Secret"
    return resp


async def handle_order(request: web.Request):
    """Обработка заказов с сайта"""
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

    # Формируем сообщение для админа
    if isinstance(items, list):
        items_lines = "\n".join(
            f"  • {esc_md(it.get('title', it.get('id', '?')))} — {it.get('qty', '?')} шт. × {it.get('price', '?')} ₽"
            for it in items
        )
    else:
        items_lines = esc_md(str(items))
    
    customer_lines = "\n".join(f"  {esc_md(str(k))}: {esc_md(str(v))}" for k, v in customer.items())

    payment_method = body.get("payment")

    # Автоматическая оплата через ЮKassa
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
                await bot.send_message(
                    ADMIN_ID,
                    f"🆕 *Новый заказ — ожидает оплаты (ЮKassa)*\n\n"
                    f"Номер: `{order_id}`\n"
                    f"Сумма: *{amount} ₽*\n"
                    f"Доставка: {esc_md(str(body.get('delivery', '—')))}\n\n"
                    f"*Контакты клиента:*\n{customer_lines}\n\n"
                    f"*Товары:*\n{items_lines}",
                    parse_mode="Markdown",
                )
            except Exception:
                log.exception("Не удалось отправить сообщение")
                return web.json_response({"ok": False, "error": "cannot message user"}, status=502)

            return web.json_response({"ok": True, "payment_url": result["confirmation_url"]})

    # Ручной режим оплаты (fallback)
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
        await bot.send_message(
            ADMIN_ID,
            f"🆕 *Новый заказ (ручная оплата)*\n\n"
            f"Номер: `{order_id}`\n"
            f"Сумма: *{amount} ₽*\n"
            f"Доставка: {esc_md(str(body.get('delivery', '—')))}\n"
            f"Оплата: {esc_md(str(payment_method or '—'))}\n\n"
            f"*Контакты клиента:*\n{customer_lines}\n\n"
            f"*Товары:*\n{items_lines}",
            parse_mode="Markdown",
        )
    except Exception:
        log.exception("Не удалось отправить сообщение")
        return web.json_response({"ok": False, "error": "cannot message user"}, status=502)

    return web.json_response({"ok": True, "manual": True})


# ===================== ХЕНДЛЕРЫ БОТА =====================
@dp.message(Command("start"))
async def start_command(message: Message):
    """Обработчик команды /start"""
    photo = get_photo(PHOTO_MAIN_MENU)
    if photo:
        await message.answer_photo(
            photo, 
            caption=WELCOME_TEXT, 
            parse_mode="Markdown", 
            reply_markup=main_menu_keyboard()
        )
    else:
        await message.answer(
            WELCOME_TEXT, 
            parse_mode="Markdown", 
            reply_markup=main_menu_keyboard()
        )


@dp.callback_query(F.data == "menu_faq")
async def menu_faq_handler(callback: CallbackQuery):
    """Обработчик FAQ"""
    await show_menu_section(callback, FAQ_TEXT, PHOTO_FAQ, back_keyboard())


@dp.callback_query(F.data == "menu_delivery")
async def menu_delivery_handler(callback: CallbackQuery):
    """Обработчик доставки"""
    await show_menu_section(callback, DELIVERY_TEXT, PHOTO_DELIVERY, back_keyboard())


@dp.callback_query(F.data == "menu_about")
async def menu_about_handler(callback: CallbackQuery):
    """Обработчик о бренде"""
    await show_menu_section(callback, ABOUT_TEXT, PHOTO_ABOUT, back_keyboard())


@dp.callback_query(F.data == "menu_contacts")
async def menu_contacts_handler(callback: CallbackQuery):
    """Обработчик контактов"""
    await show_menu_section(callback, CONTACTS_TEXT, PHOTO_CONTACTS, contacts_keyboard())


@dp.callback_query(F.data == "menu_back")
async def menu_back_handler(callback: CallbackQuery):
    """Возврат в главное меню"""
    await show_menu_section(callback, WELCOME_TEXT, PHOTO_MAIN_MENU, main_menu_keyboard())


# ===================== HTTP СЕРВЕР =====================
async def start_web_server():
    """Запуск HTTP сервера для приёма заказов"""
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_post("/webhook/order", handle_order)
    app.router.add_options("/webhook/order", lambda r: web.Response())
    app.router.add_get("/health", lambda r: web.json_response({"ok": True}))
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    log.info(f"🌐 HTTP сервер запущен на порту {PORT}")


# ===================== ЗАПУСК =====================
async def main():
    """Главная функция запуска бота"""
    global BOT_USERNAME
    
    me = await bot.get_me()
    BOT_USERNAME = me.username
    log.info(f"🤖 Бот: @{BOT_USERNAME}")
    
    if YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY:
        log.info("💳 ЮKassa настроена — автоматическая оплата доступна")
    else:
        log.warning("💳 ЮKassa НЕ настроена — заказы уходят в ручной режим")
    
    await start_web_server()
    log.info("🚀 Бот запущен и готов к работе!")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
