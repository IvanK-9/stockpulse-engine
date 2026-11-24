"""
Локальный парсер сохраненных вручную HTML-страниц защищенных площадок:
- Naimi.kz
- OLX.kz
- Profi.ru
- YouDo.com

Назначение: очистка от DOM-мусора (скрипты, стили, баннеры, трекеры) и извлечение
структурированных данных:
1. Заказы (заголовок, бюджет, описание задачи, отклики, категория)
2. Профили топовых исполнителей (имя/ник, рейтинг, количество отзывов, прайс, текст описания)
"""

import os
import sys
import glob
import json
import re
import argparse
from bs4 import BeautifulSoup, Comment

PLATFORM_PATTERNS = {
    "naimi": ["naimi.kz", "naimi-kz", "найми"],
    "olx": ["olx.kz", "olx-kz", "olx.ua", "olx.ru", "olx"],
    "profi": ["profi.ru", "профи.ру", "profi_ru", "profi"],
    "youdo": ["youdo.com", "юду", "youdo"]
}

def clean_soup(soup: BeautifulSoup) -> BeautifulSoup:
    """Удаляет скрипты, стили, svg, навигацию, футеры и служебный шум"""
    for tag in soup.find_all(["script", "style", "noscript", "svg", "nav", "footer", "iframe", "form"]):
        tag.decompose()
    for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
        comment.extract()
    return soup

def detect_platform(html_text: str, filename: str) -> str:
    name_lower = filename.lower()
    text_lower = html_text[:5000].lower()

    for p_name, patterns in PLATFORM_PATTERNS.items():
        if any(p in name_lower for p in patterns):
            return p_name
        if any(p in text_lower for p in patterns):
            return p_name

    return "generic"

# ==================== ПАРСЕРЫ ПЛОЩАДОК ====================

def parse_naimi(soup: BeautifulSoup) -> dict:
    """Разбор страниц Naimi.kz (заказы и анкеты специалистов)"""
    orders = []
    specialists = []

    # 1. Поиск заказов / заданий
    order_cards = soup.select("div[class*='order-card'], div[class*='request-card'], div[class*='task-card'], div[class*='OrderCard']")
    if not order_cards:
        order_cards = soup.find_all("div", attrs={"data-order-id": True})

    for card in order_cards:
        title_el = card.select_one("h2, h3, [class*='title'], [class*='Title']")
        price_el = card.select_one("[class*='price'], [class*='Price'], [class*='budget'], [class*='Budget']")
        desc_el = card.select_one("[class*='desc'], [class*='Desc'], [class*='text'], p")
        meta_el = card.select_one("[class*='meta'], [class*='date'], [class*='city']")

        title = title_el.get_text(strip=True) if title_el else ""
        price = price_el.get_text(strip=True) if price_el else "Договорная"
        desc = desc_el.get_text(" ", strip=True) if desc_el else ""
        meta = meta_el.get_text(" ", strip=True) if meta_el else ""

        if title or desc:
            orders.append({
                "type": "order",
                "title": title or desc[:60],
                "price": price,
                "description": desc,
                "meta": meta
            })

    # 2. Поиск анкет специалистов
    spec_cards = soup.select("div[class*='specialist-card'], div[class*='master-card'], div[class*='SpecialistCard']")
    for card in spec_cards:
        name_el = card.select_one("h2, h3, [class*='name'], [class*='Name']")
        rating_el = card.select_one("[class*='rating'], [class*='Rating'], [class*='stars']")
        reviews_el = card.select_one("[class*='review'], [class*='Review']")
        about_el = card.select_one("[class*='about'], [class*='desc'], [class*='bio'], p")
        price_el = card.select_one("[class*='price'], [class*='Price']")

        name = name_el.get_text(strip=True) if name_el else "Специалист"
        rating = rating_el.get_text(strip=True) if rating_el else ""
        reviews = reviews_el.get_text(strip=True) if reviews_el else ""
        about = about_el.get_text(" ", strip=True) if about_el else ""
        price = price_el.get_text(strip=True) if price_el else ""

        specialists.append({
            "type": "specialist",
            "name": name,
            "rating": rating,
            "reviews": reviews,
            "price": price,
            "about": about
        })

    return {"platform": "naimi.kz", "orders": orders, "specialists": specialists}

def parse_olx(soup: BeautifulSoup) -> dict:
    """Разбор объявлений OLX.kz"""
    listings = []
    cards = soup.select("div[data-cy='l-card'], div[class*='css-1sw7q4x'], div[data-testid='l-card']")
    if not cards:
        cards = soup.select("div.offer-wrapper, table.fixed")

    for card in cards:
        title_el = card.select_one("h4, h6, [data-cy='title'], a[href*='/d/obyavlenie/']")
        price_el = card.select_one("[data-cy='ad-price'], [data-testid='ad-price'], p[class*='price']")
        meta_el = card.select_one("[data-testid='location-date'], p[class*='location']")
        link_el = card.select_one("a[href*='/d/']")

        title = title_el.get_text(strip=True) if title_el else ""
        price = price_el.get_text(strip=True) if price_el else "Договорная"
        meta = meta_el.get_text(" ", strip=True) if meta_el else ""
        link = link_el.get("href", "") if link_el else ""

        if title:
            listings.append({
                "type": "listing",
                "title": title,
                "price": price,
                "meta": meta,
                "url": link
            })

    return {"platform": "olx.kz", "listings": listings}

def parse_profi(soup: BeautifulSoup) -> dict:
    """Разбор выдачи Profi.ru (специалисты и заказы)"""
    specialists = []
    orders = []

    # Карточки специалистов
    cards = soup.select("div[class*='ui-profile-card'], div[data-sh*='profile'], div[class*='desktop-profile']")
    if not cards:
        cards = soup.find_all("div", attrs={"data-qa": re.compile(r"profile-card|specialist")})

    for card in cards:
        name_el = card.select_one("h2, h3, a[class*='profile-title'], [data-qa*='profile-name']")
        rating_el = card.select_one("[class*='rating'], [data-qa*='rating']")
        reviews_el = card.select_one("[class*='review-count'], [data-qa*='reviews']")
        price_el = card.select_one("[class*='price'], [data-qa*='price']")
        about_el = card.select_one("[class*='about'], [class*='description'], p")

        name = name_el.get_text(strip=True) if name_el else "Мастер"
        rating = rating_el.get_text(strip=True) if rating_el else ""
        reviews = reviews_el.get_text(strip=True) if reviews_el else ""
        price = price_el.get_text(strip=True) if price_el else ""
        about = about_el.get_text(" ", strip=True) if about_el else ""

        specialists.append({
            "type": "specialist",
            "name": name,
            "rating": rating,
            "reviews": reviews,
            "price": price,
            "about": about
        })

    # Карточки заказов (если сохранена страница бэклога заказов)
    order_cards = soup.select("div[class*='order-item'], div[class*='task-item'], div[data-qa*='order']")
    for card in order_cards:
        title_el = card.select_one("h2, h3, a[class*='title']")
        price_el = card.select_one("[class*='price'], [class*='budget']")
        desc_el = card.select_one("[class*='desc'], p")

        title = title_el.get_text(strip=True) if title_el else ""
        price = price_el.get_text(strip=True) if price_el else "По договоренности"
        desc = desc_el.get_text(" ", strip=True) if desc_el else ""

        if title or desc:
            orders.append({
                "type": "order",
                "title": title or desc[:50],
                "price": price,
                "description": desc
            })

    return {"platform": "profi.ru", "specialists": specialists, "orders": orders}

def parse_youdo(soup: BeautifulSoup) -> dict:
    """Разбор задач и исполнителей YouDo"""
    tasks = []
    masters = []

    # Список задач
    task_cards = soup.select("li.b-tasks__item, div[class*='TasksList_item'], div.b-task-item")
    for card in task_cards:
        title_el = card.select_one("a.b-tasks__item__title, [class*='title'], h3")
        price_el = card.select_one("span.b-tasks__item__price, [class*='price']")
        desc_el = card.select_one("div.b-tasks__item__desc, [class*='description'], p")
        meta_el = card.select_one("div.b-tasks__item__info, [class*='info']")

        title = title_el.get_text(strip=True) if title_el else ""
        price = price_el.get_text(strip=True) if price_el else "Договорная"
        desc = desc_el.get_text(" ", strip=True) if desc_el else ""
        meta = meta_el.get_text(" ", strip=True) if meta_el else ""

        if title:
            tasks.append({
                "type": "order",
                "title": title,
                "price": price,
                "description": desc,
                "meta": meta
            })

    return {"platform": "youdo.com", "orders": tasks, "masters": masters}

def parse_generic(soup: BeautifulSoup) -> dict:
    """Универсальный парсер для любых сохраненных страниц"""
    headers = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"]) if len(h.get_text(strip=True)) > 5]
    prices = [p.get_text(strip=True) for p in soup.find_all(text=re.compile(r"(\d[\d\s]{2,}\s*(?:₸|₽|руб|\$|EUR|KZT))")) if len(p.strip()) < 30]
    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 20]

    return {
        "platform": "generic_html",
        "extracted_headers": headers[:30],
        "extracted_prices": list(set(prices))[:20],
        "sample_texts": paragraphs[:20]
    }

# ==================== ТОЧКА ВХОДА ====================

def process_file(filepath: str, platform_override: str = "auto") -> dict:
    print(f"\n[*] Обработка файла: {os.path.basename(filepath)}")
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        html_raw = f.read()

    soup = BeautifulSoup(html_raw, "html.parser")
    soup = clean_soup(soup)

    platform = platform_override if platform_override != "auto" else detect_platform(html_raw, filepath)
    print(f"  -> Определена платформа: {platform.upper()}")

    if platform == "naimi":
        data = parse_naimi(soup)
    elif platform == "olx":
        data = parse_olx(soup)
    elif platform == "profi":
        data = parse_profi(soup)
    elif platform == "youdo":
        data = parse_youdo(soup)
    else:
        data = parse_generic(soup)

    data["source_file"] = filepath
    return data

def main():
    parser = argparse.ArgumentParser(description="Локальный парсер HTML-дампов Naimi, OLX, Profi, YouDo")
    parser.add_argument("--input", default=None, help="Конкретный HTML файл для парсинга")
    parser.add_argument("--folder", default=r"C:\Users\1v\.gemini\antigravity\scratch\freelance_market_research\raw_data", help="Папка для пакетного сканирования")
    parser.add_argument("--platform", default="auto", choices=["auto", "naimi", "olx", "profi", "youdo"], help="Принудительный выбор платформы")
    parser.add_argument("--output", default=None, help="Путь для итогового JSON")

    args = parser.parse_args()

    files_to_process = []
    if args.input and os.path.isfile(args.input):
        files_to_process.append(args.input)
    else:
        pattern = os.path.join(args.folder, "*.htm*")
        files_to_process = glob.glob(pattern)

    if not files_to_process:
        print(f"[!] HTML файлы не найдены в {args.folder}.")
        print("    Сохраните нужные страницы из браузера (Ctrl+S -> 'Веб-страница, только HTML')")
        print(f"    в папку {args.folder} и запустите скрипт повторно:")
        print("    python scripts/parse_local_html.py")
        sys.exit(0)

    all_parsed = []
    for fpath in files_to_process:
        res = process_file(fpath, args.platform)
        all_parsed.append(res)

        # Вывод краткой сводки
        orders_cnt = len(res.get("orders", [])) + len(res.get("listings", []))
        specs_cnt = len(res.get("specialists", [])) + len(res.get("masters", []))
        print(f"     Найдено заказов/объявлений: {orders_cnt}, анкет исполнителей: {specs_cnt}")

    out_file = args.output or os.path.join(args.folder, "parsed_local_html_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_parsed, f, ensure_ascii=False, indent=2)

    print(f"\n[✓] Обработка завершена. Результаты сохранены в: {out_file}")

if __name__ == "__main__":
    main()
