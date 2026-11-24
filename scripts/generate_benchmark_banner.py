from PIL import Image, ImageDraw, ImageFont
import os

width, height = 1200, 900
image = Image.new("RGB", (width, height), color=(10, 15, 29))
draw = ImageDraw.Draw(image)

font_dir = "C:\\Windows\\Fonts"
f_badge = ImageFont.truetype(os.path.join(font_dir, "segoeuib.ttf"), 20)
f_h1 = ImageFont.truetype(os.path.join(font_dir, "segoeuib.ttf"), 46)
f_sub = ImageFont.truetype(os.path.join(font_dir, "segoeuib.ttf"), 28)
f_big_stat = ImageFont.truetype(os.path.join(font_dir, "segoeuib.ttf"), 68)
f_card_h = ImageFont.truetype(os.path.join(font_dir, "segoeuib.ttf"), 24)
f_card_p = ImageFont.truetype(os.path.join(font_dir, "segoeui.ttf"), 18)
f_pill_h = ImageFont.truetype(os.path.join(font_dir, "segoeuib.ttf"), 22)
f_pill_p = ImageFont.truetype(os.path.join(font_dir, "segoeui.ttf"), 17)
f_code = ImageFont.truetype(os.path.join(font_dir, "consola.ttf"), 19)

# Outer glow / frame
draw.rectangle([(25, 25), (width - 25, height - 25)], outline=(37, 99, 235), width=2)
draw.rounded_rectangle([(45, 45), (width - 45, height - 45)], radius=18, fill=(15, 23, 42))

# Top Badge: HIGH AVAILABILITY & SPEED
draw.rounded_rectangle([(80, 75), (430, 115)], radius=8, fill=(16, 185, 129)) # Emerald
draw.text((100, 83), "STATUS: HIGH AVAILABILITY (24/7)", fill=(10, 15, 29), font=f_badge)

# Main Title
draw.text((80, 135), "ПРОМЫШЛЕННЫЙ БЭКЕНД ДЛЯ E-COM", fill=(255, 255, 255), font=f_h1)
draw.text((80, 195), "Скорость 170 мс • Нулевые штрафы • Надежность C# & Python", fill=(56, 189, 248), font=f_sub)

# Benchmark split banner: 170 ms Hero card
draw.rounded_rectangle([(80, 260), (450, 480)], radius=14, fill=(17, 24, 39), outline=(16, 185, 129), width=2)
draw.text((105, 280), "168 мс", fill=(52, 211, 153), font=f_big_stat)
draw.text((105, 365), "СКОРОСТЬ СБОРА КАРТОЧКИ", fill=(248, 250, 252), font=f_card_h)
draw.text((105, 405), "Прямой запрос к CDN маркетплейса\nБез тяжелых браузеров, капч и зависаний.\n1 000 артикулов за 3 минуты в Excel.", fill=(148, 163, 184), font=f_card_p)

# Code / Terminal Card
draw.rounded_rectangle([(475, 260), (width - 80, 480)], radius=14, fill=(11, 15, 25), outline=(51, 65, 85), width=2)
# Window dots
draw.ellipse([(500, 282), (512, 294)], fill=(239, 68, 68))
draw.ellipse([(520, 282), (532, 294)], fill=(245, 158, 11))
draw.ellipse([(540, 282), (552, 294)], fill=(16, 185, 129))
draw.text((570, 279), "stockpulse-engine :: latency-benchmark", fill=(100, 116, 139), font=f_card_p)

code_lines = [
    "> GET /vol1385/part138590/card.json HTTP/2",
    "< 200 OK [168ms] payload: 42.8 KB",
    "> BasePrice: 3 900 RUB (Юнит-экономика)",
    "> DiscountPrice: 1 890 RUB (СПП WB)",
    "> SellerINN: 462802543300 [Верифицирован]",
    "STATUS: 1000 SKU выгружено за 180 сек в Excel"
]
cy = 315
for cl in code_lines:
    color = (52, 211, 153) if "200 OK" in cl or "1000 SKU" in cl else ((56, 189, 248) if "> BasePrice" in cl or "> DiscountPrice" in cl else (148, 163, 184))
    draw.text((500, cy), cl, fill=color, font=f_code)
    cy += 25

# Bottom 3 Feature Pills (без эмодзи, только чистые стилизованные блоки)
pills = [
    ("[1] ЗАЩИТА ОТ ШТРАФОВ", "Синхронизация остатков 1С ↔ WB\nОбновление складов за 15 секунд"),
    ("[2] АВТОБРОНЬ СЛОТОВ", "Чекер коэффициентов Коледино\nУведомления и ловля окон приемки"),
    ("[3] АУДИТ ЦЕН ЗА 24 ЧАСА", "30 конкурентов в чистом Excel\nРеальные цены до скидок и СПП")
]

px = 80
pw = (width - 160 - 40) // 3
for title, sub in pills:
    draw.rounded_rectangle([(px, 510), (px + pw, 650)], radius=12, fill=(17, 24, 39), outline=(51, 65, 85), width=1)
    draw.text((px + 18, 528), title, fill=(248, 250, 252), font=f_pill_h)
    draw.text((px + 18, 568), sub, fill=(148, 163, 184), font=f_pill_p)
    px += pw + 20

# Bottom Action / Demo Bar
draw.rounded_rectangle([(80, 680), (width - 80, 765)], radius=14, fill=(24, 34, 58), outline=(37, 99, 235), width=2)
draw.text((110, 695), "ЖИВОЙ ТЕСТ СКОРОСТИ: Telegram-бот @stockpulse_demo_bot", fill=(255, 255, 255), font=f_card_h)
draw.text((110, 728), "Отправьте любой артикул Wildberries — бот разберет карточку за 200 мс прямо сейчас", fill=(148, 163, 184), font=f_card_p)

# Footer guarantee
draw.text((80, 805), "• Сдача первого результата за 24–48 часов    • Без предоплаты за тест    • Оплата через Авито / СБП / USDT", fill=(56, 189, 248), font=f_badge)

out_path = r"C:\Users\1v\.gemini\antigravity\scratch\freelance_market_research\profiles\banner_benchmark.png"
image.save(out_path, "PNG")

art_path = r"C:\Users\1v\.gemini\antigravity\brain\6641ab47-05c1-439b-93ed-ff3a22a7e839\banner_benchmark.png"
image.save(art_path, "PNG")
print("Saved clean benchmark banner.")
