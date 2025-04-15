import os
import json
import logging
import sqlite3

from telegram import Update
from telegram.ext import (ApplicationBuilder, ContextTypes, CommandHandler,
                          MessageHandler, filters)
from openai import OpenAI
from flask import Flask, request

from sqlite_memory import load_memory, save_memory, reset_memory, is_authorized

# Logging setup
logging.basicConfig(level=logging.INFO)

# API Keys
TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL")

# OpenAI client
openai = OpenAI(api_key=OPENAI_API_KEY)

# Application & Flask
app = ApplicationBuilder().token(TOKEN).build()
flask_app = Flask(__name__)

# === Command Handlers ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text("嗨嗨～我是娜娜✨ 有什麼悄悄話想對我說嗎？")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    reset_memory(update.effective_user.id)
    await update.message.reply_text("記憶已經清空囉～我們重新開始吧 ✨")


async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    user_id = update.effective_user.id
    user_message = update.message.text
    history = load_memory(user_id)

    history.append({"role": "user", "content": user_message})

    completion = openai.chat.completions.create(
        model=OPENAI_MODEL,
        messages=history
    )

    reply_text = completion.choices[0].message.content
    history.append({"role": "assistant", "content": reply_text})

    save_memory(user_id, history)
    await update.message.reply_text(reply_text)


# === Register Handlers ===
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("reset_memory", reset))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))


# === Webhook Endpoint for Telegram ===
@flask_app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), app.bot)
    app.update_queue.put_nowait(update)
    return "ok"


# === Set Webhook on Startup ===
@flask_app.before_first_request
def setup_webhook():
    external_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
    webhook_url = f"https://{external_hostname}/{TOKEN}"
    logging.info(f"Setting webhook to: {webhook_url}")
    app.bot.set_webhook(webhook_url)


# === Run Flask (used by Render) ===
if __name__ == '__main__':
    PORT = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=PORT)
