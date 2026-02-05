from telethon import TelegramClient, events
import sqlite3
import os
import re

# Telegram API credentials
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")

# Group to monitor
TARGET_GROUP = os.getenv("TARGET_GROUP")
ALERT_TO = "me"  # Sends alerts to your Saved Messages

# ---------- INCLUDE KEYWORDS ----------
INCLUDE = {
    "deck cadet": 5,
    "deckhand": 4,
    "deck/stew": 4,
    "deck/": 3,
    "deck": 3,
    "officer": 3,
    "chase boat captain": 4,
    "tender driver": 4,
    "diver": 3,
    "tutor": 3
}

# ---------- EXCLUDE KEYWORDS ----------
EXCLUDE = {
    "stewardess": -10,
    "female": -5,
    "divemaster": -5
}

# Minimum score to trigger an alert
THRESHOLD = 3

# Minimum yacht size (meters) — only alert if >= 40m
MIN_YACHT_SIZE = 40

# ---------- Database to avoid duplicates ----------
conn = sqlite3.connect("seen.db")
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS seen (id INTEGER PRIMARY KEY)")
conn.commit()

# ---------- Scoring function ----------
def score(text: str) -> int:
    if not text:
        return 0
    text_lower = text.lower()
    s = 0
    for k, v in INCLUDE.items():
        if k in text_lower:
            s += v
    for k, v in EXCLUDE.items():
        if k in text_lower:
            s += v
    # Check yacht size mentioned in text
    size_matches = re.findall(r'(\d{2,3})\s?m', text_lower)
    size_ok = False
    for match in size_matches:
        try:
            if int(match) >= MIN_YACHT_SIZE:
                size_ok = True
                break
        except:
            continue
    if size_matches and not size_ok:
        # Yacht mentioned but too small → subtract huge points
        s -= 20
    return s

# ---------- Telegram client ----------
client = TelegramClient("session", api_id, api_hash)

@client.on(events.NewMessage(chats=TARGET_GROUP))
async def handler(event):
    msg = event.message

    # Check duplicates
    c.execute("SELECT 1 FROM seen WHERE id=?", (msg.id,))
    if c.fetchone():
        return

    # Score the message
    s = score(msg.text)

    if s >= THRESHOLD:
        # Send alert
        await client.send_message(
            ALERT_TO,
            f"📢 **Job Match Found**\n\n"
            f"Score: {s}\n\n"
            f"{msg.text}\n\n"
            f"🔗 {msg.link}"
        )

    # Mark as seen
    c.execute("INSERT INTO seen VALUES (?)", (msg.id,))
    conn.commit()

# Start bot
client.start()
client.run_until_disconnected()
