from PIL import Image, ImageDraw, ImageFont
import os

width, height = 1200, 900
image = Image.new("RGB", (width, height), color=(9, 13, 26))
draw = ImageDraw.Draw(image)

font_dir = "C:\\Windows\\Fonts"
f_badge = ImageFont.truetype(os.path.join(font_dir, "segoeuib.ttf"), 14)
f_tag = ImageFont.truetype(os.path.join(font_dir, "segoeuib.ttf"), 12)
f_h1 = ImageFont.truetype(os.path.join(font_dir, "segoeuib.ttf"), 40)
f_sub = ImageFont.truetype(os.path.join(font_dir, "segoeuib.ttf"), 20)
f_big_stat = ImageFont.truetype(os.path.join(font_dir, "segoeuib.ttf"), 64)
f_card_title = ImageFont.truetype(os.path.join(font_dir, "segoeuib.ttf"), 18)
f_card_body = ImageFont.truetype(os.path.join(font_dir, "segoeui.ttf"), 14)
f_card_body_b = ImageFont.truetype(os.path.join(font_dir, "segoeuib.ttf"), 14)
f_code = ImageFont.truetype(os.path.join(font_dir, "consola.ttf"), 15)
f_code_title = ImageFont.truetype(os.path.join(font_dir, "consola.ttf"), 13)
f_cta_h = ImageFont.truetype(os.path.join(font_dir, "segoeuib.ttf"), 20)
f_cta_p = ImageFont.truetype(os.path.join(font_dir, "segoeui.ttf"), 15)
f_btn = ImageFont.truetype(os.path.join(font_dir, "segoeuib.ttf"), 16)
f_footer = ImageFont.truetype(os.path.join(font_dir, "segoeuib.ttf"), 15)

# Outer frame
draw.rounded_rectangle([(25, 25), (width - 25, height - 25)], radius=20, outline=(30, 41, 59), width=2)
# Inner canvas
draw.rounded_rectangle([(40, 40), (width - 40, height - 40)], radius=16, fill=(13, 19, 33))

# ----------------- 1. HEADER -----------------
# Status pill
draw.rounded_rectangle([(65, 60), (410, 92)], radius=8, fill=(6, 44, 33), outline=(16, 185, 129), width=1)
draw.ellipse([(80, 72), (88, 80)], fill=(52, 211, 153))
draw.text((98, 66), "SYSTEM ONLINE • 99.98% HIGH AVAILABILITY", fill=(52, 211, 153), font=f_badge)

# H1 Headline
draw.text((65, 108), "ПРОМЫШЛЕННЫЙ БЭКЕНД ДЛЯ E-COMMERCE", fill=(255, 255, 255), font=f_h1)
# Subtitle
draw.text((65, 164), "Скорость 170 мс  |  Нулевые штрафы  |  Автоматизация Wildberries, Ozon, Kaspi", fill=(56, 189, 248), font=f_sub)

# ----------------- 2. HERO ROW (2 COLUMNS) -----------------
# Left Card: 168 ms Hero
draw.rounded_rectangle([(65, 215), (475, 455)], radius=14, fill=(17, 24, 39), outline=(16, 185, 129), width=2)

# Tag in left card with exact text bbox
tag_text = "СКОРОСТЬ ОБРАБОТКИ"
tb = f_tag.getbbox(tag_text)
tw = tb[2] - tb[0]
draw.rounded_rectangle([(90, 235), (90 + tw + 20, 259)], radius=5, fill=(6, 44, 33))
draw.text((100, 239), tag_text, fill=(52, 211, 153), font=f_tag)

draw.text((90, 265), "168 мс", fill=(52, 211, 153), font=f_big_stat)

# Divider
draw.line([(90, 355), (450, 355)], fill=(30, 41, 59), width=1)

# Bullet points in left card
bullets_left = [
    ("Прямой опрос API каталога (без браузера)", False),
    ("Стабильная работа без зависаний и падений", False),
    ("1 000 артикулов за 3 минуты сразу в Excel", True)
]
by = 370
for btext, is_bold in bullets_left:
    draw.ellipse([(90, by + 6), (96, by + 12)], fill=(52, 211, 153) if is_bold else (56, 189, 248))
    f = f_card_body_b if is_bold else f_card_body
    col = (255, 255, 255) if is_bold else (203, 213, 225)
    draw.text((106, by), btext, fill=col, font=f)
    by += 24

# Right Card: Terminal Window
draw.rounded_rectangle([(495, 215), (1135, 455)], radius=14, fill=(7, 10, 19), outline=(51, 65, 85), width=1)
# Terminal title bar
draw.rounded_rectangle([(495, 215), (1135, 255)], radius=14, fill=(15, 23, 42))
draw.rectangle([(495, 240), (1135, 255)], fill=(15, 23, 42))
draw.line([(495, 255), (1135, 255)], fill=(51, 65, 85), width=1)

# Window dots
draw.ellipse([(515, 230), (525, 240)], fill=(239, 68, 68))
draw.ellipse([(533, 230), (543, 240)], fill=(245, 158, 11))
draw.ellipse([(551, 230), (561, 240)], fill=(16, 185, 129))
draw.text((580, 227), "stockpulse-engine :: direct-catalog-stream.log", fill=(148, 163, 184), font=f_code_title)

# Terminal body
code_lines = [
    ("> GET /vol1385/part138590/card.json HTTP/2", (148, 163, 184)),
    ("< 200 OK [168ms] payload: 42.8 KB (Catalog API)", (52, 211, 153)),
    ("> BasePrice: 3 900 RUB  [Юнит-экономика до акций]", (56, 189, 248)),
    ("> DiscountPrice: 1 890 RUB  [СПП маркетплейса]", (56, 189, 248)),
    ("> MarginCalculation: 28.4%  [Чистая прибыль после тарифов]", (203, 213, 225)),
    ("STATUS: 1 000 SKU успешно выгружено в Excel", (52, 211, 153))
]
cy = 270
for cline, col in code_lines:
    draw.text((515, cy), cline, fill=col, font=f_code)
    cy += 27

# ----------------- 3. FEATURES ROW (3 CARDS) -----------------
feature_cards = [
    {
        "tag": "FBS / FBO",
        "tag_bg": (30, 41, 59),
        "tag_fg": (56, 189, 248),
        "title": "ЗАЩИТА ОТ ШТРАФОВ",
        "items": [
            "Синхронизация 1С и WB за 15 секунд",
            "Автообнуление пустых остатков",
            "Исключение отмен и падения рейтинга"
        ]
    },
    {
        "tag": "ЛОГИСТИКА",
        "tag_bg": (6, 44, 33),
        "tag_fg": (52, 211, 153),
        "title": "АВТОБРОНЬ СЛОТОВ",
        "items": [
            "Чекер Коледино / Электросталь",
            "Ловля бесплатных коэф. x1 / x0",
            "Мгновенный пуш в Telegram-бот"
        ]
    },
    {
        "tag": "АНАЛИТИКА",
        "tag_bg": (45, 26, 10),
        "tag_fg": (251, 191, 36),
        "title": "РАСЧЕТ ЦЕН ЗА 24 ЧАСА",
        "items": [
            "30 позиций в чистом Excel файле",
            "Реальные цены до акций и СПП",
            "Готовый расчет маржинальности"
        ]
    }
]

cx = 65
cw = 340
ch = 150
gap = 25

for f in feature_cards:
    draw.rounded_rectangle([(cx, 475), (cx + cw, 475 + ch)], radius=12, fill=(15, 23, 42), outline=(37, 51, 73), width=1)
    
    # Tag with accurate padding
    tb = f_tag.getbbox(f["tag"])
    tw = tb[2] - tb[0]
    draw.rounded_rectangle([(cx + 20, 492), (cx + 20 + tw + 16, 514)], radius=4, fill=f["tag_bg"])
    draw.text((cx + 28, 495), f["tag"], fill=f["tag_fg"], font=f_tag)
    
    # Title
    draw.text((cx + 20, 524), f["title"], fill=(255, 255, 255), font=f_card_title)
    
    # Items
    iy = 556
    for item in f["items"]:
        draw.ellipse([(cx + 20, iy + 6), (cx + 25, iy + 11)], fill=(56, 189, 248))
        draw.text((cx + 34, iy), item, fill=(203, 213, 225), font=f_card_body)
        iy += 22
        
    cx += cw + gap

# ----------------- 4. CTA / DEMO BAR -----------------
draw.rounded_rectangle([(65, 650), (1135, 745)], radius=14, fill=(16, 27, 54), outline=(37, 99, 235), width=2)

draw.text((95, 668), "ЖИВОЙ ТЕСТ СКОРОСТИ: Telegram-бот @stockpulse_demo_bot", fill=(255, 255, 255), font=f_cta_h)
draw.text((95, 703), "Отправьте боту любой артикул Wildberries — посмотрите на скорость разбора карточки за 170 мс", fill=(148, 163, 184), font=f_cta_p)

# Button with custom drawn vector arrow
btn_x0, btn_y0, btn_x1, btn_y1 = 925, 672, 1105, 722
draw.rounded_rectangle([(btn_x0, btn_y0), (btn_x1, btn_y1)], radius=10, fill=(16, 185, 129))
btn_text = "ТЕСТ БОТА"
draw.text((btn_x0 + 24, btn_y0 + 14), btn_text, fill=(10, 15, 29), font=f_btn)

arrow_x = btn_x0 + 128
arrow_y = btn_y0 + 25
draw.line([(arrow_x, arrow_y), (arrow_x + 18, arrow_y)], fill=(10, 15, 29), width=3)
draw.polygon([(arrow_x + 14, arrow_y - 6), (arrow_x + 23, arrow_y), (arrow_x + 14, arrow_y + 6)], fill=(10, 15, 29))

# ----------------- 5. FOOTER GUARANTEES (100% CLEAN OF CRYPTO) -----------------
# REMOVED USDT -> strictly compliant: Avito Escrow and test guarantee
footer_items = [
    "Сдача результата за 24–48 часов",
    "Бесплатный расчет на 10 артикулов",
    "Безопасная сделка: Авито / СБП"
]

fy = 782
col_positions = [65, 435, 830]
for idx, (pos_x, item) in enumerate(zip(col_positions, footer_items)):
    draw.ellipse([(pos_x, fy + 5), (pos_x + 8, fy + 13)], fill=(52, 211, 153))
    draw.text((pos_x + 16, fy), item, fill=(148, 163, 184), font=f_footer)

# Output files
out_path = r"C:\Users\1v\.gemini\antigravity\scratch\freelance_market_research\profiles\banner_benchmark.png"
image.save(out_path, "PNG")

art_path = r"C:\Users\1v\.gemini\antigravity\brain\6641ab47-05c1-439b-93ed-ff3a22a7e839\banner_benchmark.png"
image.save(art_path, "PNG")

print("Regenerated banner_benchmark.png without any crypto tokens.")
