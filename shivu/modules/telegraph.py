from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import requests
import os
import tempfile
from shivu import application

TELEGRAPH_API_URL = "https://api.telegra.ph"
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Make sure to set this in your environment variables

async def create_telegraph_account():
    """Create a Telegraph account and return the access token"""
    response = requests.post(
        f"{TELEGRAPH_API_URL}/createAccount",
        json={
            "short_name": "ShivuBot",
            "author_name": "ShivuBot"
        }
    )
    if response.ok:
        return response.json().get("access_token")
    return None

async def create_telegraph_page(access_token, title, content):
    """Create a Telegraph page and return the URL"""
    response = requests.post(
        f"{TELEGRAPH_API_URL}/createPage",
        json={
            "access_token": access_token,
            "title": title,
            "content": content,
            "return_content": True
        }
    )
    if response.ok:
        return response.json()
    return None

async def upload_to_telegraph(file_path):
    """Upload a file to Telegraph and return the URL"""
    with open(file_path, "rb") as f:
        try:
            response = requests.post(
                f"{TELEGRAPH_API_URL}/upload",
                files={"file": ("file", f, "multipart/form-data")}
            )
            if response.ok:
                return response.json()
            return None
        except Exception as e:
            print(f"Upload error: {str(e)}")
            return None

async def telegraph_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    
    # Check if replying to a message
    if not message.reply_to_message:
        await message.reply_text("Reply to a message with /telegraph to upload it!")
        return

    reply_msg = message.reply_to_message
    status_message = await message.reply_text("Processing...")

    try:
        # Create Telegraph account if not already created
        access_token = await create_telegraph_account()
        if not access_token:
            await status_message.edit_text("Failed to create Telegraph account.")
            return

        # Handle text messages
        if reply_msg.text or reply_msg.caption:
            text = reply_msg.text or reply_msg.caption
            page = await create_telegraph_page(
                access_token,
                "Telegraph Post",
                [{"tag": "p", "children": [text]}]
            )
            if page and "url" in page:
                await status_message.edit_text(f"✅ Successfully created Telegraph page!\n\n🔗 Link: {page['url']}")
            else:
                await status_message.edit_text("Failed to create Telegraph page.")
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
            await status_message.edit_text("Unsupported media type. Try sending a photo, video, animation, document, or text.")
            return

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as temp_file:
            temp_path = temp_file.name
            try:
                # Download file from Telegram
                file = await context.bot.get_file(file_id)
                await file.download_to_drive(temp_path)

                # Upload to Telegraph
                result = await upload_to_telegraph(temp_path)
                
                if result and isinstance(result, list) and "src" in result[0]:
                    telegraph_url = f"https://telegra.ph{result[0]['src']}"
                    
                    # Create Telegraph page with media
                    content = [{"tag": "img", "attrs": {"src": telegraph_url}}] if file_type == 'photo' else [
                        {"tag": "a", "attrs": {"href": telegraph_url}, "children": ["Download/Play Media"]}
                    ]
                    
                    page = await create_telegraph_page(
                        access_token,
                        f"Telegraph {file_type.title()}",
                        content
                    )
                    
                    if page and "url" in page:
                        await status_message.edit_text(
                            f"✅ Successfully uploaded!\n\n"
                            f"🔗 Page: {page['url']}\n"
                            f"📎 Direct Media: {telegraph_url}"
                        )
                    else:
                        await status_message.edit_text("Failed to create Telegraph page.")
                else:
                    await status_message.edit_text("Failed to upload media to Telegraph.")
                    
            except Exception as e:
                await status_message.edit_text(f"An error occurred: {str(e)}")
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
    except Exception as e:
        await status_message.edit_text(f"An unexpected error occurred: {str(e)}")

# Register command handler
application.add_handler(CommandHandler("telegraph", telegraph_command))