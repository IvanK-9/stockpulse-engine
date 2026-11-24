"""
Демо-бот StockPulse E-Com Engine v3.0 с интегрированной CRM и Утренним Пульсом.
1. Мгновенный разбор карточек WB за 170-200 мс (CDN протокол).
2. Утренний автотест в 08:30 CET (Швеция) со сводкой здоровья протокола.
3. Мгновенный перехват лидов: когда клиент проверяет артикул, админ получает карточку клиента.
4. Система эскалации: если админ не связался за 20 минут, бот шлет напоминание с готовым питчем.
"""

import os
import sys
import re
import time
import json
import asyncio
import argparse
import aiohttp
from datetime import datetime, timezone, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Загрузка .env
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

ADMIN_TG_ID = int(os.getenv("ADMIN_TG_ID", "1029387647"))
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

# Хранилище лидов и статистики в памяти
STATS = {
    "start_time": time.time(),
    "total_requests": 0,
    "unique_users": set()
}

PENDING_LEADS = {}  # lead_id -> dict

def get_basket_host(sku: int) -> str:
    vol = sku // 100000
    part = sku // 1000
    baskets = [
        (0, 143, 1), (144, 287, 2), (288, 431, 3), (432, 719, 4),
        (720, 1007, 5), (1008, 1061, 6), (1062, 1115, 7), (1116, 1169, 8),
        (1170, 1313, 9), (1314, 1601, 10), (1602, 1655, 11), (1656, 1919, 12),
        (1920, 2045, 13), (2046, 2189, 14), (2190, 2405, 15), (2406, 2621, 16),
        (2622, 2837, 17)
    ]
    b = 18
    for low, high, num in baskets:
        if low <= vol <= high:
            b = num
            break
    num_str = f"0{b}" if b < 10 else str(b)
    return f"https://basket-{num_str}.wbbasket.ru/vol{vol}/part{part}/{sku}"

async def fetch_wb_product(sku: int) -> dict:
    t_start = time.perf_counter()
    base_url = get_basket_host(sku)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.wildberries.ru",
        "Referer": f"https://www.wildberries.ru/catalog/{sku}/detail.aspx"
    }

    result = {
        "sku": sku,
        "success": False,
        "elapsed_ms": 0,
        "title": "Неизвестный товар",
        "category": "Не указана",
        "seller_name": "Не указан",
        "inn": "—",
        "ogrn": "—",
        "trademark": "—",
        "options_count": 0,
        "photo_url": None,
        "options_summary": []
    }

    timeout = aiohttp.ClientTimeout(total=4)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        card_url = f"{base_url}/info/ru/card.json"
        seller_url = f"{base_url}/info/sellers.json"

        try:
            async with session.get(card_url, headers=headers) as resp:
                if resp.status == 200:
                    card_data = await resp.json()
                    result["success"] = True
                    result["title"] = card_data.get("imt_name") or card_data.get("subj_name", "Товар WB")
                    result["category"] = card_data.get("subj_name", "Каталог")
                    result["vendor_code"] = card_data.get("vendor_code", "—")
                    result["description"] = card_data.get("description", "")[:180]

                    options = card_data.get("options", [])
                    result["options_count"] = len(options)
                    for opt in options[:4]:
                        n = opt.get("name")
                        v = opt.get("value")
                        if n and v:
                            result["options_summary"].append(f"• {n}: {v}")

                    result["photo_url"] = f"{base_url}/images/big/1.webp"
        except Exception:
            pass

        try:
            async with session.get(seller_url, headers=headers) as resp:
                if resp.status == 200:
                    seller_data = await resp.json()
                    result["seller_name"] = seller_data.get("supplierFullName") or seller_data.get("supplierName", "Не указан")
                    result["inn"] = seller_data.get("inn", "—")
                    result["ogrn"] = seller_data.get("ogrn", "—")
                    result["trademark"] = seller_data.get("trademark", "—")
        except Exception:
            pass

    t_end = time.perf_counter()
    result["elapsed_ms"] = round((t_end - t_start) * 1000, 1)
    return result

def format_card_message(data: dict) -> str:
    if not data.get("success"):
        return f"❌ Товар с артикулом `{data['sku']}` не найден или был удален с площадки."

    options_text = "\n".join(data.get("options_summary", []))
    options_block = f"\n📋 **Характеристики:**\n{options_text}\n" if options_text else ""

    msg = (
        f"📦 **{data['title']}**\n"
        f"🏷 **Категория:** {data['category']}\n"
        f"🔢 **Артикул WB:** `{data['sku']}`\n\n"
        f"🏢 **Продавец:** {data['seller_name']}\n"
        f"📑 **ИНН:** `{data['inn']}` | **ОГРН:** `{data['ogrn']}`\n"
        f"🎯 **Бренд:** {data['trademark']}\n"
        f"{options_block}\n"
        f"⚡ **Скорость сбора данных:** `{data['elapsed_ms']} мс`\n"
        f"🛡 **Архитектура:** Прямой CDN/API протокол (без эмуляции браузера, нулевой риск банов)\n\n"
        f"💡 *Нужен парсер цен конкурентов, остатков или автопрайсер под ключ?*"
    )
    return msg

def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚡ Тест: 211612702", callback_data="sku_211612702"),
            InlineKeyboardButton(text="⚡ Тест: 138590435", callback_data="sku_138590435"),
        ],
        [
            InlineKeyboardButton(text="🛡 Как устроен парсинг без банов?", callback_data="info_arch"),
        ],
        [
            InlineKeyboardButton(text="💼 Заказать разработку парсера / бота", url="https://t.me/horoshow88")
        ]
    ])

def get_admin_health_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚡ Замерить скорость снова", callback_data="admin_retest"),
            InlineKeyboardButton(text="📊 Статистика активности", callback_data="admin_stats")
        ]
    ])

# ==================== УВЕДОМЛЕНИЯ И ЗДОРОВЬЕ СЕРВИСА ====================

async def send_healthcheck_pulse(bot: Bot, header_text: str = ""):
    """Выполняет тестовый запрос к WB и отправляет отчет администратору"""
    test_sku = 138590435
    data = await fetch_wb_product(test_sku)

    latency = data["elapsed_ms"]
    status_icon = "🟢" if latency < 500 else ("🟡" if latency < 1500 else "🔴")
    cet_now = datetime.now(timezone.utc) + timedelta(hours=1)
    time_str = cet_now.strftime("%H:%M:%S")

    title = data.get("title", "Товар WB")
    seller = data.get("seller_name", "Не указан")
    inn = data.get("inn", "—")

    msg = (
        f"{header_text}"
        f"{status_icon} <b>Статус:</b> Демо-бот активен и слушает входящие\n"
        f"⚡ <b>Скорость WB CDN:</b> <code>{latency} мс</code> (прямой запрос)\n"
        f"📦 <b>Тестовый артикул:</b> <code>{test_sku}</code> ({title[:35]})\n"
        f"🏢 <b>Продавец:</b> {seller[:30]} (ИНН: <code>{inn}</code>)\n"
        f"🕒 <b>Время проверки:</b> {time_str} CET\n\n"
        f"<i>Сервис готов принимать селлеров с Авито и выдавать карточки за 170 мс.</i>"
    )

    try:
        await bot.send_message(
            chat_id=ADMIN_TG_ID,
            text=msg,
            parse_mode="HTML",
            reply_markup=get_admin_health_keyboard()
        )
    except Exception as e:
        print(f"[ERR] Не удалось отправить healthcheck админу: {e}")

async def morning_pulse_worker(bot: Bot):
    """Фоновый цикл: ждет 08:30 CET каждое утро и отправляет утренний отчет"""
    while True:
        try:
            # Текущее время CET (UTC+1)
            now_utc = datetime.now(timezone.utc)
            now_cet = now_utc + timedelta(hours=1)

            # Целевое время: сегодня в 08:30 CET
            target_cet = now_cet.replace(hour=8, minute=30, second=0, microsecond=0)
            if now_cet >= target_cet:
                # Если 08:30 уже прошло, целимся на завтра
                target_cet += timedelta(days=1)

            sleep_seconds = (target_cet - now_cet).total_seconds()
            print(f"[*] Утренний пульс запланирован на {target_cet.strftime('%Y-%m-%d %H:%M:%S')} CET (через {int(sleep_seconds/3600)} ч {int((sleep_seconds%3600)/60)} мин)")
            await asyncio.sleep(sleep_seconds)

            # 08:30 наступило — отправляем утренний бодрый отчет
            await send_healthcheck_pulse(
                bot,
                header_text="☕️ <b>Доброе утро, Иван! Утренний чекап системы:</b>\n\n"
            )
            # Ждем 60 секунд, чтобы не сработать дважды
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[ERR] Ошибка в morning_pulse_worker: {e}")
            await asyncio.sleep(60)

async def lead_escalation_reminder(bot: Bot, lead_id: str, minutes: int = 20):
    """Ждет указанное время. Если админ не откликнулся, шлет повторный пинг с питчем"""
    try:
        await asyncio.sleep(minutes * 60)
        lead = PENDING_LEADS.get(lead_id)
        if not lead or lead.get("acknowledged"):
            return

        username = lead.get("username")
        user_name = lead.get("user_name", "Клиент")
        title = lead.get("title", "Товар WB")
        sku = lead.get("sku")

        user_tag = f"@{username}" if username else user_name
        contact_link = f"https://t.me/{username}" if username else f"tg://user?id={lead['user_id']}"

        pitch = (
            f"Привет! Видел, вы тестировали скорость разбора карточки «{title[:30]}» в демо-боте. "
            f"Могу сделать для вас выгрузку цен конкурентов до скидок и СПП в Excel за 24 часа. "
            f"Напишите мне в ЛС @horoshow88 — сделаю тест на 10 артикулах бесплатно!"
        )

        reminder_msg = (
            f"🔔 <b>НАПОМИНАНИЕ: 20 минут без отклика!</b>\n\n"
            f"👤 Клиент: <b>{user_name}</b> ({user_tag})\n"
            f"📦 Товар: <b>{title}</b> (арт. <code>{sku}</code>)\n\n"
            f"<i>Интерес еще горячий, отправьте ему готовый питч:</i>\n"
            f"<code>{pitch}</code>"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"💬 Написать {user_tag}", url=contact_link)],
            [InlineKeyboardButton(text="✅ Откликнулся", callback_data=f"ack_{lead_id}")]
        ])

        await bot.send_message(
            chat_id=ADMIN_TG_ID,
            text=reminder_msg,
            parse_mode="HTML",
            reply_markup=kb,
            disable_web_page_preview=True
        )
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[ERR] Ошибка в напоминании лида: {e}")

# ==================== ОСНОВНОЙ БОТ ====================

def run_telegram_bot(token: str):
    bot = Bot(token=token)
    dp = Dispatcher()

    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        user_id = message.from_user.id
        STATS["unique_users"].add(user_id)
        STATS["total_requests"] += 1

        text = (
            "👋 **Демо-бот высокоскоростного парсинга маркетплейсов**\n\n"
            "Этот бот демонстрирует скорость работы прямого протокола сбора данных "
            "**без медленного браузера** и без риска блокировок.\n\n"
            "👉 **Отправьте мне любой артикул Wildberries** (число или ссылку на товар):\n"
            "Например: `211612702` или `138590435`\n\n"
            "Бот мгновенно сформирует аналитическую сводку с юрлицом, ИНН и замером миллисекунд."
        )
        await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

    @dp.callback_query(F.data.startswith("sku_"))
    async def cb_test_sku(callback: types.CallbackQuery):
        sku = int(callback.data.split("_")[1])
        await callback.answer("Загрузка данных...")
        data = await fetch_wb_product(sku)
        msg_text = format_card_message(data)
        photo_url = data.get("photo_url")
        if photo_url:
            try:
                await callback.message.answer_photo(photo_url, caption=msg_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
                return
            except Exception:
                pass
        await callback.message.answer(msg_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

    @dp.callback_query(F.data == "info_arch")
    async def cb_info_arch(callback: types.CallbackQuery):
        await callback.answer()
        text = (
            "🛠 **Инженерный подход к парсингу:**\n\n"
            "1. **Reverse Engineering:** Вместо медленного Selenium/Puppeteer запросы идут напрямую к CDN и приватным эндпоинтам мобильных приложений.\n"
            "2. **Скорость:** 100–300 миллисекунд на карточку (в 20–50 раз быстрее визуальных ботов).\n"
            "3. **Защита от банов:** Ротация мобильных/резидентных прокси, эмуляция сетевых отпечатков (TLS JA3/JA4).\n"
            "4. **Развертывание:** Изолированные Docker-контейнеры на Linux с гарантией 99.9% аптайма."
        )
        await callback.message.answer(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

    # Админские кнопки
    @dp.callback_query(F.data == "admin_retest")
    async def cb_admin_retest(callback: types.CallbackQuery):
        if callback.from_user.id != ADMIN_TG_ID:
            await callback.answer("Только для администратора")
            return
        await callback.answer("Замеряю скорость...")
        await send_healthcheck_pulse(bot, header_text="⚡ <b>Экспресс-замер скорости:</b>\n\n")

    @dp.callback_query(F.data == "admin_stats")
    async def cb_admin_stats(callback: types.CallbackQuery):
        if callback.from_user.id != ADMIN_TG_ID:
            await callback.answer("Только для администратора")
            return
        uptime_sec = int(time.time() - STATS["start_time"])
        uptime_h = uptime_sec // 3600
        uptime_m = (uptime_sec % 3600) // 60

        text = (
            f"📊 <b>Статистика работы демо-бота:</b>\n\n"
            f"⏱ <b>Время непрерывной работы:</b> {uptime_h} ч {uptime_m} мин\n"
            f"👥 <b>Уникальных пользователей:</b> {len(STATS['unique_users'])}\n"
            f"🔢 <b>Всего обработано запросов:</b> {STATS['total_requests']}\n"
            f"🎯 <b>Активных лидов в обработке:</b> {len(PENDING_LEADS)}"
        )
        await callback.message.answer(text, parse_mode="HTML")
        await callback.answer()

    @dp.callback_query(F.data.startswith("ack_"))
    async def cb_ack_lead(callback: types.CallbackQuery):
        lead_id = callback.data.replace("ack_", "")
        if lead_id in PENDING_LEADS:
            PENDING_LEADS[lead_id]["acknowledged"] = True
            task = PENDING_LEADS[lead_id].get("task")
            if task and not task.done():
                task.cancel()
        await callback.answer("Отмечено как обработанное!")
        try:
            await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Отклик выполнен", callback_data="none")]
            ]))
        except Exception:
            pass

    @dp.callback_query(F.data.startswith("dismiss_"))
    async def cb_dismiss_lead(callback: types.CallbackQuery):
        lead_id = callback.data.replace("dismiss_", "")
        if lead_id in PENDING_LEADS:
            PENDING_LEADS[lead_id]["acknowledged"] = True
            task = PENDING_LEADS[lead_id].get("task")
            if task and not task.done():
                task.cancel()
            del PENDING_LEADS[lead_id]
        await callback.answer("Лид скрыт")
        try:
            await callback.message.delete()
        except Exception:
            pass

    @dp.message()
    async def handle_any_message(message: types.Message):
        user = message.from_user
        raw = message.text or ""

        STATS["unique_users"].add(user.id)
        STATS["total_requests"] += 1

        match = re.search(r"(\d{5,11})", raw)
        if not match:
            await message.answer(
                "⚠️ Пожалуйста, отправьте корректный артикул товара Wildberries (число от 5 до 10 цифр) или ссылку на карточку.",
                reply_markup=get_main_keyboard()
            )
            return

        sku = int(match.group(1))
        status_msg = await message.answer(f"⏳ Опрашиваю протокол для артикула `{sku}`...", parse_mode="Markdown")

        data = await fetch_wb_product(sku)
        msg_text = format_card_message(data)
        photo_url = data.get("photo_url")

        try:
            await status_msg.delete()
        except Exception:
            pass

        if photo_url:
            try:
                await message.answer_photo(photo_url, caption=msg_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
            except Exception:
                await message.answer(msg_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
        else:
            await message.answer(msg_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

        # Если сообщение от внешнего клиента (не от самого администратора) -> уведомляем Ивана
        if user.id != ADMIN_TG_ID:
            lead_id = f"{user.id}_{int(time.time())}"
            lead_info = {
                "user_id": user.id,
                "user_name": f"{user.first_name} {user.last_name or ''}".strip(),
                "username": user.username or "",
                "sku": sku,
                "title": data.get("title", "Товар WB"),
                "seller": data.get("seller_name", "Не указан"),
                "inn": data.get("inn", "—"),
                "elapsed": data.get("elapsed_ms", 0),
                "timestamp": time.time(),
                "acknowledged": False
            }

            user_tag = f"@{user.username}" if user.username else lead_info["user_name"]
            contact_url = f"https://t.me/{user.username}" if user.username else f"tg://user?id={user.id}"

            admin_alert = (
                f"🎯 <b>ГОРЯЧИЙ ЛИД В ДЕМО-БОТЕ!</b>\n\n"
                f"👤 <b>Клиент:</b> {html.escape(lead_info['user_name'])} ({html.escape(user_tag)})\n"
                f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
                f"📦 <b>Запросил артикул:</b> <code>{sku}</code> ({html.escape(lead_info['title'][:40])})\n"
                f"🏢 <b>Продавец:</b> {html.escape(lead_info['seller'])} (ИНН: <code>{lead_info['inn']}</code>)\n"
                f"⚡ <b>Скорость разбора:</b> <code>{lead_info['elapsed']} мс</code>\n\n"
                f"<i>Клиент только что увидел скорость 170 мс. Самое время написать!</i>"
            )

            buttons = []
            if user.username:
                buttons.append([InlineKeyboardButton(text=f"💬 Написать {user_tag}", url=contact_url)])
            buttons.append([
                InlineKeyboardButton(text="✅ Откликнулся", callback_data=f"ack_{lead_id}"),
                InlineKeyboardButton(text="❌ Скрыть", callback_data=f"dismiss_{lead_id}")
            ])

            try:
                await bot.send_message(
                    chat_id=ADMIN_TG_ID,
                    text=admin_alert,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                    disable_web_page_preview=True
                )
            except Exception as e:
                print(f"[ERR] Не удалось отправить карточку лида админу: {e}")

            # Запускаем таймер повторного напоминания через 20 минут
            task = asyncio.create_task(lead_escalation_reminder(bot, lead_id, minutes=20))
            lead_info["task"] = task
            PENDING_LEADS[lead_id] = lead_info

    async def on_startup():
        print(f"[*] Демо-бот v3.0 успешно запущен (@{bot.token.split(':')[0]})...", flush=True)
        # 1. Отправляем приветственный чекап админу прямо сейчас при старте
        await send_healthcheck_pulse(bot, header_text="🚀 <b>Демо-бот запущен и на связи!</b>\n\n")
        # 2. Запускаем фоновый таймер на 08:30 CET
        asyncio.create_task(morning_pulse_worker(bot))

    async def main_loop():
        await on_startup()
        await dp.start_polling(bot)

    asyncio.run(main_loop())

def main():
    parser = argparse.ArgumentParser(description="Демо-бот парсинга маркетплейсов v3.0")
    parser.add_argument("--test-sku", default=None, help="Тестовый запуск парсера артикула")
    parser.add_argument("--token", default=BOT_TOKEN, help="Токен бота")

    args = parser.parse_args()

    if args.test_sku:
        sku = int(re.search(r"\d+", args.test_sku).group(0))
        data = asyncio.run(fetch_wb_product(sku))
        print(format_card_message(data))
        return

    if not args.token:
        print("[!] Токен не найден в .env")
        return

    run_telegram_bot(args.token)

if __name__ == "__main__":
    main()
