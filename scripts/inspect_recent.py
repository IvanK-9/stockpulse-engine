import json

with open(r"C:\Users\1v\.gemini\antigravity\scratch\freelance_market_research\raw_data\recent_chat_messages.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for target in ["sellers_kaspi", "ozonhelpchat", "wildberries_chat_mp"]:
    chat = data.get(target, {})
    print("=" * 60)
    print(f"ЧАТ: {chat.get('name')} (@{target})")
    print("=" * 60)
    for m in chat.get("messages", []):
        dt = m.get("date", "")
        txt = m.get("text", "").replace("\n", " ")
        print(f"[{dt}] {txt}")
    print()
