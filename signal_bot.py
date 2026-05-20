#!/usr/bin/env python3
"""
Mentor4Trading – Trade Signal Formatter Bot
Du schickst dem Bot privat Text + Bild → er postet formatiert in den Kanal
"""

import requests
import os
import time
from datetime import datetime
import pytz
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
BOT_TOKEN   = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID  = os.environ.get("CHANNEL_ID", "")
YOUR_USER_ID = os.environ.get("YOUR_USER_ID", "")  # Deine Telegram User-ID
TIMEZONE    = "Europe/Berlin"
# ─────────────────────────────────────────────

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Speichert pending Nachrichten (Text ohne Bild noch)
pending = {}


def get_time():
    tz = pytz.timezone(TIMEZONE)
    return datetime.now(tz).strftime("%H:%M")


def parse_signal(text):
    """
    Parst z.B.:
      long MNQ 19450 sl 19380 tp 19550         → direktes Signal
      lo long MNQ 19450 sl 19380 tp 19550      → Limit Order
    Gibt dict zurück oder None wenn ungültig
    """
    try:
        parts = text.lower().split()

        # LO erkennen
        is_limit = parts[0] == "lo"
        if is_limit:
            parts = parts[1:]  # "lo" entfernen

        direction = parts[0]  # long / short
        instrument = parts[1].upper()
        entry = parts[2]
        sl = parts[parts.index("sl") + 1]
        tp = parts[parts.index("tp") + 1]

        if direction not in ("long", "short"):
            return None

        return {
            "direction": direction.upper(),
            "instrument": instrument,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "is_limit": is_limit
        }
    except:
        return None


def format_signal(signal):
    """Formatiert das Signal als Telegram-Nachricht"""

    if signal["is_limit"]:
        # Limit Order Format
        emoji = "⏳"
        arrow = "📈" if signal["direction"] == "LONG" else "📉"
        msg  = f"{emoji} *LIMIT ORDER – {signal['direction']} {signal['instrument']}*\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📍 *Entry:*   `{signal['entry']}`\n"
        msg += f"🛑 *SL:*       `{signal['sl']}`\n"
        msg += f"🎯 *TP:*       `{signal['tp']}`\n"
        msg += f"⏰ *Zeit:*    `{get_time()} Uhr`\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"⚠️ *Order platziert – noch nicht aktiv!*\n"
        msg += f"{arrow} SMC/ICT Setup | @mentor4trading\\_signals"
    else:
        # Direktes Signal Format
        emoji = "🟢" if signal["direction"] == "LONG" else "🔴"
        arrow = "📈" if signal["direction"] == "LONG" else "📉"
        msg  = f"{emoji} *{signal['direction']} Signal – {signal['instrument']}*\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📍 *Entry:*   `{signal['entry']}`\n"
        msg += f"🛑 *SL:*       `{signal['sl']}`\n"
        msg += f"🎯 *TP:*       `{signal['tp']}`\n"
        msg += f"⏰ *Zeit:*    `{get_time()} Uhr`\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"✅ *Jetzt aktiv!*\n"
        msg += f"{arrow} SMC/ICT Setup | @mentor4trading\\_signals"

    return msg


def send_message(chat_id, text):
    requests.post(f"{BASE_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    })


def send_photo_to_channel(photo_id, caption):
    """Sendet Foto + Caption in den Kanal"""
    r = requests.post(f"{BASE_URL}/sendPhoto", json={
        "chat_id": CHANNEL_ID,
        "photo": photo_id,
        "caption": caption,
        "parse_mode": "Markdown"
    })
    return r.ok


def send_text_to_channel(text):
    """Sendet nur Text in den Kanal (ohne Bild)"""
    r = requests.post(f"{BASE_URL}/sendMessage", json={
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "Markdown"
    })
    return r.ok


def handle_update(update):
    msg = update.get("message", {})
    if not msg:
        return

    user_id = str(msg.get("from", {}).get("id", ""))
    chat_id = str(msg.get("chat", {}).get("id", ""))
    text    = msg.get("text", "").strip()
    caption = msg.get("caption", "").strip()
    photo   = msg.get("photo", None)

    # Nur von dir akzeptieren
    if user_id != YOUR_USER_ID:
        send_message(chat_id, "❌ Du bist nicht autorisiert.")
        return

    # Foto mit Caption (direkt alles in einer Nachricht)
    if photo and caption:
        signal = parse_signal(caption)
        if not signal:
            send_message(chat_id, "❌ Format falsch!\nBeispiel: `long MNQ 19450 sl 19380 tp 19550`")
            return
        formatted = format_signal(signal)
        photo_id = photo[-1]["file_id"]  # größtes Bild nehmen
        if send_photo_to_channel(photo_id, formatted):
            send_message(chat_id, "✅ Signal mit Bild gepostet!")
        else:
            send_message(chat_id, "❌ Fehler beim Posten!")
        return

    # Nur Text → zwischenspeichern, warte auf Bild
    if text:
        signal = parse_signal(text)
        if not signal:
            send_message(chat_id, "❌ Format falsch!\nBeispiel: `long MNQ 19450 sl 19380 tp 19550`")
            return
        pending[user_id] = signal
        send_message(chat_id, "✅ Signal gespeichert!\nJetzt Chartbild schicken (oder /skip für nur Text)")
        return

    # Nur Foto → schauen ob Text noch pending
    if photo and user_id in pending:
        signal = pending.pop(user_id)
        formatted = format_signal(signal)
        photo_id = photo[-1]["file_id"]
        if send_photo_to_channel(photo_id, formatted):
            send_message(chat_id, "✅ Signal mit Bild gepostet!")
        else:
            send_message(chat_id, "❌ Fehler beim Posten!")
        return

    # /skip → Text ohne Bild posten
    if text == "/skip" and user_id in pending:
        signal = pending.pop(user_id)
        formatted = format_signal(signal)
        if send_text_to_channel(formatted):
            send_message(chat_id, "✅ Signal ohne Bild gepostet!")
        else:
            send_message(chat_id, "❌ Fehler beim Posten!")
        return

    # /help
    if text == "/help" or text == "/start":
        help_text = (
            "📊 *Signal Bot – Anleitung*\n\n"
            "Format:\n`long MNQ 19450 sl 19380 tp 19550`\n\n"
            "Mit Bild:\n1️⃣ Text schicken\n2️⃣ Chartbild schicken\n\n"
            "Oder beides zusammen:\nBild schicken + Caption mit dem Signal\n\n"
            "Ohne Bild: Nach dem Text `/skip` schicken"
        )
        send_message(chat_id, help_text)
        return


def main():
    print(f"[{datetime.now()}] Signal Bot startet...")

    if not BOT_TOKEN or not CHANNEL_ID or not YOUR_USER_ID:
        print("[ERROR] BOT_TOKEN, CHANNEL_ID oder YOUR_USER_ID fehlt in .env!")
        return

    offset = 0
    print("[OK] Bot läuft – warte auf Nachrichten...")

    while True:
        try:
            r = requests.get(f"{BASE_URL}/getUpdates", params={
                "offset": offset,
                "timeout": 30
            }, timeout=35)

            updates = r.json().get("result", [])
            for update in updates:
                offset = update["update_id"] + 1
                handle_update(update)

        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
