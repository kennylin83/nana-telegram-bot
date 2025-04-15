import os
import json
import sqlite3
import logging
import requests

from flask import Flask, request
from telegram import Update, ForceReply
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# === 記憶資料庫 ===
DB_PATH = "data/memory.db"

def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS memories (
                    user_id TEXT PRIMARY KEY,
                    content TEXT
                )''')
    conn.commit()
    conn.close()

def load_memory(user_id):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT content FROM memories WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return []

def save_memory(user_id, history):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("REPLACE INTO memories (user_id, content) VALUES (?, ?)", (user_id, json.dumps(history)))
    conn.commit()
    conn.close()

def reset_memory(user_id):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM memories WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def is_authorized(update):
    return True  # 可自行設定限制的使用者 ID

# === Telegram 設定 ===
TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

flask_app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), app)
    app.update_queue.put_nowait(update)
    return "ok"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text("嗨嗨～我是娜娜✨ 有什麼悄悄話想對我說嗎？")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    reset_memory(update.effective_user.id)
    await update.message.reply_text("記憶已經清空囉～我們重新開始吧 💞")

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    user_id = update.effective_user.id
    user_message = update.message.text
    history = load_memory(user_id)

    history.append({"role": "user", "content": user_message})

    import openai
    openai.api_key = OPENAI_API_KEY

    completion = openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=history
    )

    reply_text = completion.choices[0].message.content
    history.append({"role": "assistant", "content": reply_text})

    save_memory(user_id, history)
    await update.message.reply_text(reply_text)

# === 啟動 Telegram Bot 應用 ===
if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 5000))
    init_db()

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset_memory", reset))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), reply))

    app.update_queue = app.update_queue  # 設定給 webhook 用

    render_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    webhook_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    res = requests.post(webhook_url, json={"url": render_url})
    print("Webhook 設定結果：", res.text)

    flask_app.run(host="0.0.0.0", port=PORT)
