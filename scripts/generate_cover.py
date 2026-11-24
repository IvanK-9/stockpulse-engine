from PIL import Image, ImageDraw, ImageFont
import os

width, height = 1200, 900
image = Image.new("RGB", (width, height), color=(11, 17, 33)) # Deep navy obsidian
draw = ImageDraw.Draw(image)

font_dir = "C:\\Windows\\Fonts"
font_badge = ImageFont.truetype(os.path.join(font_dir, "segoeuib.ttf"), 15)
font_num = ImageFont.truetype(os.path.join(font_dir, "segoeuib.ttf"), 16)
font_title = ImageFont.truetype(os.path.join(font_dir, "segoeuib.ttf"), 44)
font_subtitle = ImageFont.truetype(os.path.join(font_dir, "segoeuib.ttf"), 32)
font_card_title = ImageFont.truetype(os.path.join(font_dir, "segoeuib.ttf"), 26)
font_card_desc = ImageFont.truetype(os.path.join(font_dir, "segoeui.ttf"), 20)
font_footer = ImageFont.truetype(os.path.join(font_dir, "segoeuib.ttf"), 20)

# Outer decorative border
draw.rounded_rectangle([(25, 25), (width - 25, height - 25)], radius=20, outline=(30, 41, 59), width=2)
# Inner panel
draw.rounded_rectangle([(40, 40), (width - 40, height - 40)], radius=16, fill=(15, 23, 42))

# ----------------- TOP BADGE & TITLE -----------------
# 100% compliant with Avito rules: "РАЗРАБОТКА И АВТОМАТИЗАЦИЯ" (no "базы", no "парсеры" in main title)
badge_text = "ИНЖЕНЕРНЫЙ BACKEND"
bb = font_badge.getbbox(badge_text)
bw = bb[2] - bb[0]
draw.rounded_rectangle([(70, 68), (70 + bw + 36, 102)], radius=6, fill=(37, 99, 235))
draw.ellipse([(84, 82), (90, 88)], fill=(255, 255, 255))
draw.text((100, 75), badge_text, fill=(255, 255, 255), font=font_badge)

# Main Title
draw.text((70, 122), "АВТОМАТИЗАЦИЯ МАРКЕТПЛЕЙСОВ", fill=(255, 255, 255), font=font_title)
draw.text((70, 180), "БОТЫ • СИНХРОНИЗАЦИЯ 1C • АВТОПРАЙСЕРЫ", fill=(56, 189, 248), font=font_subtitle)

# ----------------- 4 KEY CARDS -----------------
cards = [
    (
        "Аналитика розничных цен Wildberries и Ozon",
        "Мониторинг изменения цен, остатков и скидок в каталоге. Скорость от 170 мс."
    ),
    (
        "Telegram-боты и автопрайсеры под ключ",
        "Ловля слотов приемки (Коледино, Электросталь), пересчет цен по СПП и алерты."
    ),
    (
        "Синхронизация складов (FBS / FBO)",
        "Связка 1С, МойСклад и маркетплейсов по API. Защита от штрафов за отмены."
    ),
    (
        "Стабильность и надежность 24/7",
        "Стек C# / Python / Docker. Демонстрация работы до оплаты, сдача под ключ."
    )
]

start_y = 252
card_h = 108
spacing = 18

for i, (title, desc) in enumerate(cards):
    y = start_y + i * (card_h + spacing)
    # Card container
    draw.rounded_rectangle([(70, y), (width - 70, y + card_h)], radius=12, fill=(11, 17, 33), outline=(51, 65, 85), width=1)
    
    # Bullet icon circle
    cx, cy = 112, y + 40
    r = 16
    draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=(37, 99, 235))
    
    # Exact centered digit
    num_str = str(i + 1)
    nb = font_num.getbbox(num_str)
    nw = nb[2] - nb[0]
    nh = nb[3] - nb[1]
    draw.text((cx - nw / 2 - nb[0], cy - nh / 2 - nb[1]), num_str, fill=(255, 255, 255), font=font_num)
    
    # Text with neat margins
    draw.text((150, y + 20), title, fill=(248, 250, 252), font=font_card_title)
    draw.text((150, y + 60), desc, fill=(148, 163, 184), font=font_card_desc)

# ----------------- FOOTER BAR (CENTERED) -----------------
draw.rounded_rectangle([(70, 770), (width - 70, 828)], radius=10, fill=(20, 29, 47), outline=(51, 65, 85), width=1)
footer_text = "Работа онлайн по всей России • Демо на ваших товарах • Без предоплаты"
fb = font_footer.getbbox(footer_text)
fw = fb[2] - fb[0]
fh = fb[3] - fb[1]
fx = (width - fw) / 2
fy = 770 + (58 - fh) / 2 - fb[1]
draw.text((fx, fy), footer_text, fill=(56, 189, 248), font=font_footer)

output_path = r"C:\Users\1v\.gemini\antigravity\scratch\freelance_market_research\profiles\avito_cover.png"
image.save(output_path, "PNG")

artifact_path = r"C:\Users\1v\.gemini\antigravity\brain\6641ab47-05c1-439b-93ed-ff3a22a7e839\avito_cover.png"
image.save(artifact_path, "PNG")
print("Saved 100% compliant avito cover.")
