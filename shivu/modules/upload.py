import urllib.request
import io
import aiohttp
import asyncio
from pymongo import ReturnDocument
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu.modules.database.sudo import is_user_sudo
from shivu import application, collection, db, CHARA_CHANNEL_ID, SUPPORT_CHAT, sudo_users


WRONG_FORMAT_TEXT = """Wrong ❌️ format...  
Example: `/upload Img_url muzan-kibutsuji Demon-slayer 3`

Format:  
img_url/video_url character-name anime-name rarity-number  

**Note:** Supports both images and videos/MP4 files!

Use rarity number accordingly:  
1. 🟢 Common 
2. 🟣 Rare
3. 🟡 Legendary 
4. 💮 Special Edition 
5. 💫 Neon 
6. ✨ Manga 
7. 🎭 Cosplay 
8. 🎐 Celestial 
9. 🔮 Premium Edition 
10. 💋 Erotic 
11. 🌤 Summer 
12. ☃️ Winter 
13. ☔️ Monsoon 
14. 💝 Valentine 
15. 🎃 Halloween 
16. 🎄 Christmas 
17. 🏵 Mythic
18. 🎗 Special Events
19. 🎥 AMV
20. 👼 Tiny
"""

REPLY_UPLOAD_TEXT = """Reply to a photo/video with:
`/upload character-name anime-name rarity-number`

Example: `/upload muzan-kibutsuji Demon-slayer 3`

**Supports:** Photos, Videos, MP4 files, and Documents!
"""

RARITY_MAP = {
    1: "🟢 Common",
    2: "🟣 Rare",
    3: "🟡 Legendary", 
    4: "💮 Special Edition", 
    5: "💫 Neon",
    6: "✨ Manga", 
    7: "🎭 Cosplay",
    8: "🎐 Celestial",
    9: "🔮 Premium Edition",
    10: "💋 Erotic",
    11: "🌤 Summer",
    12: "☃️ Winter",
    13: "☔️ Monsoon",
    14: "💝 Valentine",
    15: "🎃 Halloween", 
    16: "🎄 Christmas",
    17: "🏵 Mythic",
    18: "🎗 Special Events",
    19: "🎥 AMV",
    20: "👼 Tiny"
}


async def get_next_sequence_number(sequence_name):
    """Generate next sequential ID for characters"""
    sequence_collection = db.sequences
    sequence_document = await sequence_collection.find_one_and_update(
        {'_id': sequence_name},
        {'$inc': {'sequence_value': 1}},
        return_document=ReturnDocument.AFTER
    )
    if not sequence_document:
        await sequence_collection.insert_one({'_id': sequence_name, 'sequence_value': 0})
        return 0
    return sequence_document['sequence_value']


async def upload_to_catbox(file_bytes, filename):
    """Upload file to Catbox"""
    url = "https://catbox.moe/user/api.php"

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
            data = aiohttp.FormData()
            data.add_field('reqtype', 'fileupload')
            data.add_field('fileToUpload', file_bytes, filename=filename)

            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = (await response.text()).strip()
                    # Verify the URL is accessible
                    if result and result.startswith('http'):
                        return result
                return None
    except Exception as e:
        print(f"Catbox upload error: {e}")
        return None


async def upload_to_imgbb(file_bytes, filename):
    """Upload to ImgBB (reliable for images, free tier available)"""
    # You'll need an API key from https://api.imgbb.com/
    # For now, this is a placeholder - you can add your key
    api_key = "YOUR_IMGBB_API_KEY"  # Get from https://api.imgbb.com/
    
    if api_key == "YOUR_IMGBB_API_KEY":
        return None
    
    url = "https://api.imgbb.com/1/upload"
    
    try:
        import base64
        
        # ImgBB requires base64 encoding
        b64_image = base64.b64encode(file_bytes.read()).decode('utf-8')
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
            data = aiohttp.FormData()
            data.add_field('key', api_key)
            data.add_field('image', b64_image)
            
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('success'):
                        return result['data']['url']
                return None
    except Exception as e:
        print(f"ImgBB upload error: {e}")
        return None


async def upload_to_telegra_ph(file_bytes, filename):
    """Upload file to Telegraph (works reliably for images)"""
    url = "https://telegra.ph/upload"

    try:
        # Check if it's an image
        if not any(filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            return None

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
            data = aiohttp.FormData()
            data.add_field('file', file_bytes, filename=filename)

            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    if isinstance(result, list) and len(result) > 0:
                        img_url = f"https://telegra.ph{result[0]['src']}"
                        # Verify URL is accessible
                        async with session.head(img_url) as check:
                            if check.status == 200:
                                return img_url
                return None
    except Exception as e:
        print(f"Telegraph upload error: {e}")
        return None


async def upload_to_pixeldrain(file_bytes, filename):
    """Upload to Pixeldrain (good for both images and videos)"""
    url = "https://pixeldrain.com/api/file"
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
            data = aiohttp.FormData()
            data.add_field('file', file_bytes, filename=filename)
            
            async with session.post(url, data=data) as response:
                if response.status == 201:
                    result = await response.json()
                    if result.get('success'):
                        file_id = result['id']
                        # Return direct view URL
                        return f"https://pixeldrain.com/api/file/{file_id}?download"
                return None
    except Exception as e:
        print(f"Pixeldrain upload error: {e}")
        return None


async def upload_to_gofile(file_bytes, filename):
    """Upload to Gofile (reliable, no limits)"""
    try:
        # First get server
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
            async with session.get("https://api.gofile.io/getServer") as resp:
                if resp.status != 200:
                    return None
                server_data = await resp.json()
                if server_data['status'] != 'ok':
                    return None
                server = server_data['data']['server']
            
            # Upload file
            url = f"https://{server}.gofile.io/uploadFile"
            data = aiohttp.FormData()
            data.add_field('file', file_bytes, filename=filename)
            
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    if result['status'] == 'ok':
                        return result['data']['downloadPage']
                return None
    except Exception as e:
        print(f"Gofile upload error: {e}")
        return None


async def verify_url_accessible(url):
    """Verify if URL is accessible by Telegram"""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            async with session.head(url, allow_redirects=True) as response:
                return response.status == 200
    except:
        return False


async def upload_with_fallback(file_bytes, filename):
    """Try multiple upload services in order with verification"""
    services = [
        ("Catbox", upload_to_catbox),
        ("Telegraph", upload_to_telegra_ph),
        ("Pixeldrain", upload_to_pixeldrain),
        ("ImgBB", upload_to_imgbb),
        ("Gofile", upload_to_gofile)
    ]

    for service_name, upload_func in services:
        try:
            print(f"Trying {service_name}...")
            
            # Reset file pointer
            if hasattr(file_bytes, 'seek'):
                file_bytes.seek(0)
            
            url = await upload_func(file_bytes if hasattr(file_bytes, 'read') else io.BytesIO(file_bytes), filename)
            
            if url:
                # Verify URL is accessible
                print(f"Verifying {service_name} URL...")
                if await verify_url_accessible(url):
                    print(f"✅ Successfully uploaded and verified with {service_name}")
                    return url, service_name
                else:
                    print(f"⚠️ {service_name} URL not accessible, trying next...")
                    continue
        except Exception as e:
            print(f"❌ {service_name} failed: {e}")
            continue

    return None, None


def is_video_url(url):
    """Check if URL points to a video file"""
    if not url:
        return False
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']
    return any(url.lower().endswith(ext) for ext in video_extensions)


def is_video_file(filename):
    """Check if filename is a video"""
    if not filename:
        return False
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']
    return any(filename.lower().endswith(ext) for ext in video_extensions)


async def create_character_entry(media_url, character_name, anime, rarity, user_id, user_name, context, is_new=True, is_video=False, file_bytes=None, filename=None):
    """Create character entry in database and post to channel"""
    char_id = str(await get_next_sequence_number('character_id')).zfill(2)

    character = {
        'img_url': media_url,
        'id': char_id,
        'name': character_name,
        'anime': anime,
        'rarity': rarity,
        'is_video': is_video
    }

    action_text = "𝑴𝒂𝒅𝒆" if is_new else "𝑼𝒑𝒅𝒂𝒕𝒆𝒅"
    media_type = "🎥 Video" if is_video else "🖼 Image"

    caption = (
        f'<b>{char_id}:</b> {character_name}\n'
        f'<b>{anime}</b>\n'
        f'<b>{rarity[0]} 𝙍𝘼𝙍𝙄𝙏𝙔:</b> {rarity[2:]}\n'
        f'<b>Type:</b> {media_type}\n\n'
        f'{action_text} 𝑩𝒚 ➥ <a href="tg://user?id={user_id}">{user_name}</a>'
    )

    try:
        message = None
        
        # Try sending via URL first
        try:
            if is_video:
                message = await context.bot.send_video(
                    chat_id=CHARA_CHANNEL_ID,
                    video=media_url,
                    caption=caption,
                    parse_mode='HTML',
                    read_timeout=60,
                    write_timeout=60
                )
                character['file_id'] = message.video.file_id
                character['file_unique_id'] = message.video.file_unique_id
            else:
                message = await context.bot.send_photo(
                    chat_id=CHARA_CHANNEL_ID,
                    photo=media_url,
                    caption=caption,
                    parse_mode='HTML',
                    read_timeout=60,
                    write_timeout=60
                )
                character['file_id'] = message.photo[-1].file_id
                character['file_unique_id'] = message.photo[-1].file_unique_id
        except Exception as url_error:
            print(f"URL upload failed: {url_error}")
            
            # Fallback: Try uploading file bytes directly if available
            if file_bytes and filename:
                print("Trying direct file upload as fallback...")
                if hasattr(file_bytes, 'seek'):
                    file_bytes.seek(0)
                
                if is_video or is_video_file(filename):
                    message = await context.bot.send_video(
                        chat_id=CHARA_CHANNEL_ID,
                        video=file_bytes,
                        caption=caption,
                        parse_mode='HTML',
                        read_timeout=120,
                        write_timeout=120
                    )
                    character['file_id'] = message.video.file_id
                    character['file_unique_id'] = message.video.file_unique_id
                else:
                    message = await context.bot.send_photo(
                        chat_id=CHARA_CHANNEL_ID,
                        photo=file_bytes,
                        caption=caption,
                        parse_mode='HTML',
                        read_timeout=60,
                        write_timeout=60
                    )
                    character['file_id'] = message.photo[-1].file_id
                    character['file_unique_id'] = message.photo[-1].file_unique_id
            else:
                raise url_error

        if message:
            character['message_id'] = message.message_id
            await collection.insert_one(character)
            return True, f'✅ Character added successfully!\n🆔 ID: {char_id}\n📁 Type: {media_type}'
        else:
            raise Exception("Failed to send message")
            
    except Exception as e:
        # Save to database anyway for manual fix
        await collection.insert_one(character)
        error_msg = str(e)
        return False, (
            f"⚠️ Character added to database but channel upload failed.\n\n"
            f"🆔 ID: {char_id}\n"
            f"❌ Error: {error_msg}\n\n"
            f"💡 The character is saved. You can try updating it later with:\n"
            f"`/update {char_id} img_url <new_url>`"
        )


def validate_url(url):
    """Validate if URL is accessible"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        urllib.request.urlopen(req, timeout=15)
        return True
    except Exception as e:
        print(f"URL validation failed: {e}")
        return False


def parse_rarity(rarity_str):
    """Parse and validate rarity number"""
    try:
        rarity_num = int(rarity_str)
        if rarity_num in RARITY_MAP:
            return RARITY_MAP[rarity_num]
        return None
    except (KeyError, ValueError):
        return None


async def upload(update: Update, context: CallbackContext) -> None:
    """Handle character uploads via URL or by replying to media"""
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('❌ You need sudo access to use this command.')
        return

    try:
        # Handle reply to photo/video/document
        if update.message.reply_to_message:
            reply_msg = update.message.reply_to_message

            if not (reply_msg.photo or reply_msg.video or reply_msg.document):
                await update.message.reply_text('❌ Please reply to a photo, video, or document!')
                return

            args = context.args
            if len(args) != 3:
                await update.message.reply_text(REPLY_UPLOAD_TEXT)
                return

            processing_msg = await update.message.reply_text('⏳ Downloading file...')

            try:
                # Get file and determine type
                is_video = False
                file = None
                filename = None

                if reply_msg.photo:
                    file = await reply_msg.photo[-1].get_file()
                    filename = f"char_{update.effective_user.id}.jpg"
                elif reply_msg.video:
                    file = await reply_msg.video.get_file()
                    filename = f"char_{update.effective_user.id}.mp4"
                    is_video = True
                else:  # Document
                    file = await reply_msg.document.get_file()
                    filename = reply_msg.document.file_name or f"char_{update.effective_user.id}"
                    if reply_msg.document.mime_type and 'video' in reply_msg.document.mime_type:
                        is_video = True

                # Download file
                file_bytes = await file.download_as_bytearray()
                file_io = io.BytesIO(file_bytes)

                # Try uploading with multiple services
                await processing_msg.edit_text('⏳ Uploading to cloud services...')
                media_url, service = await upload_with_fallback(file_io, filename)

                if not media_url:
                    await processing_msg.edit_text(
                        '⚠️ All cloud upload services failed.\n'
                        '🔄 Attempting direct upload to Telegram...'
                    )
                    # Use a dummy URL, we'll upload directly
                    media_url = f"https://example.com/{filename}"
                else:
                    media_type = "video" if is_video else "image"
                    await processing_msg.edit_text(
                        f'✅ {media_type.title()} uploaded to {service}!\n'
                        f'🔗 {media_url}\n\n'
                        f'⏳ Adding to database...'
                    )

                character_name = args[0].replace('-', ' ').title()
                anime = args[1].replace('-', ' ').title()
                rarity = parse_rarity(args[2])

                if not rarity:
                    await processing_msg.edit_text('❌ Invalid rarity number. Check format guide.')
                    return

                # Pass file_bytes for fallback direct upload
                file_io.seek(0)
                success, message = await create_character_entry(
                    media_url, character_name, anime, rarity,
                    update.effective_user.id, update.effective_user.first_name,
                    context, is_video=is_video, file_bytes=file_io, filename=filename
                )

                await processing_msg.edit_text(message)

            except Exception as e:
                await processing_msg.edit_text(f'❌ Error: {str(e)}')
                return

        # Handle URL-based upload
        else:
            args = context.args
            if len(args) != 4:
                await update.message.reply_text(WRONG_FORMAT_TEXT)
                return

            media_url = args[0]
            if not validate_url(media_url):
                await update.message.reply_text('❌ Invalid or inaccessible URL.')
                return

            is_video = is_video_url(media_url)
            character_name = args[1].replace('-', ' ').title()
            anime = args[2].replace('-', ' ').title()
            rarity = parse_rarity(args[3])

            if not rarity:
                await update.message.reply_text('❌ Invalid rarity number. Check format guide.')
                return

            success, message = await create_character_entry(
                media_url, character_name, anime, rarity,
                update.effective_user.id, update.effective_user.first_name,
                context, is_video=is_video
            )

            await update.message.reply_text(message)

    except Exception as e:
        await update.message.reply_text(
            f'❌ Character upload failed.\n\n'
            f'Error: {str(e)}\n\n'
            f'Contact: {SUPPORT_CHAT}'
        )


async def delete(update: Update, context: CallbackContext) -> None:
    """Delete a character by ID"""
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('❌ You need sudo access to use this command.')
        return

    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text('❌ Incorrect format.\n\nUse: `/delete ID`')
            return

        character = await collection.find_one_and_delete({'id': args[0]})

        if not character:
            await update.message.reply_text('❌ Character not found in database.')
            return

        # Try to delete from channel
        try:
            await context.bot.delete_message(
                chat_id=CHARA_CHANNEL_ID, 
                message_id=character['message_id']
            )
        except Exception:
            pass

        await update.message.reply_text('✅ Character deleted successfully.')

    except Exception as e:
        await update.message.reply_text(f'❌ Error: {str(e)}')


async def update_character(update: Update, context: CallbackContext) -> None:
    """Update character fields"""
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('❌ You need sudo access to use this command.')
        return

    try:
        args = context.args
        if len(args) != 3:
            await update.message.reply_text(
                '❌ Incorrect format.\n\n'
                'Use: `/update id field new_value`\n\n'
                'Valid fields: img_url, name, anime, rarity'
            )
            return

        char_id, field, new_value = args
        character = await collection.find_one({'id': char_id})

        if not character:
            await update.message.reply_text('❌ Character not found.')
            return

        valid_fields = ['img_url', 'name', 'anime', 'rarity']
        if field not in valid_fields:
            await update.message.reply_text(
                f'❌ Invalid field.\n\nChoose from: {", ".join(valid_fields)}'
            )
            return

        # Process field values
        if field in ['name', 'anime']:
            new_value = new_value.replace('-', ' ').title()
        elif field == 'rarity':
            new_value = parse_rarity(new_value)
            if not new_value:
                await update.message.reply_text('❌ Invalid rarity number.')
                return
        elif field == 'img_url':
            if not validate_url(new_value):
                await update.message.reply_text('❌ Invalid or inaccessible URL.')
                return

        # Update database
        update_data = {field: new_value}

        if field == 'img_url':
            update_data['is_video'] = is_video_url(new_value)

        await collection.find_one_and_update({'id': char_id}, {'$set': update_data})
        character = await collection.find_one({'id': char_id})

        is_video = character.get('is_video', False)
        media_type = "🎥 Video" if is_video else "🖼 Image"

        caption = (
            f'<b>{character["id"]}:</b> {character["name"]}\n'
            f'<b>{character["anime"]}</b>\n'
            f'<b>{character["rarity"][0]} 𝙍𝘼𝙍𝙄𝙏𝙔:</b> {character["rarity"][2:]}\n'
            f'<b>Type:</b> {media_type}\n\n'
            f'𝑼𝒑𝒅𝒂𝒕𝒆𝒅 𝑩𝒚 ➥ <a href="tg://user?id={update.effective_user.id}">'
            f'{update.effective_user.first_name}</a>'
        )

        try:
            if field == 'img_url':
                await context.bot.delete_message(
                    chat_id=CHARA_CHANNEL_ID, 
                    message_id=character['message_id']
                )

                if is_video:
                    message = await context.bot.send_video(
                        chat_id=CHARA_CHANNEL_ID,
                        video=new_value,
                        caption=caption,
                        parse_mode='HTML',
                        read_timeout=60,
                        write_timeout=60
                    )
                    await collection.find_one_and_update(
                        {'id': char_id},
                        {'$set': {
                            'message_id': message.message_id,
                            'file_id': message.video.file_id,
                            'file_unique_id': message.video.file_unique_id
                        }}
                    )
                else:
                    message = await context.bot.send_photo(
                        chat_id=CHARA_CHANNEL_ID,
                        photo=new_value,
                        caption=caption,
                        parse_mode='HTML',
                        read_timeout=60,
                        write_timeout=60
                    )
                    await collection.find_one_and_update(
                        {'id': char_id},
                        {'$set': {
                            'message_id': message.message_id,
                            'file_id': message.photo[-1].file_id,
                            'file_unique_id': message.photo[-1].file_unique_id
                        }}
                    )
            else:
                await context.bot.edit_message_caption(
                    chat_id=CHARA_CHANNEL_ID,
                    message_id=character['message_id'],
                    caption=caption,
                    parse_mode='HTML'
                )
        except Exception as e:
            await update.message.reply_text(
                f'⚠️ Database updated but channel message update failed.\n\nError: {str(e)}'
            )
            return

        await update.message.reply_text('✅ Character updated successfully.')

    except Exception as e:
        await update.message.reply_text(f'❌ Error: {str(e)}')


# Register handlers
application.add_handler(CommandHandler('upload', upload, block=False))
application.add_handler(CommandHandler('delete', delete, block=False))
application.add_handler(CommandHandler('update', update_character, block=False))