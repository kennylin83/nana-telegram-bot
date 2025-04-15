import os
import logging
import json
import sqlite3
from flask import Flask, request
from telegram import Update, __version__ as TG_VER
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import openai

# 記憶資料庫
DB_PATH = "data/memory.db"
os.makedirs("data", exist_ok=True)

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            user_id TEXT PRIMARY KEY,
            content TEXT
        )
    ''')
    conn.commit()
    conn.close()

def load_memory(user_id):
    init_db()
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
    return update.effective_user.id == 555412099  # 只允許 Kenny 使用

# 初始化
openai.api_key = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")
TOKEN = os.environ.get("TELEGRAM_TOKEN")
app = Flask(__name__)
bot_app = ApplicationBuilder().token(TOKEN).build()
init_db()

# 指令處理
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    await update.message.reply_text("嗨嗨～我是娜娜✨ 有什麼悄悄話想對我說嗎？")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    reset_memory(update.effective_user.id)
    await update.message.reply_text("記憶已經清空囉～我們重新開始吧 💞")

# 文字訊息處理
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    user_id = update.effective_user.id
    user_message = update.message.text
    history = load_memory(user_id)
    history.append({"role": "user", "content": user_message})

    completion = openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=history
    )

    reply_text = completion.choices[0].message.content
    history.append({"role": "assistant", "content": reply_text})

    save_memory(user_id, history)
    await update.message.reply_text(reply_text)

# 加入處理器
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("reset_memory", reset))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

# Webhook 路由
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json(force=True)
    bot_app.update_queue.put_nowait(Update.de_json(update, bot_app.bot))
    return "ok"

# 本地端執行
if __name__ == '__main__':
    PORT = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=PORT)
