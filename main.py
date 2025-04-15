import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from sqlite_memory import load_memory, save_memory, reset_memory, is_authorized
from config import OPENAI_MODEL
import openai
from flask import Flask, request

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
app = ApplicationBuilder().token(TOKEN).build()

# Flask 用於 Webhook 接收
flask_app = Flask(__name__)

# 指令：/start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text("嗨嗨～我是娜娜✨ 有什麼悄悄話想對我說嗎？")

# 指令：/reset_memory
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    reset_memory(update.effective_user.id)
    await update.message.reply_text("娜娜已經把剛剛的事情通通忘掉囉 😘")

# 文字訊息回應
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

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

# 設定指令與訊息處理器
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("reset_memory", reset))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

# Webhook 對應路由
@flask_app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), app.bot)
    app.update_queue.put_nowait(update)
    return "ok"

# 設定 Webhook 路由，讓 Telegram 發訊息時有路徑可接收
@flask_app.route("/")
def index():
    return "Nana is running 💖"

if __name__ == '__main__':
    # 在 Render 上 PORT 是系統分配的環境變數
    PORT = int(os.environ.get("PORT", 5000))
    app.bot.set_webhook(url=f"https://nana-telegram-bot.onrender.com/{TOKEN}")
    flask_app.run(host="0.0.0.0", port=PORT)
