"""
Скрипт сбора заказов, задач на разработку и коммерческих предложений с открытых форумов:
1. ZennoLab Forum (поиск и предложение услуг по созданию шаблонов / автоматизации)
2. Searchengines.guru (раздел 'Программы и скрипты' и 'Работа и услуги для вебмастера')
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

FORUMS = [
    {
        "name": "ZennoLab (Шаблоны / Заказы)",
        "url_template": "https://zennolab.com/discussion/forums/poisk-i-predlozhenie-uslug-po-sozdaniju-shablonov.213/page-{page}",
        "first_page": "https://zennolab.com/discussion/forums/poisk-i-predlozhenie-uslug-po-sozdaniju-shablonov.213/",
        "base_url": "https://zennolab.com",
        "type": "zennolab",
        "pages": 3
    },
    {
        "name": "Searchengines.guru (Программы и скрипты)",
        "url_template": "https://searchengines.guru/ru/forum/optimizators-exchange/programs-scripts/page{page}",
        "first_page": "https://searchengines.guru/ru/forum/optimizators-exchange/programs-scripts",
        "base_url": "https://searchengines.guru",
        "type": "searchengines",
        "pages": 3
    },
    {
        "name": "Searchengines.guru (Работа для вебмастера)",
        "url_template": "https://searchengines.guru/ru/forum/webmasters-jobs/page{page}",
        "first_page": "https://searchengines.guru/ru/forum/webmasters-jobs",
        "base_url": "https://searchengines.guru",
        "type": "searchengines",
        "pages": 2
    }
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def parse_zennolab(html: str, base_url: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    threads = soup.find_all("div", class_=re.compile(r"structItem--thread"))

    for t in threads:
        title_block = t.find("div", class_="structItem-title")
        if not title_block:
            continue

        a_tags = title_block.find_all("a", href=re.compile(r"/threads/"))
        if not a_tags:
            continue
        title_a = a_tags[-1]
        title = title_a.get_text(strip=True)
        link = title_a.get("href", "")
        if link.startswith("/"):
            link = f"{base_url}{link}"

        # Префикс темы (например: [Заказ шаблона], [Услуга])
        prefix = ""
        prefix_el = title_block.find("span", class_=re.compile(r"label"))
        if prefix_el:
            prefix = prefix_el.get_text(strip=True)

        author_el = t.find("a", class_="username")
        author = author_el.get_text(strip=True) if author_el else "Аноним"

        date_el = t.find("time")
        date_str = date_el.get("datetime") if date_el else (date_el.get_text(strip=True) if date_el else "")

        meta_stats = t.find("div", class_="structItem-cell--meta")
        replies_views = meta_stats.get_text(" ", strip=True) if meta_stats else ""

        items.append({
            "source": "zennolab",
            "title": f"{prefix} {title}".strip(),
            "url": link,
            "author": author,
            "date": date_str,
            "stats": replies_views,
            "type": "order" if "заказ" in title.lower() or "требуется" in title.lower() or "ищу" in title.lower() else "service"
        })
    return items

def parse_searchengines(html: str, base_url: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    # Находим все ссылки на топики
    for a in soup.find_all("a", href=re.compile(r"^/ru/forum/\d+$")):
        title = a.get_text(strip=True)
        if not title or title.isdigit() or len(title) < 6:
            continue

        link = f"{base_url}{a['href']}"

        # Контейнер темы
        parent = a.parent
        for _ in range(4):
            if parent.parent and parent.parent.name in ["div", "li", "tr"]:
                parent = parent.parent

        snippet = parent.get_text(" | ", strip=True) if parent else ""

        items.append({
            "source": "searchengines",
            "title": title,
            "url": link,
            "snippet": snippet[:300],
            "type": "order" if any(w in title.lower() for w in ["ищу", "требуется", "заказ", "нужен"]) else "service_offer"
        })
    return items

def main():
    parser = argparse.ArgumentParser(description="Парсер открытых форумов по парсингу и автоматизации")
    parser.add_argument("--output", default=r"C:\Users\1v\.gemini\antigravity\scratch\freelance_market_research\raw_data\forums_orders_dump.json")
    args = parser.parse_args()

    session = requests.Session()
    all_results = []
    seen_urls = set()

    for forum in FORUMS:
        print(f"\n[*] Сбор с форума: {forum['name']}")
        forum_session = requests.Session()
        if forum["type"] == "searchengines":
            forum_session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            })
        else:
            forum_session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            })
        max_p = forum.get("pages", 2)
        for page in range(1, max_p + 1):
            if page == 1 and "first_page" in forum:
                url = forum["first_page"]
            else:
                url = forum["url_template"].format(page=page)
            print(f"  -> Загрузка стр {page}: {url}")
            try:
                resp = forum_session.get(url, timeout=12)
                if resp.status_code != 200:
                    print(f"     [-] Код ответа: {resp.status_code}")
                    continue
                html = resp.text
            except Exception as e:
                print(f"     [-] Ошибка: {e}")
                continue

            if forum["type"] == "zennolab":
                items = parse_zennolab(html, forum["base_url"])
            else:
                items = parse_searchengines(html, forum["base_url"])

            new_cnt = 0
            for it in items:
                u = it.get("url")
                if u and u not in seen_urls:
                    seen_urls.add(u)
                    all_results.append(it)
                    new_cnt += 1

            print(f"     [+] Собрано на странице: {len(items)}, новых: {new_cnt}")
            time.sleep(1.0)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n[✓] Готово! Всего собрано тем с форумов: {len(all_results)}")
    print(f"[✓] Данные сохранены в: {args.output}")

if __name__ == "__main__":
    main()
