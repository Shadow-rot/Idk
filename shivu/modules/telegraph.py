from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from telegraph import Telegraph
import requests
import os
from shivu import application

telegraph = Telegraph()
telegraph.create_account(short_name="ShivuBot")

async def telegraph_command(update: Update, context: CallbackContext):
    message = update.effective_message

    if not message.reply_to_message:
        await message.reply_text("Reply to a message with /telegraph to upload it!")
        return

    reply_msg = message.reply_to_message

    # Handle text messages
    if reply_msg.text or reply_msg.caption:
        text = reply_msg.text or reply_msg.caption
        response = telegraph.create_page(
            title="Telegraph Post",
            html_content=f"<p>{text}</p>"
        )
        await message.reply_text(f"Link: https://telegra.ph/{response['path']}")
        return

    # Handle media
    file_id = None
    if reply_msg.photo:
        file_id = reply_msg.photo[-1].file_id
        file_type = 'photo'
    elif reply_msg.document:
        file_id = reply_msg.document.file_id
        file_type = 'document'
    elif reply_msg.video:
        file_id = reply_msg.video.file_id
        file_type = 'video'
    elif reply_msg.animation:
        file_id = reply_msg.animation.file_id
        file_type = 'animation'
    else:
        await message.reply_text(
            "Unsupported media type or no media found. "
            "Try sending a photo, video (less than 5MB), or image document."
        )
        return

    # Download file from Telegram servers
    file = await context.bot.get_file(file_id)
    file_path = f"{file.file_id}"
    await file.download_to_drive(file_path)

    # Check file size (Telegraph only supports <5MB)
    max_size = 5 * 1024 * 1024
    if os.path.getsize(file_path) > max_size:
        await message.reply_text("File is too large for Telegraph (max 5MB).")
        os.remove(file_path)
        return

    # Check file extension (Telegraph only accepts images and some videos)
    allowed_exts = ['.jpg', '.jpeg', '.png', '.gif', '.mp4']
    ext = os.path.splitext(file_path)[-1].lower()
    # Try to guess extension from file info if missing
    if not ext and reply_msg.document and reply_msg.document.file_name:
        ext = os.path.splitext(reply_msg.document.file_name)[-1].lower()
    if ext not in allowed_exts:
        await message.reply_text(
            f"Telegraph only supports images and small MP4 videos. "
            f"Your file extension was: {ext}"
        )
        os.remove(file_path)
        return

    # Upload file to telegra.ph
    with open(file_path, "rb") as f:
        response = requests.post(
            "https://telegra.ph/upload",
            files={"file": (f"file{ext}", f, "multipart/form-data")}
        )
    os.remove(file_path)

    try:
        result = response.json()
        if isinstance(result, list) and "src" in result[0]:
            telegraph_url = "https://telegra.ph" + result[0]["src"]
            html_content = f'<img src="{telegraph_url}"/>' if ext in ['.jpg', '.jpeg', '.png', '.gif'] else f'<video src="{telegraph_url}" controls></video>'
            page = telegraph.create_page(
                title=f"Telegraph {file_type.title()}",
                html_content=html_content
            )
            await message.reply_text(f"Link: https://telegra.ph/{page['path']}\nDirect Media: {telegraph_url}")
        else:
            await message.reply_text("Failed to upload media to Telegraph. Only images and small mp4 videos (<5MB) are supported.")
    except Exception as e:
        await message.reply_text(f"Telegraph upload failed: {e}")

application.add_handler(CommandHandler("telegraph", telegraph_command, block=False))