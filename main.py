import os
import json
import logging
import sqlite3
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

# --- Logging ---
logging.basicConfig(level=logging.INFO)

# --- Config ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL")
EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_HOSTNAME")

# --- SQLite Memory ---
DB_PATH = "data/memory.db"
os.makedirs("data", exist_ok=True)

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            user_id TEXT PRIMARY KEY,
            content TEXT
        )
    """)
    conn.commit()
    conn.close()

def load_memory(user_id):
    init_db()
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT content FROM memories WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return json.loads(row[0]) if row else []

def save_memory(user_id, history):
    init_db()
    conn = get_conn()
    c = conn.cursor()
    c.execute("REPLACE INTO memories (user_id, content) VALUES (?, ?)", (user_id, json.dumps(history)))
    conn.commit()
    conn.close()

def reset_memory(user_id):
    init_db()
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM memories WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def is_authorized(update: Update):
    return True  # 之後可加白名單邏輯

# --- Telegram Bot ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    await update.message.reply_text("嗨嗨～我是娜娜✨ 有什麼悄悄話想對我說嗎？")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    reset_memory(update.effective_user.id)
    await update.message.reply_text("記憶已經清空囉～我們重新開始吧 ✨")

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    from openai import ChatCompletion

    user_id = update.effective_user.id
    user_msg = update.message.text
    history = load_memory(user_id)
    history.append({"role": "user", "content": user_msg})

    completion = ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=history
    )
    reply_text = completion.choices[0].message.content
    history.append({"role": "assistant", "content": reply_text})

    save_memory(user_id, history)
    await update.message.reply_text(reply_text)

# --- App & Webhook ---
flask_app = Flask(__name__)

@flask_app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    from telegram import Update
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    bot_app.update_queue.put_nowait(update)
    return "ok"

async def set_webhook():
    url = f"https://{EXTERNAL_URL}/{TOKEN}"
    await bot_app.bot.set_webhook(url)

# --- Main Entry ---
if __name__ == "__main__":
    bot_app = ApplicationBuilder().token(TOKEN).build()

    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("reset_memory", reset))
    bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), reply))

    import asyncio
    asyncio.run(set_webhook())

    PORT = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=PORT)
