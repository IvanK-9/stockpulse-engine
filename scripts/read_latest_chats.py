import os
import sys
import json
from datetime import datetime, timezone
from telethon import TelegramClient

session_path = r"C:\Users\1v\.gemini\antigravity\scratch\freelance_market_research\raw_data\telegram_reader_session"
output_path = r"C:\Users\1v\.gemini\antigravity\scratch\freelance_market_research\raw_data\recent_chat_messages.json"

env_path = r"C:\Users\1v\.gemini\antigravity\scratch\freelance_market_research\.env"
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k.strip()] = v.strip()

api_id = int(os.getenv("TG_API_ID", 36838578))
api_hash = str(os.getenv("TG_API_HASH", "3c52aa894a8288fdf4c2cd078da37707"))

TARGETS = [
    {"name": "WB/Ozon Чат Шапкина", "username": "sellers_chat"},
    {"name": "WB Ozon Help", "username": "ozonhelpchat"},
    {"name": "Wildberries поставщики", "username": "wildberries_chat_mp"},
    {"name": "Kaspi Казахстан", "username": "sellers_kaspi"},
    {"name": "Uzum Узбекистан", "username": "seller_uzum"},
    {"name": "n8n сообщество", "username": "n8n_ru"},
    {"name": "Чат селлеров WB/Ozon", "username": "chat_wb_sellers"}
]

async def main():
    client = TelegramClient(session_path, api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        print("Not authorized")
        return

    all_data = {}
    print("Reading latest messages...")
    for t in TARGETS:
        try:
            ent = await client.get_entity(t["username"])
            messages = []
            async for msg in client.iter_messages(ent, limit=40):
                if msg.text and len(msg.text.strip()) > 10:
                    dt_str = msg.date.strftime("%Y-%m-%d %H:%M:%S") if msg.date else ""
                    messages.append({
                        "id": msg.id,
                        "date": dt_str,
                        "text": msg.text.strip()
                    })
            all_data[t["username"]] = {
                "name": t["name"],
                "count": len(messages),
                "messages": messages
            }
            print(f"[{t['name']}] collected {len(messages)} messages")
        except Exception as e:
            print(f"Error {t['username']}: {e}")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
