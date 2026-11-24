import json

with open(r"C:\Users\1v\.gemini\antigravity\scratch\freelance_market_research\raw_data\recent_chat_messages.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for username, chat in data.items():
    print(f"\n=== {chat['name']} (@{username}) ===")
    questions = []
    for m in chat.get("messages", []):
        t = m["text"]
        # Filter out spam ads like CargoS7, job spam
        if any(w in t.lower() for w in ["cargos7", "ребята 16+", "даю по 500р", "карго"]):
            continue
        if any(q in t.lower() for q in ["как", "подскажите", "кто", "посоветуйте", "нужн", "почему", "бот", "парс", "цен", "отчет", "налог", "остат"]):
            questions.append((m["date"], t.replace("\n", " ")[:160]))
    for dt, q in questions[:6]:
        print(f"[{dt}] {q}...")
