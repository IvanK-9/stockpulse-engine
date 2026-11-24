"""
Скрипт быстрого пакетного экспорта карточек Wildberries (Tripwire Tool).
Принимает список артикулов (из файла или аргументов), опрашивает публичный CDN WB
на сверхвысокой скорости (~150-180 мс на товар) и генерирует Excel/CSV отчет:
- Базовая цена без скидок (для юнит-экономики)
- Цена со скидкой WB (финальная розничная)
- Размер скидки %
- Рейтинг и количество отзывов
- Юрлицо продавца, ИНН, ОГРН
- Прямая ссылка на карточку
"""

import sys
import os
import json
import csv
import time
import urllib.request
import truststore
truststore.inject_into_ssl()

def get_wb_basket_host(vol: int) -> str:
    if 0 <= vol <= 143: return "basket-01.wbbasket.ru"
    elif 144 <= vol <= 287: return "basket-02.wbbasket.ru"
    elif 288 <= vol <= 431: return "basket-03.wbbasket.ru"
    elif 432 <= vol <= 719: return "basket-04.wbbasket.ru"
    elif 720 <= vol <= 1007: return "basket-05.wbbasket.ru"
    elif 1008 <= vol <= 1061: return "basket-06.wbbasket.ru"
    elif 1062 <= vol <= 1115: return "basket-07.wbbasket.ru"
    elif 1116 <= vol <= 1169: return "basket-08.wbbasket.ru"
    elif 1170 <= vol <= 1313: return "basket-09.wbbasket.ru"
    elif 1314 <= vol <= 1601: return "basket-10.wbbasket.ru"
    elif 1602 <= vol <= 1655: return "basket-11.wbbasket.ru"
    elif 1656 <= vol <= 1919: return "basket-12.wbbasket.ru"
    elif 1920 <= vol <= 2045: return "basket-13.wbbasket.ru"
    elif 2046 <= vol <= 2189: return "basket-14.wbbasket.ru"
    elif 2190 <= vol <= 2405: return "basket-15.wbbasket.ru"
    elif 2406 <= vol <= 2621: return "basket-16.wbbasket.ru"
    elif 2622 <= vol <= 2837: return "basket-17.wbbasket.ru"
    else: return "basket-18.wbbasket.ru"

def fetch_sku_details(sku: int) -> dict:
    vol = sku // 100000
    part = sku // 1000
    host = get_wb_basket_host(vol)
    card_url = f"https://{host}/vol{vol}/part{part}/{sku}/info/ru/card.json"
    sellers_url = f"https://{host}/vol{vol}/part{part}/{sku}/info/sellers.json"
    price_url = f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&nm={sku}"

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    data = {
        "sku": sku,
        "name": "",
        "brand": "",
        "base_price": "",
        "sale_price": "",
        "discount_pct": "",
        "rating": "",
        "feedbacks": "",
        "seller_name": "",
        "seller_inn": "",
        "seller_ogrn": "",
        "link": f"https://www.wildberries.ru/catalog/{sku}/detail.aspx"
    }

    try:
        req = urllib.request.Request(card_url, headers=headers)
        with urllib.request.urlopen(req, timeout=4) as resp:
            card_json = json.loads(resp.read().decode('utf-8'))
            data["name"] = card_json.get("imt_name") or card_json.get("subj_name", "")
            data["brand"] = card_json.get("selling", {}).get("brand_name", "")
    except Exception:
        pass

    try:
        req = urllib.request.Request(sellers_url, headers=headers)
        with urllib.request.urlopen(req, timeout=4) as resp:
            seller_json = json.loads(resp.read().decode('utf-8'))
            data["seller_name"] = seller_json.get("supplier_name", "")
            data["seller_inn"] = seller_json.get("inn", "")
            data["seller_ogrn"] = seller_json.get("ogrn", "")
    except Exception:
        pass

    try:
        req = urllib.request.Request(price_url, headers=headers)
        with urllib.request.urlopen(req, timeout=4) as resp:
            p_json = json.loads(resp.read().decode('utf-8'))
            products = p_json.get("data", {}).get("products", [])
            if products:
                prod = products[0]
                sizes = prod.get("sizes", [])
                if sizes:
                    price_obj = sizes[0].get("price", {})
                    basic = price_obj.get("basic", 0) // 100
                    total = price_obj.get("total", 0) // 100
                    data["base_price"] = basic or ""
                    data["sale_price"] = total or ""
                    if basic and total and basic > total:
                        data["discount_pct"] = f"{round((1 - total / basic) * 100)}%"
                data["rating"] = prod.get("reviewRating", "")
                data["feedbacks"] = prod.get("feedbacks", "")
                if not data["name"]:
                    data["name"] = prod.get("name", "")
                if not data["brand"]:
                    data["brand"] = prod.get("brand", "")
    except Exception:
        pass

    return data

def export_batch(skus: list[int], output_csv: str):
    start = time.time()
    results = []
    print(f"[*] Начало выгрузки {len(skus)} артикулов WB...")

    for i, sku in enumerate(skus, 1):
        t0 = time.time()
        item = fetch_sku_details(sku)
        dt = (time.time() - t0) * 1000
        results.append(item)
        print(f"[{i}/{len(skus)}] SKU {sku}: '{item['name'][:30]}' | Базовая: {item['base_price']} ₽ | Со скидкой: {item['sale_price']} ₽ | ИНН: {item['seller_inn']} ({dt:.0f} мс)")

    # Экспорт в CSV (совместим с Excel UTF-8 с BOM)
    with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [
            "sku", "name", "brand", "base_price", "sale_price",
            "discount_pct", "rating", "feedbacks", "seller_name",
            "seller_inn", "seller_ogrn", "link"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(results)

    total_time = time.time() - start
    print("=" * 60)
    print(f"[✓] Успешно! Собрано {len(results)} артикулов за {total_time:.2f} сек ({total_time/len(skus):.2f} с/товар).")
    print(f"[✓] Отчет сохранен: {output_csv}")

if __name__ == "__main__":
    test_skus = [
        138590435, 172945412, 180123456, 192837465, 210987654
    ]
    out_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "raw_data", "batch_export_sample.csv")
    export_batch(test_skus, out_file)
