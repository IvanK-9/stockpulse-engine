"""
Парсер проектных заказов и вакансий с HeadHunter (hh.kz, hh.uz, hh.ru).
Поддерживает работу через REST API hh.ru и прямой HTML-парсинг выдачи с фильтром employment=project.
Извлекает: название, вилку оплаты, работодателя/заказчика, описание, локацию и прямую ссылку.
"""

import os
import sys
import json
import time
import re
import argparse

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import requests
import urllib3
urllib3.disable_warnings()
from bs4 import BeautifulSoup

DEFAULT_KEYWORDS = [
    "парсер",
    "парсер данных",
    "интеграция api",
    "kaspi api",
    "telegram бот",
    "wildberries ozon",
    "payme click",
    "backend c#",
    "backend python",
    "парсинг",
    "автоматизация",
    "zennoposter"
]

AREAS = {
    "kz": {"id": 40, "domain": "hh.kz", "name": "Казахстан"},
    "uz": {"id": 97, "domain": "hh.uz", "name": "Узбекистан"},
    "ru": {"id": 113, "domain": "hh.ru", "name": "Россия"}
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

def fetch_via_api(session: requests.Session, keyword: str, area_id: int, employment: str = "project", page: int = 0) -> list:
    url = "https://api.hh.ru/vacancies"
    params = {
        "text": keyword,
        "area": area_id,
        "employment": employment,
        "page": page,
        "per_page": 20
    }
    api_headers = {
        "User-Agent": "MarketResearchBot/1.0 (dev@freelance-audit.net)",
        "HH-User-Agent": "MarketResearchBot/1.0 (dev@freelance-audit.net)"
    }
    try:
        resp = session.get(url, params=params, headers=api_headers, timeout=8)
        if resp.status_code != 200:
            return None
        data = resp.json()
        results = []
        for item in data.get("items", []):
            salary = item.get("salary")
            salary_str = "По договоренности"
            if salary:
                f = salary.get("from")
                t = salary.get("to")
                c = salary.get("currency", "")
                if f and t:
                    salary_str = f"{f} - {t} {c}"
                elif f:
                    salary_str = f"от {f} {c}"
                elif t:
                    salary_str = f"до {t} {c}"
            snippet = item.get("snippet", {})
            results.append({
                "id": item.get("id"),
                "title": item.get("name"),
                "employer": (item.get("employer") or {}).get("name", "Не указан"),
                "salary": salary_str,
                "url": item.get("alternate_url"),
                "published_at": item.get("published_at"),
                "requirement": snippet.get("requirement", ""),
                "responsibility": snippet.get("responsibility", ""),
                "area": (item.get("area") or {}).get("name", ""),
                "source": "api.hh.ru"
            })
        return results
    except Exception:
        return None

def fetch_via_html(session: requests.Session, keyword: str, domain: str, employment: str = "project", page: int = 0) -> list:
    url = f"https://{domain}/search/vacancy"
    params = {
        "text": keyword,
        "page": page
    }
    if employment and employment != "all":
        params["employment"] = employment

    try:
        resp = session.get(url, params=params, headers=HEADERS, timeout=12, verify=False)
        if resp.status_code != 200:
            return []
        html = resp.text
    except Exception as e:
        print(f"[-] Ошибка загрузки {url}: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    results = []

    # Находим все ссылки на вакансии
    vacancy_links = soup.find_all("a", href=re.compile(r"/vacancy/\d+"))
    seen_ids = set()

    for a in vacancy_links:
        title = a.get_text(strip=True)
        raw_href = a.get("href", "")
        if not title or len(title) < 3:
            continue

        match = re.search(r"/vacancy/(\d+)", raw_href)
        if not match:
            continue
        v_id = match.group(1)
        if v_id in seen_ids:
            continue
        seen_ids.add(v_id)

        full_url = f"https://{domain}/vacancy/{v_id}"

        # Поднимаемся до карточки (контейнера)
        card = a.parent
        for _ in range(6):
            if card.parent and card.parent.name in ["div", "li"]:
                card = card.parent

        card_text = card.get_text(" | ", strip=True) if card else ""

        # Извлечение зарплаты
        salary = "По договоренности"
        sal_match = re.search(r"(\d[\d\s\xa0]{2,}\s*[–-]\s*\d[\d\s\xa0]{2,}\s*(?:₽|₸|so'm|USD|EUR|KZT|RUB|UZS))", card_text)
        if not sal_match:
            sal_match = re.search(r"((?:от|до)\s*\d[\d\s\xa0]{2,}\s*(?:₽|₸|so'm|USD|EUR|KZT|RUB|UZS))", card_text)
        if sal_match:
            salary = re.sub(r"\s+", " ", sal_match.group(1)).strip()

        # Извлечение работодателя
        employer = "Не указан"
        emp_match = re.search(r"(?:ИП\s+[\w\s]+|ТОО\s+[\w\s]+|ООО\s+[\w\s]+|[A-Za-z0-9\s]{3,30}(?:Inc|LLC|Group|Studio|Digital))", card_text)
        if emp_match:
            employer = emp_match.group(0).strip()

        results.append({
            "id": v_id,
            "title": title,
            "employer": employer,
            "salary": salary,
            "url": full_url,
            "snippet": card_text[:400],
            "domain": domain,
            "keyword": keyword,
            "source": f"html_{domain}"
        })

    return results

def main():
    parser = argparse.ArgumentParser(description="Сбор проектных заказов и вакансий с hh.kz/hh.uz")
    parser.add_argument("--countries", nargs="+", default=["kz", "uz"], help="kz, uz, ru")
    parser.add_argument("--keywords", nargs="+", default=DEFAULT_KEYWORDS, help="Ключевые слова")
    parser.add_argument("--employment", default="project", help="project, part, full, probe")
    parser.add_argument("--pages", type=int, default=2, help="Количество страниц на ключ")
    parser.add_argument("--output", default=r"C:\Users\1v\.gemini\antigravity\scratch\freelance_market_research\raw_data\hh_project_orders.json")
    args = parser.parse_args()

    session = requests.Session()
    all_records = []
    seen_urls = set()

    print(f"[*] Запуск сбора HH: страны={args.countries}, ключей={len(args.keywords)}, тип={args.employment}")

    for country in args.countries:
        meta = AREAS.get(country)
        if not meta:
            continue
        print(f"\n[+] Сбор данных по региону: {meta['name']} ({meta['domain']})")

        for kw in args.keywords:
            for page in range(args.pages):
                # 1. Попытка через API
                items = fetch_via_api(session, kw, meta["id"], args.employment, page)
                method = "API"

                # 2. Если API заблокирован или недоступен — парсим HTML
                if items is None:
                    method = "HTML"
                    items = fetch_via_html(session, kw, meta["domain"], args.employment, page)
                    time.sleep(1.0)

                if not items:
                    break

                new_count = 0
                for item in items:
                    u = item.get("url")
                    if u and u not in seen_urls:
                        seen_urls.add(u)
                        item["region_code"] = country
                        all_records.append(item)
                        new_count += 1

                print(f"  -> '{kw}' [Стр {page + 1} | {method}]: +{new_count} (всего {len(items)})")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    print(f"\n[✓] Готово! Собрано уникальных заказов/вакансий: {len(all_records)}")
    print(f"[✓] Файл сохранен: {args.output}")

if __name__ == "__main__":
    main()
