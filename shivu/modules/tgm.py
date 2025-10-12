import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ⚠️ Apna token yahan likho ya environment variable me set karo
TOKEN = os.environ.get("7891572866:AAEKgMqTNK0vQ_mAw63YFKdL6bD2oEiss14") or "PUT_YOUR_BOT_TOKEN_HERE"

async def tgm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    # Check: reply hai ya nahi
    if not msg.reply_to_message:
        await msg.reply_text("🚫 Kisi image par reply karke /tgm likho.")
        return

    reply = msg.reply_to_message

    # Check: photo ya document hai kya
    file_id = None
    if reply.photo:
        # Highest quality photo (last element)
        file_id = reply.photo[-1].file_id
    elif reply.document and reply.document.mime_type.startswith("image/"):
        file_id = reply.document.file_id
    else:
        await msg.reply_text("⚠️ Yeh image message nahi hai. Kisi photo/document image par reply karo.")
        return

    try:
        # File info le aao
        file = await context.bot.get_file(file_id)
        file_path = file.file_path  # path on Telegram server
        bot_token = context.bot.token

        # Direct file link
        link = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"

        await msg.reply_text(f"✅ Image link ready:\n{link}")

    except Exception as e:
        logger.exception(e)
        await msg.reply_text("❗ Error aaya, dobara koshish karo.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("tgm", tgm))

    print("✅ Bot started... Use /tgm on any image reply.")
    app.run_polling()

if __name__ == "__main__":
    main()