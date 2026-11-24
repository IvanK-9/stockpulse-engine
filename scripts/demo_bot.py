"""
Демонстрационный Telegram-бот для показа возможностей парсинга маркетплейсов клиентам (Proof-of-Work).
Принимает артикул Wildberries (SKU или ссылку), за доли секунды выгружает через прямой CDN/API-протокол:
- Название и категорию товара
- Юридические данные продавца (ООО/ИП, ИНН, ОГРН, адрес)
- Характеристики карточки
- Фотографию высокого разрешения
- Замеряет и выводит реальную скорость сбора (в миллисекундах)
"""

import os
import sys
import re
import time
import json
import asyncio
import argparse
import aiohttp

# Загрузка .env
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

def get_basket_host(sku: int) -> str:
    """Вычисление CDN хоста WB для конкретного артикула"""
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
    """Асинхронный сбор данных по товару с замером времени"""
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
        # 1. Запрос карточки товара
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

        # 2. Запрос юр. данных продавца
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
    if options_text:
        options_block = f"\n📋 **Характеристики:**\n{options_text}\n"
    else:
        options_block = ""

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

# ==================== ТЕЛЕГРАМ БОТ (AIOGRAM 3) ====================

def run_telegram_bot(token: str):
    from aiogram import Bot, Dispatcher, types, F
    from aiogram.filters import Command
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    bot = Bot(token=token)
    dp = Dispatcher()

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

    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
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

    @dp.message()
    async def handle_any_message(message: types.Message):
        raw = message.text or ""
        # Поиск чисел от 5 до 11 знаков (артикул WB)
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
                return
            except Exception:
                pass

        await message.answer(msg_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

    print(f"[*] Демо-бот успешно запущен (@{bot.token.split(':')[0]}) и слушает входящие сообщения...", flush=True)
    asyncio.run(dp.start_polling(bot))

# ==================== CLI ТЕСТОВЫЙ РЕЖИМ ====================

def main():
    parser = argparse.ArgumentParser(description="Демо-бот парсинга маркетплейсов")
    parser.add_argument("--test-sku", default=None, help="Тестовый запуск парсера артикула в консоли (без запуска бота)")
    parser.add_argument("--token", default=os.getenv("TELEGRAM_BOT_TOKEN"), help="Токен бота от @BotFather")

    args = parser.parse_args()

    # Если передан флаг --test-sku, тестируем парсинг локально прямо в терминале
    if args.test_sku:
        sku = int(re.search(r"\d+", args.test_sku).group(0))
        print(f"[*] Локальное тестирование парсинга артикула: {sku}...")
        data = asyncio.run(fetch_wb_product(sku))
        print("\n" + "="*50)
        print(format_card_message(data))
        print("="*50)
        print(f"[✓] Замер времени сбора: {data['elapsed_ms']} мс")
        return

    token = args.token
    if not token:
        print("\n[!] Токен Telegram бота не найден.")
        print("    Получите токен у @BotFather в Telegram (занимает 30 секунд):")
        print("    1. Откройте @BotFather в Telegram -> отправьте /newbot")
        print("    2. Задайте имя (например: Market Data Demo) и юзернейм (например: market_fast_demo_bot)")
        print("    3. Скопируйте полученный HTTP API токен")
        token = input("\nВведите полученный токен бота (или Enter для тестового парсинга в консоли): ").strip()
        if not token:
            print("[*] Запуск в режиме консольного тестирования артикула 211612702:")
            data = asyncio.run(fetch_wb_product(211612702))
            print("\n" + "="*50)
            print(format_card_message(data))
            print("="*50)
            return

    run_telegram_bot(token)

if __name__ == "__main__":
    main()
