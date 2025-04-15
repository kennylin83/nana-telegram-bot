import os
import json
import sqlite3
import logging
from flask import Flask, request
from telegram import Update, ForceReply
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI

# 初始化日誌
logging.basicConfig(level=logging.INFO)

# 連線資訊
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

# 建立 Flask app
flask_app = Flask(__name__)

# 初始化 OpenAI
openai = OpenAI(api_key=OPENAI_API_KEY)

# SQLite 記憶體資料庫
DB_PATH = "data/memory.db"

def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            user_id TEXT PRIMARY KEY,
            content TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_conn():
    return sqlite3.connect(DB_PATH)

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
    return True  # 預設允許所有人互動

# 建立 Telegram bot
bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

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

# 文字訊息處理
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    user_id = update.effective_user.id
    user_msg = update.message.text
    print("收到訊息：", user_msg)
    history = load_memory(user_id)

    history.append({"role": "user", "content": user_msg})

    try:
        completion = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=history
        )
        reply_text = completion.choices[0].message.content
        history.append({"role": "assistant", "content": reply_text})
        save_memory(user_id, history)
        await update.message.reply_text(reply_text)
    except Exception as e:
        print("OpenAI 發生錯誤：", e)
        await update.message.reply_text("嗚嗚，娜娜一時之間腦袋打結了，等我一下再說一次好嗎🥺")

# 加入指令與文字監聽器
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("reset_memory", reset))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

# Telegram webhook
@flask_app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    bot_app.update_queue.put_nowait(update)
    return "ok"

# 部署時自動啟用 webhook
@flask_app.before_first_request
def setup():
    import requests
    url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{TELEGRAM_TOKEN}"
    requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={url}")

# 本地執行
if __name__ == "__main__":
    import requests

    # 將 webhook 指向 Render 的網址
    render_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    set_hook_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    response = requests.post(set_hook_url, json={"url": render_url})

    print("Webhook 註冊結果:", response.text)
    flask_app.run(host="0.0.0.0", port=PORT)
