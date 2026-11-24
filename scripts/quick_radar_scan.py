"""
Quick Radar Scan - Снайперский пакетный сканер для GitHub Actions и Cron.
Выполняет быстрый опрос 15 целевых каналов за последние 25 минут,
фильтрует спам, находит прямые заказы и боли селлеров,
отправляет алерты с готовыми питчами в Telegram и завершает работу.
Время выполнения: ~15-25 секунд.
"""

import os
import sys
import re
import html
import asyncio
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient
from telethon.sessions import StringSession

# Load local .env if available
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
session_str = os.getenv("TG_SESSION_STRING", "").strip()
bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
admin_id = os.getenv("ADMIN_TG_ID", "1029387647").strip()

if not api_id or not api_hash:
    print("[ERROR] TG_API_ID or TG_API_HASH not set.")
    sys.exit(1)

TARGET_SELLER_CHATS = [
    "ozonhelpchat",
    "wildberries_chat_mp",
    "sellers_kaspi",
    "seller_uzum",
    "n8n_ru",
    "chat_wb_sellers",
    "sellerschatru",
    "wildberries_sellers_dnr_chat"
]

TARGET_FREELANCE_CHANNELS = [
    "zakazy_it",
    "progjob",
    "job_python",
    "freelance_chat_ru",
    "freelancetaverna",
    "it_freelance"
]

# Strict RegEx Filters
TIER1_PATTERNS = [
    re.compile(r"(?:нужен|ищу|требуется|найму|заказ(?:ать|чик)?)\b.{0,60}?\b(?:разработчик|программист|парсер|парс(?:инг|ить)|скрипт|бот|backend|бэкенд|c#|\.net|python|1с)\b", re.IGNORECASE),
    re.compile(r"\b(?:тз|бюджет)\b.{0,40}?\b(?:парсер|бот|скрипт|api|интеграц|выгрузк)\b", re.IGNORECASE),
    re.compile(r"\b(?:написать|разработать|создать|сделать)\b.{0,50}?\b(?:парсер|скрипт|бот[а-я]*|автопрайсер|чекер)\b", re.IGNORECASE),
    re.compile(r"\b(?:парсер|парс(?:инг|ить))\b.{0,40}?\b(?:wb|wildberries|вайлдберриз|ozon|озон|kaspi|каспи|под ключ|excel)\b", re.IGNORECASE),
    re.compile(r"\b(?:заказ|проект|задача)\b.{0,50}?\b(?:выгрузк[а-я]*\s+цен|мониторинг\s+цен|остатк[а-я]*\s+1с|слот[а-я]*\s+wb)\b", re.IGNORECASE)
]

TIER2_PATTERNS = [
    re.compile(r"\b(?:мониторинг|срез|отслежива(?:ть|ние)|сбор|парсинг)\b.{0,40}?\b(?:цен|остатков|скидок|спп|демпинг|конкурент)\b", re.IGNORECASE),
    re.compile(r"\b(?:слот|окно|приемк[а-я]*)\b.{0,40}?\b(?:коледино|электросталь|поймать|коэффициент|бот|чекер|автобронь)\b", re.IGNORECASE),
    re.compile(r"\b(?:1с|мойсклад|fbs|fbo)\b.{0,50}?\b(?:синхронизац|остатк|штраф|отмен[а-я]*\s+заказ|интеграц)\b", re.IGNORECASE),
    re.compile(r"\b(?:kaspi|каспи)\b.{0,50}?\b(?:демпинг|бот|парсер|автопрайсер|перебив(?:ает|ка))\b", re.IGNORECASE)
]

HARD_STOP_WORDS = [
    "уборка", "клининг", "квартир", "водитель", "курьер", "грузчик",
    "швеция", "стокгольм", "посудомой", "стройка", "ремонт квартир",
    "ищу работу", "ищу подработку", "резюме", "обо мне:", "обо мне :",
    "навыки:", "опыт работы:", "ищу вакансию", "рассмотрю предложения"
]

def is_hard_stop(text: str) -> bool:
    t_lower = text.lower()
    return any(sw in t_lower for sw in HARD_STOP_WORDS)

def check_message(text: str) -> tuple:
    if is_hard_stop(text):
        return None, None
    for pat in TIER1_PATTERNS:
        m = pat.search(text)
        if m:
            return "TIER1", m.group(0)
    for pat in TIER2_PATTERNS:
        m = pat.search(text)
        if m:
            return "TIER2", m.group(0)
    return None, None

def get_quick_response(category: str, chat_title: str) -> str:
    if category == "TIER1":
        return (
            "Привет! Готов качественно и быстро закрыть эту задачу.\n"
            "Senior Backend инженер (C#, .NET, Python). Сбор данных делаю на прямых API-запросах "
            "к CDN (170 мс на карточку, без медленных браузеров и риска капчи).\n"
            "Пример живой скорости: @stockpulse_demo_bot (скиньте любой артикул WB).\n"
            "Напишите мне в ЛС @horoshow88 — обсудим задачу, сделаю тестовый срез бесплатно."
        )
    else:
        return (
            "Привет! Увидел ваш вопрос в чате селлеров.\n"
            "Специализируюсь на надежном e-com бэкенде: мониторинг цен конкурентов до СПП, "
            "чекеры слотов складов (Коледино) и синхронизация остатков 1С ↔ WB/Ozon.\n"
            "Можете проверить скорость сбора в живом боте: @stockpulse_demo_bot\n"
            "Если задача еще актуальна — напишите в ЛС @horoshow88, сориентирую по решению."
        )

async def send_telegram_alert(alert_html: str):
    """Отправка уведомления через Bot API напрямую администратору"""
    if not bot_token or not admin_id:
        print("[WARN] bot_token or admin_id missing, cannot send push alert.")
        return
    import urllib.request
    import json
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": admin_id,
        "text": alert_html,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            pass
        print(f"[✓] Push alert delivered to admin {admin_id}")
    except Exception as e:
        print(f"[ERR] Failed to send push alert via bot: {e}")

async def run_scan():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Quick Radar Scan...")

    # Determine session method
    if session_str:
        session = StringSession(session_str)
        print("[+] Using StringSession from environment.")
    else:
        session_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "raw_data", "telegram_reader_session")
        session = session_file
        print(f"[+] Using local session file: {session_file}")

    client = TelegramClient(session, int(api_id), api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        print("[ERROR] Client is not authorized in Telegram!")
        await client.disconnect()
        sys.exit(1)

    print("[✓] Connected & Authorized. Scanning channels...")

    # Look back 25 minutes to overlap with 20-min cron
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=25)
    total_checked = 0
    total_leads = 0

    all_channels = TARGET_SELLER_CHATS + TARGET_FREELANCE_CHANNELS

    for ch_name in all_channels:
        try:
            entity = await client.get_entity(ch_name)
            chat_title = getattr(entity, 'title', ch_name)
            async for msg in client.iter_messages(entity, limit=30):
                if not msg.text:
                    continue
                if msg.date and msg.date < cutoff_time:
                    # Message is older than 25 minutes, stop scanning this channel
                    break

                total_checked += 1
                cat, trigger = check_message(msg.text)
                if cat:
                    total_leads += 1
                    sender_name = "Без имени"
                    sender_user = ""
                    try:
                        sender = await msg.get_sender()
                        if sender:
                            sender_name = f"{getattr(sender, 'first_name', '')} {getattr(sender, 'last_name', '')}".strip() or "Без имени"
                            sender_user = getattr(sender, 'username', '') or ""
                    except Exception:
                        pass

                    msg_link = f"https://t.me/{ch_name}/{msg.id}"
                    pitch = get_quick_response(cat, chat_title)
                    icon = "🔥 ПРЯМОЙ ЗАКАЗ" if cat == "TIER1" else "⚡ БОЛЬ СЕЛЛЕРА"

                    alert_html = (
                        f"<b>{icon} [GitHub Cron]</b>\n"
                        f"📍 <b>Источник:</b> {html.escape(chat_title)} (@{ch_name})\n"
                        f"👤 <b>Автор:</b> {html.escape(sender_name)} "
                        f"{'(@' + html.escape(sender_user) + ')' if sender_user else '(@без username)'}\n"
                        f"🎯 <b>Триггер:</b> <code>{html.escape(trigger)}</code>\n\n"
                        f"💬 <b>Сообщение:</b>\n"
                        f"«{html.escape(msg.text[:400])}»\n\n"
                        f"🔗 <a href=\"{msg_link}\">Перейти к сообщению в чате</a>\n\n"
                        f"📋 <b>Быстрый отклик (скопируйте):</b>\n"
                        f"<code>{html.escape(pitch)}</code>"
                    )

                    await send_telegram_alert(alert_html)
                    print(f"[{cat}] Found match in @{ch_name}! Trigger: {trigger}")
        except Exception as e:
            print(f"[!] Warning on channel @{ch_name}: {e}")

    print(f"\n[✓] Scan complete. Checked {total_checked} recent messages. Found {total_leads} leads.")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(run_scan())
