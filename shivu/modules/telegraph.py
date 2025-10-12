from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from telegraph import Telegraph
import requests
import os
import tempfile
from shivu import application

telegraph = Telegraph()
telegraph.create_account(short_name="ShivuBot")

async def telegraph_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    if not message.reply_to_message:
        await message.reply_text("Reply to a message with /telegraph to upload it!")
        return

    reply_msg = message.reply_to_message

    # Handle text messages
    if reply_msg.text or reply_msg.caption:
        try:
            text = reply_msg.text or reply_msg.caption
            response = telegraph.create_page(
                title="Telegraph Post",
                html_content=f"<p>{text}</p>"
            )
            await message.reply_text(f"Link: https://telegra.ph/{response['path']}")
            return
        except Exception as e:
            await message.reply_text(f"Failed to create Telegraph page: {str(e)}")
            return

    # Handle media
    file_id = None
    if reply_msg.photo:
        file_id = reply_msg.photo[-1].file_id
        file_type = 'photo'
    elif reply_msg.video:
        file_id = reply_msg.video.file_id
        file_type = 'video'
    elif reply_msg.animation:
        file_id = reply_msg.animation.file_id
        file_type = 'animation'
    elif reply_msg.document:
        file_id = reply_msg.document.file_id
        file_type = 'document'
    elif reply_msg.audio:
        file_id = reply_msg.audio.file_id
        file_type = 'audio'
    elif reply_msg.sticker:
        file_id = reply_msg.sticker.file_id
        file_type = 'sticker'
    else:
        await message.reply_text("Unsupported media type. Try sending a photo, video, animation, document, or text.")
        return

    # Create a temporary file with a unique name
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_path = temp_file.name
        try:
            # Download file from Telegram servers
            file = await context.bot.get_file(file_id)
            await file.download_to_drive(temp_path)

            # Upload file to telegra.ph
            with open(temp_path, "rb") as f:
                response = requests.post(
                    "https://telegra.ph/upload",
                    files={"file": (os.path.basename(temp_path), f, "multipart/form-data")}
                )

            result = response.json()
            if isinstance(result, list) and "src" in result[0]:
                telegraph_url = "https://telegra.ph" + result[0]["src"]
                html_content = f'<img src="{telegraph_url}"/>' if file_type == 'photo' else f'<a href="{telegraph_url}">Download/Play Media</a>'
                
                page = telegraph.create_page(
                    title=f"Telegraph {file_type.title()}",
                    html_content=html_content
                )
                await message.reply_text(
                    f"Link: https://telegra.ph/{page['path']}\n"
                    f"Direct Media: {telegraph_url}"
                )
            else:
                await message.reply_text("Failed to upload media to Telegraph.")
        except requests.RequestException as e:
            await message.reply_text(f"Network error while uploading to Telegraph: {str(e)}")
        except Exception as e:
            await message.reply_text(f"An error occurred: {str(e)}")
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)

application.add_handler(CommandHandler("telegraph", telegraph_command))