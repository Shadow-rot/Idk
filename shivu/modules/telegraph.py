from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from telegraph import Telegraph
import requests
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
    media_type = None
    if reply_msg.photo:
        file_id = reply_msg.photo[-1].file_id
        media_type = "photo"
    elif reply_msg.document:
        file_id = reply_msg.document.file_id
        media_type = "document"
    elif reply_msg.video:
        file_id = reply_msg.video.file_id
        media_type = "video"
    elif reply_msg.animation:
        file_id = reply_msg.animation.file_id
        media_type = "animation"
    else:
        await message.reply_text("Unsupported media type. Try sending a photo, video, document, or text.")
        return

    # Download file from Telegram servers
    file = await context.bot.get_file(file_id)
    file_path = f"downloads/{file.file_id}"
    await file.download_to_drive(file_path)

    # Upload file to telegra.ph
    with open(file_path, "rb") as f:
        response = requests.post(
            "https://telegra.ph/upload",
            files={"file": (file_path, f, "multipart/form-data")}
        )
    try:
        result = response.json()
        if isinstance(result, list) and "src" in result[0]:
            telegraph_url = "https://telegra.ph" + result[0]["src"]
            # Create a page with the media
            page = telegraph.create_page(
                title="Telegraph Media",
                html_content=f'<img src="{telegraph_url}"/>'
            )
            await message.reply_text(f"Link: https://telegra.ph/{page['path']}\nDirect Media: {telegraph_url}")
        else:
            await message.reply_text("Failed to upload media to Telegraph.")
    except Exception as e:
        await message.reply_text(f"Telegraph upload failed: {e}")

# Register handler in your main bot file
application.add_handler(CommandHandler("telegraph", telegraph_command, block=False))