#!/usr/bin/env python3
"""
Mentor4Trading – Trade Signal Formatter Bot
Du schickst dem Bot privat Text + Bild → er postet formatiert in den Kanal
"""

import requests
import os
import time
import json
import random
from datetime import datetime
import pytz
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
BOT_TOKEN    = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID   = os.environ.get("CHANNEL_ID", "")
YOUR_USER_ID = os.environ.get("YOUR_USER_ID", "")
TIMEZONE     = "Europe/Berlin"
STATS_FILE   = "/root/signal_bot/stats.json"
# ─────────────────────────────────────────────

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
pending  = {}


def get_time():
    tz = pytz.timezone(TIMEZONE)
    return datetime.now(tz).strftime("%H:%M")


def get_week():
    tz = pytz.timezone(TIMEZONE)
    return datetime.now(tz).strftime("%Y-W%V")


def load_stats():
    try:
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    except:
        return {"week": get_week(), "wins": 0, "losses": 0}


def save_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f)


def add_result(result):
    stats = load_stats()
    current_week = get_week()

    # Neue Woche → Reset
    if stats.get("week") != current_week:
        stats = {"week": current_week, "wins": 0, "losses": 0}

    if result == "win":
        stats["wins"] += 1
    else:
        stats["losses"] += 1

    save_stats(stats)
    return stats


def build_recap(stats):
    wins   = stats.get("wins", 0)
    losses = stats.get("losses", 0)
    total  = wins + losses
    winrate = round((wins / total) * 100) if total > 0 else 0

    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    kw  = now.strftime("%V")

    if winrate >= 70:
        comment = "💪 Starke Woche – weiter so!"
    elif winrate >= 50:
        comment = "📊 Solide Woche – Prozess stimmt!"
    else:
        comment = "🔄 Schwierige Woche – Analyse & weiter!"

    msg  = f"📊 *Weekly Recap – KW {kw}*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"✅ *Wins:*      {wins}\n"
    msg += f"❌ *Losses:*   {losses}\n"
    msg += f"📉 *Trades:*   {total}\n"
    msg += f"📈 *Win Rate:* {winrate}%\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"{comment}\n"
    msg += "@mentor4trading\\_signals"
    return msg


def parse_signal(text):
    try:
        parts = text.lower().split()
        is_limit = parts[0] == "lo"
        if is_limit:
            parts = parts[1:]

        direction  = parts[0]
        instrument = parts[1].upper()
        entry      = parts[2]
        sl         = parts[parts.index("sl") + 1]
        tp         = parts[parts.index("tp") + 1]

        if direction not in ("long", "short"):
            return None

        return {
            "direction":  direction.upper(),
            "instrument": instrument,
            "entry":      entry,
            "sl":         sl,
            "tp":         tp,
            "is_limit":   is_limit
        }
    except:
        return None


def format_signal(signal):
    arrow = "📈" if signal["direction"] == "LONG" else "📉"

    if signal["is_limit"]:
        msg  = f"⏳ *LIMIT ORDER – {signal['direction']} {signal['instrument']}*\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📍 *Entry:*   `{signal['entry']}`\n"
        msg += f"🛑 *SL:*       `{signal['sl']}`\n"
        msg += f"🎯 *TP:*       `{signal['tp']}`\n"
        msg += f"⏰ *Zeit:*    `{get_time()} Uhr`\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"⚠️ *Order platziert – noch nicht aktiv!*\n"
        msg += f"{arrow} SMC/ICT Setup | @mentor4trading\\_signals"
    else:
        emoji = "🟢" if signal["direction"] == "LONG" else "🔴"
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


def format_result(result, instrument):
    if result == "win":
        msg  = f"✅ *FULL TP – {instrument}*\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"🎯 Take Profit erreicht!\n"
        msg += f"⏰ `{get_time()} Uhr`\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "💰 *GG! Trade geschlossen!*\n"
        msg += "@mentor4trading\\_signals"
    else:
        msg  = f"❌ *STOP LOSS – {instrument}*\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"🛑 Stop Loss getroffen\n"
        msg += f"⏰ `{get_time()} Uhr`\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "💪 *Loss gehört dazu – next setup kommt!*\n"
        msg += "@mentor4trading\\_signals"
    return msg


def format_update(signal):
    arrow = "📈" if signal["direction"] == "LONG" else "📉"
    msg  = f"🔄 *UPDATE – LIMIT ORDER {signal['instrument']}*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"📍 *Neuer Entry:* `{signal['entry']}`\n"
    msg += f"🛑 *SL:*           `{signal['sl']}`\n"
    msg += f"🎯 *TP:*           `{signal['tp']}`\n"
    msg += f"⏰ *Zeit:*        `{get_time()} Uhr`\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "⚠️ *Order angepasst – alter Entry ungültig!*\n"
    msg += f"{arrow} SMC/ICT Setup | @mentor4trading\\_signals"
    return msg


def format_announcement(text):
    msg  = "📢 *ANNOUNCEMENT*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"{text}\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "🤖 Jarvis | @mentor4trading\\_signals"
    return msg


def format_be(instrument):
    msg  = f"🔒 *BREAKEVEN – {instrument}*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "SL auf Entry gezogen – kein Risiko mehr\\!\n"
    msg += f"⏰ `{get_time()} Uhr`\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "🤖 Jarvis | @mentor4trading\\_signals"
    return msg


def format_partial(instrument, tp1):
    msg  = f"💰 *PARTIAL TP – {instrument}*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "Erste Position geschlossen\\!\n"
    msg += f"🎯 *TP1 bei:* `{tp1}`\n"
    msg += "Rest läuft weiter 📈\n"
    msg += f"⏰ `{get_time()} Uhr`\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "🤖 Jarvis | @mentor4trading\\_signals"
    return msg


WIN_MESSAGES = [
    "🔥 Das ist der Prozess\\! Genau so läuft das.",
    "💰 Geiler Trade\\! Analyse stimmt, Execution stimmt – weiter so\\!",
    "🎯 Bullseye\\! Setup gelesen, Entry gesetzt, Profit gesichert.",
    "📈 Das ist kein Glück – das ist Können\\! GG.",
    "🏆 Wieder einen geholt\\! Der Markt zahlt uns heute.",
    "⚡ Sauber abgeliefert\\! SMC funktioniert – immer wieder.",
    "💪 Das war Lehrbuch\\! Entry, Management, Exit – perfekt.",
    "🚀 Grüner Trade\\! So macht Trading Spaß.",
    "🎉 Kassiert\\! Wer den Plan hält, wird belohnt.",
    "✅ Wieder im Plus\\! Disziplin zahlt sich aus.",
    "🤑 Full TP kassiert\\! Das Konto sagt Danke.",
    "💥 Das saß\\! Setup war klar, Execution war sauber – GG.",
    "🎯 Plan gemacht, Plan gehalten, Profit gemacht. Simpel.",
    "📊 Jarvis bestätigt: Grüner Trade. Der Prozess funktioniert\\!",
    "🔑 Das ist es\\! Kein Overtrading, kein FOMO – nur das Setup.",
    "💎 Diamantenhände\\! TP gehalten und voll kassiert.",
    "⚡ Boom\\! Der Markt hat heute geliefert – wir auch.",
    "🌟 Textbuch Setup\\! CHoCH, BOS, Entry – Full TP. Perfekt.",
    "🏅 Wieder einen im Sack\\! Weiter mit dem gleichen Prozess.",
    "🔥 Das ist warum wir jeden Morgen aufstehen und traden\\!"
]

LOSS_MESSAGES = [
    "💪 Loss gehört dazu\\! Kein Trader der Welt hat 100% Win Rate.",
    "🔄 Nächstes Setup kommt\\! Der Markt gibt immer neue Chancen.",
    "🧠 Jeder Loss ist eine Lektion – was können wir daraus lernen?",
    "⚡ Abgehakt\\! SL ist kein Versagen, SL ist Risikomanagement.",
    "📊 Ein Loss ändert nichts am Prozess\\! Weiter nach Plan.",
    "💎 Die Besten verlieren auch\\! Was sie unterscheidet ist wie sie damit umgehen.",
    "🎯 Setup war valid – der Markt hat anders entschieden. Das ist Trading.",
    "🔑 SL respektiert, Konto geschützt\\! Das ist schon ein Gewinn.",
    "💪 Kopf hoch\\! Ein Loss ist kein Problem – Revenge Trading wäre eines.",
    "📈 Langfristig gewinnt der Prozess\\! Ein Trade ändert nichts.",
    "🧘 Ruhe bewahren\\! Die nächste Chance kommt bestimmt.",
    "⚠️ Kein Revenge Trading\\! Pause, Reset, nächstes Setup abwarten.",
    "🎯 Jarvis sagt: Abgehakt und vorwärts\\! Der nächste Trade wartet.",
    "💡 Manchmal nimmt der Markt – aber meistens gibt er zurück\\!",
    "🔄 Reset\\! Neuer Trade, neuer Anfang, neuer Profit.",
    "💪 Mark Douglas sagte: Ein Loss ist nur ein Trade in einer Serie\\!",
    "📊 Win Rate stimmt trotzdem\\! Ein Loss ist Teil des Systems.",
    "🛡️ SL getriggert – Konto gesichert\\! So bleibt man langfristig im Game.",
    "🌅 Morgen ist ein neuer Tag\\! Heute abgehakt, morgen zurückschlagen.",
    "⚡ Verluste sind Schulgebühren der Märkte\\! Wir zahlen und lernen."
]

MORNING_MESSAGES = [
    "Neuer Tag, neue Chance.\nBleibt beim Plan, managed euer Risiko\nund lasst die Setups zu euch kommen!",
    "Die Märkte warten nicht – aber gute Trader schon.\nNur A+ Setups. Kein FOMO. Kein Stress.",
    "Heute wird geliefert. Nicht gehofft, nicht geraten.\nNur Chart, Setup, Execute. 🎯",
    "Disziplin schlägt Talent jeden Tag.\nHaltet euren Plan und der Rest kommt von selbst.",
    "Kaffee an, Charts auf, Kopf klar. ☕\nMal sehen was der Markt heute serviert.",
    "Verluste gehören dazu. Gewinne auch.\nWas zählt ist der Prozess – und der stimmt.",
    "Kein Setup? Kein Trade. So einfach ist das.\nGeduld ist die profitabelste Fähigkeit im Trading.",
    "Der Markt hat immer Recht.\nUnsere Aufgabe ist es, zuzuhören – nicht zu kämpfen.",
    "Heute ist ein neuer Tag. Gestrige Trades sind Geschichte.\nFokus auf jetzt. 💪",
    "Wer auf alles reagiert, verliert alles.\nWer auf das Richtige wartet, gewinnt langfristig.",
    "SMC ist kein Geheimnis – es ist Geduld & Wiederholung.\nBleibt konsequent!",
    "Risiko managen, Gewinne laufen lassen.\nKlingt einfach. Ist es auch – wenn man es verinnerlicht hat.",
    "Nicht jeder Tag bringt ein Setup.\nAber jeder Tag ist eine Chance, besser zu werden. 📈",
    "Die besten Trader handeln weniger, nicht mehr.\nQualität über Quantität – immer.",
    "Markt offen heißt nicht Pflicht zu traden.\nWarte auf deinen Edge – dann strike. 🎯",
    "Heute ist Gameday. Aber nur wenn der Markt mitspielt.\nSonst ist Zuschauen auch eine Position.",
    "Stop Loss ist keine Niederlage – es ist Risikomanagement.\nJeder Profi nutzt ihn. Ihr auch? ✅",
    "Jarvis checkt die Charts. Jarvis sieht Struktur.\nJetzt liegt es an euch. Let's go! 🤖",
    "Kleines Risiko, großes Potenzial.\nSo spielt man das Spiel langfristig. 💰",
    "Gut Ding will Weile haben – auch im Trading.\nKein Setup erzwingen. Der Markt kommt zu euch."
]


def build_morning_message():
    text = random.choice(MORNING_MESSAGES)
    msg  = "🌅 *Guten Morgen Trader\\!*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"{text}\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "🤖 Jarvis | @mentor4trading\\_signals"
    return msg


def send_message(chat_id, text):
    requests.post(f"{BASE_URL}/sendMessage", json={
        "chat_id":    chat_id,
        "text":       text,
        "parse_mode": "Markdown"
    })


def send_photo_to_channel(photo_id, caption):
    r = requests.post(f"{BASE_URL}/sendPhoto", json={
        "chat_id":    CHANNEL_ID,
        "photo":      photo_id,
        "caption":    caption,
        "parse_mode": "Markdown"
    })
    return r.ok


def send_text_to_channel(text):
    r = requests.post(f"{BASE_URL}/sendMessage", json={
        "chat_id":    CHANNEL_ID,
        "text":       text,
        "parse_mode": "Markdown"
    })
    return r.ok


def check_friday_recap():
    """Prüft ob es Freitag 17:00 Uhr ist und postet ggf. den Recap"""
    tz  = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    if now.weekday() == 4 and now.hour == 17 and now.minute == 0:
        stats = load_stats()
        recap = build_recap(stats)
        send_text_to_channel(recap)
        print(f"[OK] Weekly Recap gepostet!")


def handle_update(update):
    msg = update.get("message", {})
    if not msg:
        return

    user_id = str(msg.get("from", {}).get("id", ""))
    chat_id = str(msg.get("chat", {}).get("id", ""))
    text    = msg.get("text", "").strip()
    caption = msg.get("caption", "").strip()
    photo   = msg.get("photo", None)

    if user_id != YOUR_USER_ID:
        send_message(chat_id, "❌ Du bist nicht autorisiert.")
        return

    # Foto mit Caption
    if photo and caption:
        signal = parse_signal(caption)
        if not signal:
            send_message(chat_id, "❌ Format falsch!\nBeispiel: `long MNQ 19450 sl 19380 tp 19550`")
            return
        formatted = format_signal(signal)
        photo_id  = photo[-1]["file_id"]
        if send_photo_to_channel(photo_id, formatted):
            send_message(chat_id, "✅ Signal mit Bild gepostet!")
        else:
            send_message(chat_id, "❌ Fehler beim Posten!")
        return

    if text:
        parts = text.lower().split()

        # BE: be MNQ
        if parts[0] == "be" and len(parts) >= 2:
            instrument = parts[1].upper()
            if send_text_to_channel(format_be(instrument)):
                send_message(chat_id, "✅ BE gepostet!")
            else:
                send_message(chat_id, "❌ Fehler beim Posten!")
            return

        # Partial TP: partial MNQ 19520
        if parts[0] == "partial" and len(parts) >= 3:
            instrument = parts[1].upper()
            tp1        = parts[2]
            if send_text_to_channel(format_partial(instrument, tp1)):
                send_message(chat_id, "✅ Partial TP gepostet!")
            else:
                send_message(chat_id, "❌ Fehler beim Posten!")
            return

        # Announcement: announce Dein Text hier
        if parts[0] == "announce" and len(parts) >= 2:
            announce_text = " ".join(text.split(" ")[1:])
            formatted = format_announcement(announce_text)
            if send_text_to_channel(formatted):
                send_message(chat_id, "✅ Announcement gepostet!")
            else:
                send_message(chat_id, "❌ Fehler beim Posten!")
            return

        # LO Update: update MNQ 19430 sl 19370 tp 19550
        if parts[0] == "update" and len(parts) >= 5:
            try:
                instrument = parts[1].upper()
                entry      = parts[2]
                sl         = parts[parts.index("sl") + 1]
                tp         = parts[parts.index("tp") + 1]
                direction  = pending.get(user_id, {}).get("direction", "LONG")
                signal     = {"instrument": instrument, "entry": entry, "sl": sl, "tp": tp, "direction": direction}
                update_msg = format_update(signal)
                if send_text_to_channel(update_msg):
                    send_message(chat_id, "✅ LO Update gepostet!")
                else:
                    send_message(chat_id, "❌ Fehler beim Posten!")
            except:
                send_message(chat_id, "❌ Format falsch!\nBeispiel: `update MNQ 19430 sl 19370 tp 19550`")
            return

        # Trade Ergebnis: win MNQ / loss MNQ
        if parts[0] in ("win", "loss") and len(parts) >= 2:
            instrument = parts[1].upper()
            result_msg = format_result(parts[0], instrument)
            stats      = add_result(parts[0])
            if send_text_to_channel(result_msg):
                # Motivations-Post direkt danach
                if parts[0] == "win":
                    motivation = random.choice(WIN_MESSAGES)
                else:
                    motivation = random.choice(LOSS_MESSAGES)
                send_text_to_channel(f"🤖 *Jarvis sagt:*\n{motivation}")
                send_message(chat_id, f"✅ Trade Update gepostet!\n📊 Diese Woche: {stats['wins']} Wins / {stats['losses']} Losses")
            else:
                send_message(chat_id, "❌ Fehler beim Posten!")
            return

        # /recap → manuell Recap abrufen
        if text == "/recap":
            stats = load_stats()
            recap = build_recap(stats)
            if send_text_to_channel(recap):
                send_message(chat_id, "✅ Recap gepostet!")
            else:
                send_message(chat_id, "❌ Fehler beim Posten!")
            return

        # /stats → nur dir anzeigen
        if text == "/stats":
            stats   = load_stats()
            wins    = stats.get("wins", 0)
            losses  = stats.get("losses", 0)
            total   = wins + losses
            winrate = round((wins / total) * 100) if total > 0 else 0
            send_message(chat_id, f"📊 *Diese Woche:*\n✅ Wins: {wins}\n❌ Losses: {losses}\n📈 Win Rate: {winrate}%")
            return

        # /skip → pending Signal ohne Bild posten
        if text == "/skip" and user_id in pending:
            signal    = pending.pop(user_id)
            formatted = format_signal(signal)
            if send_text_to_channel(formatted):
                send_message(chat_id, "✅ Signal ohne Bild gepostet!")
            else:
                send_message(chat_id, "❌ Fehler beim Posten!")
            return

        # /help oder /start
        if text in ("/help", "/start"):
            help_text = (
                "📊 *Signal Bot – Anleitung*\n\n"
                "📍 *Direktes Signal:*\n`long MNQ 19450 sl 19380 tp 19550`\n\n"
                "⏳ *Limit Order:*\n`lo long MNQ 19450 sl 19380 tp 19550`\n\n"
                "🔄 *LO Update:*\n`update MNQ 19430 sl 19370 tp 19550`\n\n"
                "✅ *Trade gewonnen:*\n`win MNQ`\n\n"
                "❌ *Trade verloren:*\n`loss MNQ`\n\n"
                "📊 *Recap manuell posten:*\n`/recap`\n\n"
                "🔢 *Stats nur für dich:*\n`/stats`\n\n"
                "🔒 *Breakeven:*\n`be MNQ`\n\n"
                "💰 *Partial TP:*\n`partial MNQ 19520`\n\n"
                "📢 *Announcement:*\n`announce Dein Text hier`\n\n"
                "1️⃣ Text schicken → 2️⃣ Chartbild schicken\n"
                "Oder Bild + Caption direkt zusammen\n\n"
                "⏭ *Ohne Bild:* `/skip` nach dem Text"
            )
            send_message(chat_id, help_text)
            return

        # Signal Text → auf Bild warten
        signal = parse_signal(text)
        if not signal:
            send_message(chat_id, "❌ Format falsch!\nBeispiel: `long MNQ 19450 sl 19380 tp 19550`")
            return
        pending[user_id] = signal
        send_message(chat_id, "✅ Signal gespeichert!\nJetzt Chartbild schicken (oder /skip für nur Text)")
        return

    # Nur Foto ohne Caption → pending Signal verwenden
    if photo and user_id in pending:
        signal    = pending.pop(user_id)
        formatted = format_signal(signal)
        photo_id  = photo[-1]["file_id"]
        if send_photo_to_channel(photo_id, formatted):
            send_message(chat_id, "✅ Signal mit Bild gepostet!")
        else:
            send_message(chat_id, "❌ Fehler beim Posten!")
        return


def main():
    print(f"[{datetime.now()}] Signal Bot startet...")

    if not BOT_TOKEN or not CHANNEL_ID or not YOUR_USER_ID:
        print("[ERROR] BOT_TOKEN, CHANNEL_ID oder YOUR_USER_ID fehlt in .env!")
        return

    offset        = 0
    last_recap_min = -1
    print("[OK] Bot läuft – warte auf Nachrichten...")

    while True:
        try:
            # Freitag Recap + Guten Morgen (nur einmal pro Minute)
            tz  = pytz.timezone(TIMEZONE)
            now = datetime.now(tz)
            current_min = now.hour * 60 + now.minute
            if current_min != last_recap_min:
                last_recap_min = current_min
                check_friday_recap()
                # Guten Morgen täglich 06:30
                if now.hour == 6 and now.minute == 30:
                    send_text_to_channel(build_morning_message())
                    print("[OK] Guten Morgen gepostet!")

            r = requests.get(f"{BASE_URL}/getUpdates", params={
                "offset":  offset,
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
