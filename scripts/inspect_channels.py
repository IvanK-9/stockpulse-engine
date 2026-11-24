import asyncio
from telethon import TelegramClient

session_path = r"C:\Users\1v\.gemini\antigravity\scratch\freelance_market_research\raw_data\telegram_reader_session"

async def main():
    client = TelegramClient(session_path, 36838578, "3c52aa894a8288fdf4c2cd078da37707")
    await client.connect()
    for ch in ["it_freelance", "progjob", "job_python", "freelance_chat_ru", "freelancetaverna", "work_in_it"]:
        ent = await client.get_entity(ch)
        async for m in client.iter_messages(ent, limit=1):
            if m.date:
                print(f"[{ch}] Last post: {m.date} | text: {str(m.text)[:80].replace(chr(10), ' ')}")

if __name__ == "__main__":
    asyncio.run(main())
