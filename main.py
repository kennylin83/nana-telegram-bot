import os
import json
import logging
import sqlite3
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import openai

# === OpenAI 設定 ===
openai.api_key = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

# === SQLite 紀錄路徑 ===
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
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT content FROM memories WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return []

def save_memory(user_id, history):
    conn = get_conn()
    c = conn.cursor()
    c.execute("REPLACE INTO memories (user_id, content) VALUES (?, ?)", (user_id, json.dumps(history)))
    conn.commit()
    conn.close()

def reset_memory(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM memories WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def is_authorized(update):
    return True  # 可以自行改為限制使用者 ID

# === Telegram Bot ===
TOKEN = os.environ.get("TELEGRAM_TOKEN")
app = ApplicationBuilder().token(TOKEN).build()
flask_app = Flask(__name__)
init_db()

# /start 指令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text("嗨嗨～我是娜娜✨ 有什麼悄悄話想對我說嗎？")

# /reset_memory 指令
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    reset_memory(update.effective_user.id)
    await update.message.reply_text("記憶已經清空囉～我們重新開始吧 💞")

# 對話功能
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    user_id = update.effective_user.id
    user_msg = update.message.text
    history = load_memory(user_id)
    history.append({"role": "user", "content": user_msg})

    completion = openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=history
    )

    reply_text = completion.choices[0].message.content
    history.append({"role": "assistant", "content": reply_text})
    save_memory(user_id, history)

    await update.message.reply_text(reply_text)

# 加入指令與對話監聽
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("reset_memory", reset))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

# Webhook 接收 Telegram 請求
@flask_app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), app.bot)
    app.update_queue.put_nowait(update)
    return "ok"

# 啟動點
if __name__ == "__main__":
    import asyncio

    PORT = int(os.environ.get("PORT", 5000))

    async def setup_and_run():
        await app.bot.set_webhook(f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}")
        flask_app.run(host="0.0.0.0", port=PORT)

    asyncio.run(setup_and_run())
