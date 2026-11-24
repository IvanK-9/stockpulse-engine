import os
import asyncio
from telethon import TelegramClient

session_path = r"C:\Users\1v\.gemini\antigravity\scratch\freelance_market_research\raw_data\telegram_reader_session"
env_path = r"C:\Users\1v\.gemini\antigravity\scratch\freelance_market_research\.env"
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k.strip()] = v.strip()

api_id = int(os.getenv("TG_API_ID", 36838578))
api_hash = str(os.getenv("TG_API_HASH", "3c52aa894a8288fdf4c2cd078da37707"))

CANDIDATES = [
    "freelancefeed",
    "zakazy_it",
    "it_freelance",
    "freelancetaverna",
    "freelance_ru",
    "work_in_it",
    "tenchat_it",
    "progjob",
    "job_python",
    "csharp_jobs",
    "freelance_orders",
    "dev_orders",
    "tabor_freelance",
    "freelance_chat_ru"
]

async def main():
    client = TelegramClient(session_path, api_id, api_hash)
    await client.connect()
    valid = []
    for c in CANDIDATES:
        try:
            ent = await client.get_entity(c)
            title = getattr(ent, 'title', c)
            print(f"[+] RESOLVED: @{c} -> {title}")
            valid.append(c)
        except Exception as e:
            print(f"[-] FAILED: @{c} ({e})")
    print(f"\nTotal valid: {len(valid)}: {valid}")

if __name__ == "__main__":
    asyncio.run(main())
