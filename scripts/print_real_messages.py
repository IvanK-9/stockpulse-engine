import json

with open(r"C:\Users\1v\.gemini\antigravity\scratch\freelance_market_research\raw_data\recent_chat_messages.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for target in ["ozonhelpchat", "wildberries_chat_mp", "sellers_kaspi"]:
    chat = data.get(target, {})
    print("=" * 60)
    print(f"ЧАТ: {chat.get('name')}")
    print("=" * 60)
    count = 0
    for m in chat.get("messages", []):
        t = m.get("text", "")
        # Filter spam
        if any(w in t.lower() for w in ["cargos7", "ребята 16+", "даю по 500р", "фулфилмент", "крупные импортеры", "вывод в топ", "ozon up"]):
            continue
        print(f"[{m.get('date')}] ID {m.get('id')}:")
        print(t)
        print("-" * 40)
        count += 1
        if count >= 8:
            break
