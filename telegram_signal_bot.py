#!/usr/bin/env python3
"""
TradingView → Telegram Signal Forwarder
Empfängt Webhook Alerts vom BTC HA Strategy Indikator (MES)
und postet formatierte Signale direkt in den Telegram Kanal.
Kein Trading, kein Binance — nur Signal-Posting.
Port: 10001
"""

import os
import logging
import asyncio
from flask import Flask, request, jsonify
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_signal.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

TELEGRAM_TOKEN   = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL = '-1003969084481'
WEBHOOK_SECRET   = os.getenv('WEBHOOK_SECRET')


def send_telegram(message: str):
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        asyncio.run(bot.send_message(
            chat_id=TELEGRAM_CHANNEL,
            text=message,
            parse_mode='HTML'
        ))
        logger.info("✅ Telegram message sent")
    except Exception as e:
        logger.error(f"❌ Telegram error: {e}")


def format_signal(data: dict) -> str | None:
    signal = data.get('signal', '').upper()
    symbol = data.get('symbol', 'MES')
    entry  = data.get('entry')
    sl     = data.get('sl')
    tp     = data.get('tp')

    from datetime import datetime
    zeit = datetime.now().strftime('%H:%M')

    if signal == 'LONG':
        return (
            f"🟢 <b>LONG Signal – {symbol}</b>\n"
            f"――――――――――――\n\n"
            f"📍 Entry:  {entry}\n"
            f"🔴 SL:      {sl}\n"
            f"🎯 TP:      {tp}\n"
            f"🕐 Zeit:   {zeit} Uhr\n\n"
            f"――――――――――――\n"
            f"✅ Jetzt aktiv\!\n"
            f"📈 BTC HA Strategy | @mentor4trading_signals"
        )

    elif signal == 'SHORT':
        return (
            f"🔴 <b>SHORT Signal – {symbol}</b>\n"
            f"――――――――――――\n\n"
            f"📍 Entry:  {entry}\n"
            f"🔴 SL:      {sl}\n"
            f"🎯 TP:      {tp}\n"
            f"🕐 Zeit:   {zeit} Uhr\n\n"
            f"――――――――――――\n"
            f"✅ Jetzt aktiv\!\n"
            f"📈 BTC HA Strategy | @mentor4trading_signals"
        )

    elif signal == 'CLOSE_LONG':
        return (
            f"✅ <b>LONG geschlossen – {symbol}</b>\n"
            f"――――――――――――\n"
            f"📈 BTC HA Strategy | @mentor4trading_signals"
        )

    elif signal == 'CLOSE_SHORT':
        return (
            f"✅ <b>SHORT geschlossen – {symbol}</b>\n"
            f"――――――――――――\n"
            f"📈 BTC HA Strategy | @mentor4trading_signals"
        )

    elif signal == 'BREAKEVEN':
        return (
            f"⚖️ <b>BREAKEVEN – {symbol}</b>\n"
            f"――――――――――――\n"
            f"🔒 SL auf Entry gezogen: <b>{entry}</b>\n"
            f"✅ Trade ist risikofrei\!\n"
            f"📈 BTC HA Strategy | @mentor4trading_signals"
        )

    return None


@app.route('/signal', methods=['POST'])
def signal():
    try:
        data = request.get_json()

        if not data:
            logger.error("❌ No JSON received")
            return jsonify({'error': 'No data'}), 400

        if data.get('secret') != WEBHOOK_SECRET:
            logger.error("❌ Invalid secret")
            return jsonify({'error': 'Unauthorized'}), 401

        logger.info(f"📨 Signal received: {data.get('signal')} {data.get('symbol')}")

        msg = format_signal(data)
        if msg:
            send_telegram(msg)
            return jsonify({'status': 'ok'}), 200
        else:
            logger.error(f"❌ Unknown signal type: {data.get('signal')}")
            return jsonify({'error': 'Unknown signal'}), 400

    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/test', methods=['GET'])
def test():
    return jsonify({'status': 'running', 'port': 10001}), 200


if __name__ == '__main__':
    logger.info("🚀 Telegram Signal Forwarder starting on port 10001")
    app.run(host='0.0.0.0', port=10001, debug=False)
