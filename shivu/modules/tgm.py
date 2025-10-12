# requirements:
# pip install python-telegram-bot --upgrade

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TG_BOT_TOKEN") or "PUT_YOUR_BOT_TOKEN_HERE"

async def tgm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    # check reply
    if not msg or not msg.reply_to_message:
        await msg.reply_text("🚫 Kisi image par reply karke /tgm chalayein.")
        return

    reply = msg.reply_to_message

    # CASE 1: Photo (Telegram photos are in reply.photo as list of PhotoSize)
    if reply.photo:
        # highest resolution is last element
        photo = reply.photo[-1]
        file_id = photo.file_id

    # CASE 2: Image sent as Document (user sent image as file)
    elif reply.document and reply.document.mime_type and reply.document.mime_type.startswith("image"):
        file_id = reply.document.file_id

    else:
        await msg.reply_text("🚫 Reply ki hui cheez image nahi hai. Photo ya image-file par reply karein.")
        return

    try:
        # get File object
        file = await context.bot.get_file(file_id)
        # file.file_path gives path on Telegram file server
        file_path = file.file_path  # e.g. photos/file_123.jpg or documents/file_456.bin

        # direct download link:
        bot_token = context.bot.token
        direct_link = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"

        await msg.reply_text(f"🔗 Image link ready:\n{direct_link}")

    except Exception as e:
        logger.exception("Error while getting file link")
        await msg.reply_text("❗ Koi error aaya. Dobara koshish karein ya logs check karein.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("tgm", tgm_command))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()