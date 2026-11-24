"""
Автоматизированный скрипт для сбора болей и задач из Telegram-сообществ (Kaspi, WB/Ozon, Uzum, n8n).
Использует Telethon в режиме 'только чтение' (Read-Only).
Поддерживает пакетный авто-режим (--auto) по проверенным открытым чатам селлеров.
"""

import os
import sys
import json
import re
import asyncio
import argparse
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.types import Channel, Chat, User
from telethon.tl.functions.contacts import SearchRequest
from telethon.errors import FloodWaitError

# Автоматическая загрузка .env
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

DEFAULT_KEYWORDS = [
    "парсер",
    "парсинг",
    "бот",
    "интеграция",
    "api",
    "kaspi",
    "uzum",
    "wildberries",
    "ozon",
    "wb",
    "n8n",
    "make",
    "crm",
    "1c",
    "1с",
    "click",
    "payme",
    "выгрузка",
    "синхронизация",
    "остатки",
    "цены",
    "скрипт",
    "автоматизация",
    "слот",
    "штраф",
    "разработчик"
]

VERIFIED_TARGETS = [
    {"name": "Kaspi (Казахстан)", "chat": "sellers_kaspi"},
    {"name": "Wildberries поставщики", "chat": "wildberries_chat_mp"},
    {"name": "Uzum Market (Узбекистан)", "chat": "seller_uzum"},
    {"name": "n8n / Автоматизация", "chat": "n8n_ru"}
]

async def get_authenticated_client(api_id: int, api_hash: str, phone: str, session_path: str) -> TelegramClient:
    client = TelegramClient(session_path, api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        print("[*] Требуется первичная авторизация...")
        if phone:
            await client.start(phone=phone)
        else:
            await client.start()
    return client

async def list_my_chats(client: TelegramClient):
    print("\n[*] Ваши активные группы и каналы:")
    count = 0
    async for dialog in client.iter_dialogs(limit=30):
        if dialog.is_group or dialog.is_channel:
            count += 1
            username = f"@{dialog.entity.username}" if getattr(dialog.entity, "username", None) else "(приватный чат)"
            print(f"  {count}. {dialog.title} -> {username} | ID: {dialog.id}")

async def search_public_chats(client: TelegramClient, query: str):
    print(f"\n[*] Глобальный поиск открытых чатов по запросу: '{query}'...")
    res = await client(SearchRequest(q=query, limit=10))
    if not res.chats:
        print("  [-] Ничего не найдено.")
        return []
    found = []
    for i, c in enumerate(res.chats, 1):
        username = getattr(c, "username", None)
        title = getattr(c, "title", "Без названия")
        if username:
            print(f"  {i}. {title} -> @{username}")
            found.append(username)
    return found

async def dump_single_chat(client: TelegramClient, chat_target: str, limit: int, keywords: list, output_file: str):
    clean_target = chat_target.replace("@", "").strip()
    try:
        entity = await client.get_entity(clean_target)
        title = getattr(entity, 'title', clean_target)
        print(f"\n[+] Подключение к чату: '{title}' (@{clean_target})")
    except Exception as e:
        print(f"[-] Не удалось открыть чат '{clean_target}': {e}")
        return None

    print(f"[*] Сбор последних {limit} сообщений и фильтрация по {len(keywords)} ключевым словам...")
    messages_data = []
    scanned_count = 0
    matched_count = 0
    lower_keywords = [k.lower() for k in keywords]

    try:
        async for msg in client.iter_messages(entity, limit=limit):
            scanned_count += 1
            text = msg.raw_text or ""
            if not text:
                continue

            t_lower = text.lower()
            matched_tags = [kw for kw in lower_keywords if kw in t_lower]

            if matched_tags or not lower_keywords:
                matched_count += 1
                sender = await msg.get_sender()
                sender_name = "Аноним"
                sender_username = None
                if sender:
                    first = getattr(sender, 'first_name', '') or ''
                    last = getattr(sender, 'last_name', '') or ''
                    sender_name = f"{first} {last}".strip() or "Без имени"
                    sender_username = getattr(sender, 'username', None)

                messages_data.append({
                    "id": msg.id,
                    "date": msg.date.isoformat() if msg.date else None,
                    "sender_id": msg.sender_id,
                    "sender_name": sender_name,
                    "sender_username": sender_username,
                    "text": text,
                    "views": msg.views,
                    "matched_keywords": matched_tags
                })

    except FloodWaitError as e:
        print(f"[!] Лимит Telegram. Ожидание {e.seconds} сек...")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        print(f"[-] Ошибка во время чтения: {e}")

    result = {
        "target": clean_target,
        "title": title,
        "scanned_total": scanned_count,
        "matched_total": matched_count,
        "dump_date": datetime.now().isoformat(),
        "messages": messages_data
    }

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[✓] Проверено: {scanned_count} сообщений. Найдено болей/задач: {matched_count}.")
    print(f"[✓] Файл сохранен: {output_file}")
    return result

async def run_pipeline(args):
    session_path = rf"C:\Users\1v\.gemini\antigravity\scratch\freelance_market_research\raw_data\telegram_reader_session"
    raw_dir = os.path.dirname(session_path)

    api_id = int(args.api_id or os.getenv("TG_API_ID", 36838578))
    api_hash = str(args.api_hash or os.getenv("TG_API_HASH", "3c52aa894a8288fdf4c2cd078da37707"))
    phone = str(args.phone or os.getenv("TG_PHONE", "+46761718482"))

    client = await get_authenticated_client(api_id, api_hash, phone, session_path)

    # Режим просмотра своих групп
    if args.list:
        await list_my_chats(client)
        await client.disconnect()
        return

    # Режим поиска открытых групп
    if args.search:
        await search_public_chats(client, args.search)
        await client.disconnect()
        return

    # Режим авто-сбора по проверенным чатам селлеров
    if args.auto:
        print("\n" + "="*60)
        print("[*] ЗАПУСК АВТОМАТИЧЕСКОГО СБОРА ПО ВСЕМ КЛЮЧЕВЫМ СООБЩЕСТВАМ")
        print("="*60)
        for item in VERIFIED_TARGETS:
            out_file = os.path.join(raw_dir, f"telegram_{item['chat']}.json")
            print(f"\n>>> Площадка: {item['name']} (чат: @{item['chat']})")
            await dump_single_chat(client, item['chat'], args.limit, args.keywords, out_file)
            await asyncio.sleep(1.5)
        print("\n[✓] Автоматический сбор по всем чатам завершен!")
        await client.disconnect()
        return

    # Одиночный сбор
    target = args.chat
    if not target:
        user_input = input("Введите юзернейм/ссылку чата (или 'auto' для сбора всех селлеров): ").strip()
        if user_input.lower() == "auto":
            args.auto = True
            await client.disconnect()
            await run_pipeline(args)
            return
        target = user_input if user_input else "sellers_kaspi"

    out_file = args.output or os.path.join(raw_dir, f"telegram_{target.replace('@', '')}.json")
    await dump_single_chat(client, target, args.limit, args.keywords, out_file)
    await client.disconnect()

def main():
    parser = argparse.ArgumentParser(description="Автоматический дамп сообщений из Telegram-чатов")
    parser.add_argument("--auto", action="store_true", help="Автоматический сбор по всем ключевым сообществам (Kaspi, WB, Uzum, n8n)")
    parser.add_argument("--list", action="store_true", help="Показать список ваших чатов")
    parser.add_argument("--search", default=None, help="Глобальный поиск открытых чатов по слову (например: --search kaspi)")
    parser.add_argument("--chat", default=None, help="Юзернейм или ссылка конкретного чата")
    parser.add_argument("--limit", type=int, default=500, help="Лимит сообщений на чат (по умолчанию 500)")
    parser.add_argument("--keywords", nargs="+", default=DEFAULT_KEYWORDS, help="Ключевые слова")
    parser.add_argument("--output", default=None, help="Выходной файл")
    parser.add_argument("--api-id", default=None)
    parser.add_argument("--api-hash", default=None)
    parser.add_argument("--phone", default=None)

    args = parser.parse_args()
    asyncio.run(run_pipeline(args))

if __name__ == "__main__":
    main()
