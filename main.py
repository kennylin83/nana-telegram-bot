import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from utils import load_memory, save_memory, reset_memory, is_authorized
from config import PROMPT

logging.basicConfig(level=logging.INFO)
memory = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    await update.message.reply_text("嗨嗨～我是娜娜✨有什麼悄悄話想對我說嗎？")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    reset_memory(update.effective_user.id)
    await update.message.reply_text("記憶已經清空囉～我們重新開始吧 💞")

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    user_id = update.effective_user.id
    history = load_memory(user_id)
    message = update.message.text

    history.append({"role": "user", "content": message})
    reply = "嗯嗯～主人說的我都記下來囉♡（假裝有回應 😘）"
    history.append({"role": "assistant", "content": reply})
    save_memory(user_id, history)

    await update.message.reply_text(reply)

def main():
    import os
    token = os.getenv("TELEGRAM_TOKEN")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset_memory", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
    app.run_polling()

if __name__ == "__main__":
    main()