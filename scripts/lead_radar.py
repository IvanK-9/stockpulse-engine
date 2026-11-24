"""
Скрипт-Радар v2.1 (Снайперский режим с защитой от ложных срабатываний).
Работает через Telethon Event Listener в фоновом режиме.

Отфильтровывает:
- Бытовой шум (уборка, клининг, ремонт, водители, курьеры)
- Соискателей (резюме, «ищу работу»)
- Личные/эмигрантские диалоги (слушает СТРОГО целевые e-com и IT каналы)

Детектирует:
1. 🔴 ПРЯМЫЕ ЗАКАЗЫ (поиск разработчика/программиста, ТЗ, бюджеты, заказ ботов/парсеров)
2. 🟡 БОЛИ СЕЛЛЕРОВ (мониторинг цен, слоты складов, 1С остатки, демпинг Kaspi)

Отправляет Push-уведомление в @stockpulse_demo_bot и 'Избранное' с готовым 1-click ответом.
"""

import os
import sys
import json
import re
import html
import asyncio
import urllib.request
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat, User

# Загрузка .env
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

TARGET_SELLER_CHATS = [
    "sellers_chat",
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

# Точные регулярные выражения с лимитом расстояния между словами
TIER1_PATTERNS = [
    # Прямой поиск разрабов (строго IT специальности в пределах 4 слов)
    r"(?:ищу|ищем|нужен|нужна|нужно|нужны|требуется|посоветуйте|кто может|посоветуй|найму)(?:\s+\w+){0,4}\s+(?:разработчик|программист|бэкендер|кодер|парсерщик|1с-ник|1сник|скриптер)",
    # Человек / специалист, но СТРОГО с IT действием
    r"(?:нужен|ищу|требуется)(?:\s+\w+){0,3}\s+(?:человек|специалист)(?:,\s*|\s+)(?:который|кто)\s+(?:напишет|сделает|разработает|настроит|спарсит|подключит)",
    # Заказ парсера / бота / интеграции (в пределах 4 слов)
    r"(?:нужен|нужна|нужно|нужны|ищу|ищем|написать|сделать|заказать|купить|настроить)(?:\s+\w+){0,4}\s+(?:парсер|парсинг|скрипт|граббер|бот[а]?|автопрайсер|автобронь|интеграци[юи]|синхронизаци[юи])",
    # Действия по парсингу данных
    r"(?:спарсить|выгрузить|собрать|вытащить)(?:\s+\w+){0,4}\s+(?:цены|остатки|товары|базу|контакты|каталог|артикул)",
    # ТЗ и бюджеты в IT
    r"(?:тз|бюджет|оплата|проект)\s*[:—]\s*.*(?:парсер|бот|скрипт|разработк|python|c#|api)"
]

PAIN_PRICES_PATTERNS = [
    r"(?:как|где|чем|помогите)\s+.*(?:посмотреть|узнать|отследить|выгрузить|увидеть|рассчитать)\s+.*(?:цен[уаы]|стоимость|скидк[уаи]|юнитк[уаи])\s+.*(?:конкурент|вб|wb|озон|ozon)",
    r"(?:как|где)\s+.*(?:посмотреть|узнать|вытащить)\s+.*(?:цен[уаы]|стоимость)\s+.*без\s+скид",
    r"(?:мониторинг|отслеживание|сбор)\s+цен",
    r"(?:как|где)\s+(?:выгрузить|спарсить|вытащить)\s+.*(?:цены|отзывы|остатки|товары)"
]

PAIN_SLOTS_PATTERNS = [
    r"(?:не могу|не удается|не получается)\s+.*(?:поймать|забронировать|создать|открыть|поставить)\s+.*(?:слот|поставк|приемк|склад|коэффициент)",
    r"(?:нет|закончились|недоступны|недоступно)\s+.*(?:слот|коэффициент|приемк|мест)",
    r"(?:коледино|электросталь|чашниково|тула|подольск).*?(?:недоступн|забит|закрыт|нет мест)",
    r"(?:коэффициент|коэффициенты)\s+приемки\s+.*(?:х20|x20|бешеные|высокие|платн)",
    r"(?:ловля|поймать|автобронь|чекер)\s+.*слот"
]

PAIN_STOCK_PATTERNS = [
    r"(?:синхронизаци|связк|интеграци)\w*\s+.*(?:1с|1c|мойсклад|wb|ozon|вб|озон|каспи|kaspi)",
    r"(?:авто|автоматически)\s+.*(?:обновлять|синхронизировать|выгружать)\s+остатки",
    r"(?:штраф|списали|удержание)\s+.*(?:логистик|отмен|просрочк|габарит)"
]

PAIN_KASPI_PATTERNS = [
    r"(?:демпинг|автопрайсер|автоснижение|снизить цену на 10|байбокс|buybox|кнопк[ау]\s+купить)",
    r"(?:упали|просели|мало)\s+.*(?:заказы|продажи|показы)\s+.*(?:каспи|kaspi|вдвое|в двое)",
    r"рекламн(?:ый|ого)\s+бот[а]?"
]

STOP_WORDS = [
    "карго",
    "перевозки из китая",
    "выкуплю ваш товар",
    "ребята 16+",
    "дам возможность подработать",
    "даю по 500р",
    "вернуть страховку",
    "накрутка",
    "отзывы за выкуп",
    # Бытовые профессии и физический труд
    "уборк",
    "клининг",
    "ремонт квартир",
    "переводчик",
    "лингвист",
    "няня",
    "водитель",
    "грузчик",
    "маникюр",
    "курьер",
    "официант",
    "швея",
    "парикмахер",
    "повар",
    # Соискатели (отсекаем тех, кто сам ищет работу)
    "ищу работу",
    "ищет работу",
    "ищу подработку",
    "резюме"
]

def analyze_lead(text: str):
    t_lower = text.lower()
    if any(s in t_lower for s in STOP_WORDS):
        return None, None, None

    # 1. Прямой заказ
    for p in TIER1_PATTERNS:
        m = re.search(p, t_lower, re.DOTALL)
        if m:
            return "DIRECT", "🔴 ПРЯМОЙ ЗАКАЗ", m.group(0)

    # 2. Боли селлеров
    for p in PAIN_PRICES_PATTERNS:
        m = re.search(p, t_lower, re.DOTALL)
        if m:
            return "PAIN_PRICES", "🟡 БОЛЬ: ЦЕНЫ И ПАРСИНГ", m.group(0)

    for p in PAIN_SLOTS_PATTERNS:
        m = re.search(p, t_lower, re.DOTALL)
        if m:
            return "PAIN_SLOTS", "🟡 БОЛЬ: СЛОТЫ И СКЛАДЫ", m.group(0)

    for p in PAIN_STOCK_PATTERNS:
        m = re.search(p, t_lower, re.DOTALL)
        if m:
            return "PAIN_STOCK", "🟡 БОЛЬ: 1С И ОСТАТКИ", m.group(0)

    for p in PAIN_KASPI_PATTERNS:
        m = re.search(p, t_lower, re.DOTALL)
        if m:
            return "PAIN_KASPI", "🟡 БОЛЬ: KASPI ДЕМПИНГ", m.group(0)

    return None, None, None

def get_pitch(category: str) -> str:
    if category == "DIRECT":
        return (
            "Сделаю парсер/бота без Selenium: открытые CDN/API, 150–220 мс на карточку, история цен, база и Telegram-алерты.\n"
            "Уже есть рабочий пример: @stockpulse_demo_bot — разбирает карточки WB: цена, скидка, юнит-экономика, продавец/ИНН.\n"
            "Для вашей задачи могу показать первый результат на 10–20 артикулах за 24–48 часов. Оплата: 50% до старта, 50% после демонстрации. Могу начать сегодня."
        )
    elif category == "PAIN_PRICES":
        return (
            "Цену конкурента до скидки можно собирать напрямую через открытые источники, без Selenium и браузеров — поэтому решение не зависает и не ломается на объемах.\n"
            "У меня есть живой бот: карточка, цена, скидка, юнит-экономика и ИНН продавца приходят за 168–220 мс: @stockpulse_demo_bot.\n"
            "Могу за 24 часа сделать срез по вашей категории: до 30 конкурентов, Excel + короткий разбор. Стоимость 7 000 ₽. Если по вашей нише данные собрать нельзя — верну деньги. Интересно?"
        )
    elif category == "PAIN_SLOTS":
        return (
            "Ручной мониторинг складов обычно не успевает за изменением коэффициентов. Я делаю мониторинг нужных складов и свободных окон с алертом в Telegram.\n"
            "Для старта можно сделать простой мониторинг по вашему списку складов за 12 000–15 000 ₽, срок 1–2 дня. Могу сначала показать, как выглядит алерт."
        )
    elif category == "PAIN_STOCK":
        return (
            "Прежде чем строить интеграцию, полезно понять, где именно возникает расхождение: остатки, заказы, сроки сборки или статусы.\n"
            "Делаю экспресс-аудит за 5 000–8 000 ₽: список конкретных точек риска и рекомендации. Если проблема системная — потом можно собрать алерты и интеграцию."
        )
    elif category == "PAIN_KASPI":
        return (
            "По поводу просадки на Kaspi — скорее всего, конкуренты включили демпинг-ботов (перебивают цену на 10 тенге и забирают кнопку «Купить»).\n"
            "Могу настроить автопрайсер под ваш кабинет с защитой минимальной маржи. Напишите в ЛС @horoshow88."
        )
    return "Привет! Могу помочь решить эту задачу с гарантией результата. Напишите в ЛС @horoshow88."

async def main():
    session_path = rf"C:\Users\1v\.gemini\antigravity\scratch\freelance_market_research\raw_data\telegram_reader_session"
    leads_file = rf"C:\Users\1v\.gemini\antigravity\scratch\freelance_market_research\raw_data\leads_radar.json"

    api_id = int(os.getenv("TG_API_ID", 36838578))
    api_hash = str(os.getenv("TG_API_HASH", "3c52aa894a8288fdf4c2cd078da37707"))
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    client = TelegramClient(session_path, api_id, api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        print("[-] Сессия не авторизована.")
        return

    me = await client.get_me()
    print("=" * 65)
    print(f"[*] РАДАР ЛИДОВ v2.1 ЗАПУЩЕН | Аккаунт: {me.first_name} (@{me.username})")
    print("[*] Мониторинг строго целевых e-com сообществ и IT-бирж...")
    print("=" * 65, flush=True)

    monitored_entities = []

    # 1. Чаты селлеров (только целевые e-commerce)
    for username in TARGET_SELLER_CHATS:
        try:
            ent = await client.get_entity(username)
            if ent not in monitored_entities:
                monitored_entities.append(ent)
                print(f"  + Подключен e-com чат: {getattr(ent, 'title', username)} (@{username})")
        except Exception as e:
            print(f"  - Не удалось подключить @{username}: {e}")

    # 2. Каналы бирж заказов (только проверенные IT каналы)
    for username in TARGET_FREELANCE_CHANNELS:
        try:
            ent = await client.get_entity(username)
            if ent not in monitored_entities:
                monitored_entities.append(ent)
                print(f"  + Подключена IT биржа: {getattr(ent, 'title', username)} (@{username})")
        except Exception as e:
            print(f"  - Не удалось подключить @{username}: {e}")

    print(f"\n[✓] Всего целевых источников: {len(monitored_entities)}. Бытовые диалоги отключены. Ожидание...\n", flush=True)

    @client.on(events.NewMessage(chats=monitored_entities))
    async def handler(event):
        text = event.raw_text or ""
        if len(text.strip()) < 15:
            return

        cat_code, cat_title, matched_kw = analyze_lead(text)
        if not cat_code:
            return

        chat = await event.get_chat()
        chat_title = getattr(chat, 'title', 'Источник')
        chat_username = getattr(chat, 'username', None)

        sender = await event.get_sender()
        sender_name = "Аноним"
        sender_username = None
        if sender:
            f = getattr(sender, 'first_name', '') or ''
            l = getattr(sender, 'last_name', '') or ''
            sender_name = f"{f} {l}".strip() or "Без имени"
            sender_username = getattr(sender, 'username', None)

        if chat_username:
            msg_link = f"https://t.me/{chat_username}/{event.id}"
        else:
            msg_link = f"https://t.me/c/{chat.id}/{event.id}"

        now_str = datetime.now().strftime("%H:%M:%S")

        print("\n" + "🔥" * 25)
        print(f"[{cat_title}] {now_str}")
        print(f"📍 Чат: {chat_title} (@{chat_username})")
        print(f"👤 Автор: {sender_name} (@{sender_username})")
        print(f"🎯 Сработало: «{matched_kw}»")
        print(f"💬 Текст: {text[:250]}")
        print(f"🔗 Ссылка: {msg_link}")
        print("🔥" * 25 + "\n", flush=True)

        pitch = get_pitch(cat_code)

        alert_html = (
            f"<b>{cat_title}</b>\n\n"
            f"📍 <b>Источник:</b> {html.escape(chat_title)} (@{html.escape(chat_username or 'приватный')})\n"
            f"👤 <b>Автор:</b> {html.escape(sender_name)} (@{html.escape(sender_username or 'без username')})\n"
            f"🎯 <b>Триггер:</b> <code>{html.escape(matched_kw)}</code>\n\n"
            f"💬 <b>Сообщение:</b>\n<i>«{html.escape(text[:380])}»</i>\n\n"
            f"🔗 <a href='{msg_link}'>Перейти к сообщению в Telegram</a>\n\n"
            f"📋 <b>Быстрый ответ (нажмите, чтобы скопировать):</b>\n"
            f"<code>{html.escape(pitch)}</code>"
        )

        # Отправка через Bot API в @stockpulse_demo_bot
        if bot_token:
            try:
                api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                payload = json.dumps({
                    "chat_id": 1029387647,
                    "text": alert_html,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True
                }).encode("utf-8")
                req = urllib.request.Request(api_url, data=payload, headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=5)
            except Exception as e:
                print(f"[-] Ошибка отправки ботом: {e}")

        # Отправка в 'Saved Messages'
        try:
            await client.send_message("me", alert_html, parse_mode="html")
        except Exception as e:
            print(f"[-] Ошибка отправки в 'Избранное': {e}")

        # Сохранение в JSON
        lead_entry = {
            "timestamp": datetime.now().isoformat(),
            "category": cat_title,
            "chat_title": chat_title,
            "chat_username": chat_username,
            "sender_name": sender_name,
            "sender_username": sender_username,
            "matched_intent": matched_kw,
            "text": text,
            "msg_link": msg_link
        }

        leads_data = []
        if os.path.exists(leads_file):
            try:
                with open(leads_file, "r", encoding="utf-8") as f:
                    leads_data = json.load(f)
            except Exception:
                pass
        leads_data.append(lead_entry)
        with open(leads_file, "w", encoding="utf-8") as f:
            json.dump(leads_data, f, ensure_ascii=False, indent=2)

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
