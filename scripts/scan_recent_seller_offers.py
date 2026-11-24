import os
import sys
import json
import asyncio
from datetime import datetime
from telethon import TelegramClient

# Load .env
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

api_id = os.getenv("TG_API_ID")
api_hash = os.getenv("TG_API_HASH")
session_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "raw_data", "telegram_reader_session")

CHATS_TO_SCAN = [
    "ozonhelpchat",
    "wildberries_chat_mp",
    "chat_wb_sellers",
    "sellerschatru"
]

# Keywords that indicate service offers, promo, advertising, commercial proposals
PROMO_KEYWORDS = [
    "предлагаю", "услуг", "помогу", "под ключ", "настрою", "разработка", "дизайн",
    "инфографик", "продвижени", "сео", "seo", "честный знак", "фулфилмент", "склад",
    "доставка", "китай", "байер", "сертификат", "отзыв", "выкуп", "самовыкуп",
    "аудит", "оцифровк", "таблиц", "бот", "парсер", "скидк", "акци", "пишите в лс",
    "обращайтесь", "консультаци", "кейс", "результат"
]

async def scan():
    client = TelegramClient(session_path, int(api_id), api_hash)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("Error: Client not authorized.")
        return

    print("Connected to Telegram. Scanning recent seller chats for offers/proposals...")
    
    all_offers = []
    
    for chat_username in CHATS_TO_SCAN:
        print(f"\n--- Scanning @{chat_username} ---")
        try:
            entity = await client.get_entity(chat_username)
            count = 0
            found_offers = 0
            async for msg in client.iter_messages(entity, limit=80):
                if not msg.text:
                    continue
                count += 1
                text_lower = msg.text.lower()
                
                # Check if it has offer signals or is a substantial post
                is_offer = False
                matched_kw = []
                for kw in PROMO_KEYWORDS:
                    if kw in text_lower:
                        matched_kw.append(kw)
                
                # An offer usually has at least 1-2 keywords and more than 60 chars (not just "помогите")
                if len(matched_kw) >= 2 and len(msg.text) > 80 and not text_lower.startswith("подскажите") and not text_lower.startswith("кто знает"):
                    is_offer = True
                elif ("пишите в лс" in text_lower or "обращайтесь" in text_lower or "в личку" in text_lower) and len(msg.text) > 60:
                    is_offer = True
                
                if is_offer:
                    sender_name = "Unknown"
                    sender_username = ""
                    try:
                        sender = await msg.get_sender()
                        if sender:
                            sender_name = f"{getattr(sender, 'first_name', '')} {getattr(sender, 'last_name', '')}".strip()
                            sender_username = getattr(sender, 'username', '') or ""
                    except Exception:
                        pass
                    
                    offer_data = {
                        "chat": chat_username,
                        "msg_id": msg.id,
                        "date": msg.date.strftime("%Y-%m-%d %H:%M:%S") if msg.date else "",
                        "sender_name": sender_name,
                        "sender_username": sender_username,
                        "text": msg.text,
                        "matched_keywords": matched_kw
                    }
                    all_offers.append(offer_data)
                    found_offers += 1
            print(f"Checked {count} messages, found {found_offers} offers/proposals.")
        except Exception as e:
            print(f"Error scanning @{chat_username}: {e}")
            
    out_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "raw_data", "seller_chat_offers.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_offers, f, ensure_ascii=False, indent=2)
    print(f"\nTotal offers collected: {len(all_offers)}. Saved to {out_file}")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(scan())
