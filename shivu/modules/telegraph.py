from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import requests
import os
import tempfile
from shivu import application

# Telegraph API Configuration
TELEGRAPH_API = "https://api.telegra.ph"
ACCOUNT_URL = f"{TELEGRAPH_API}/createAccount?short_name=Sandbox&author_name=Anonymous"

async def get_telegraph_token():
    """Create a Telegraph account and return the access token"""
    try:
        response = requests.get(ACCOUNT_URL)
        if response.ok:
            result = response.json()
            if result.get("ok"):
                return result["result"]["access_token"]
    except Exception as e:
        print(f"Failed to get Telegraph token: {str(e)}")
    return None

async def telegraph_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    if not message.reply_to_message:
        await message.reply_text("Reply to a message with /telegraph to upload it!")
        return

    reply_msg = message.reply_to_message
    status_message = await message.reply_text("Processing your request...")

    # Get Telegraph token
    access_token = await get_telegraph_token()
    if not access_token:
        await status_message.edit_text("Failed to create Telegraph account. Please try again later.")
        return

    # Handle text messages
    if reply_msg.text or reply_msg.caption:
        try:
            text = reply_msg.text or reply_msg.caption
            response = requests.post(
                f"{TELEGRAPH_API}/createPage",
                json={
                    "access_token": access_token,
                    "title": "Telegraph Post",
                    "content": [{"tag": "p", "children": [text]}],
                    "return_content": True
                }
            )
            
            if response.ok:
                result = response.json()
                if result.get("ok"):
                    url = f"https://telegra.ph/{result['result']['path']}"
                    await status_message.edit_text(f"✅ Successfully created!\n\n🔗 Link: {url}")
                    return
            await status_message.edit_text("Failed to create Telegraph page.")
            return
        except Exception as e:
            await status_message.edit_text(f"Error creating page: {str(e)}")
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

    # Process media file
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as temp_file:
        temp_path = temp_file.name
        try:
            # Download file
            file = await context.bot.get_file(file_id)
            await file.download_to_drive(temp_path)

            # Upload to Telegraph
            with open(temp_path, "rb") as f:
                response = requests.post(
                    f"{TELEGRAPH_API}/upload",
                    files={"file": ("file", f, "multipart/form-data")}
                )

            if response.ok:
                result = response.json()
                if isinstance(result, list) and len(result) > 0 and "src" in result[0]:
                    telegraph_url = f"https://telegra.ph{result[0]['src']}"
                    
                    # Create page with media
                    content = [{"tag": "img", "attrs": {"src": telegraph_url}}] if file_type == 'photo' else [
                        {"tag": "a", "attrs": {"href": telegraph_url}, "children": ["Download/Play Media"]}
                    ]
                    
                    page_response = requests.post(
                        f"{TELEGRAPH_API}/createPage",
                        json={
                            "access_token": access_token,
                            "title": f"Telegraph {file_type.title()}",
                            "content": content,
                            "return_content": True
                        }
                    )
                    
                    if page_response.ok:
                        page_result = page_response.json()
                        if page_result.get("ok"):
                            page_url = f"https://telegra.ph/{page_result['result']['path']}"
                            await status_message.edit_text(
                                f"✅ Successfully uploaded!\n\n"
                                f"🔗 Page: {page_url}\n"
                                f"📎 Direct Media: {telegraph_url}"
                            )
                        else:
                            await status_message.edit_text("Failed to create Telegraph page.")
                    else:
                        await status_message.edit_text("Failed to create Telegraph page.")
                else:
                    await status_message.edit_text("Failed to upload media to Telegraph.")
            else:
                await status_message.edit_text("Failed to upload media to Telegraph.")
                
        except Exception as e:
            await status_message.edit_text(f"An error occurred: {str(e)}")
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)

# Register command handler
application.add_handler(CommandHandler("telegraph", telegraph_command))