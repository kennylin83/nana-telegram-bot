import os
import logging
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from sqlite_memory import load_memory, save_memory, reset_memory, is_authorized

from config import OPENAI_MODEL
import openai
from flask import Flask, request

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
app = ApplicationBuilder().token(TOKEN).build()

flask_app = Flask(__name__)

# Start 指令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text("嗨嗨～我是娜娜✨ 有什麼悄悄話想對我說嗎？")

# Reset 指令
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    reset_memory(update.effective_user.id)
    await update.message.reply_text("記憶已經清空囉～我們重新開始吧 🥰")

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

# Telegram Bot 指令註冊
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("reset_memory", reset))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

# Webhook 入口
@flask_app.route("/7750963807:AAF8UQkU4reGlNuqwYMQEDk6Xe6fbGb6z0Y", methods=["POST"])
def webhook():
    update = request.get_json(force=True)
    app.update_queue.put_nowait(Update.de_json(update, app.bot))
    return "ok"

# 本地或 Render 執行
if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 5000))

    # 綁定 webhook 給 Telegram
    import asyncio
    async def setup():
        await app.bot.set_webhook(f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}")
    asyncio.run(setup())

    # 啟動 Flask
    flask_app.run(host="0.0.0.0", port=PORT)
