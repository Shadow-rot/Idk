import urllib.request
import io
import aiohttp
from pymongo import ReturnDocument
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, filters
from shivu.modules.database.sudo import is_user_sudo
from shivu import application, collection, db, CHARA_CHANNEL_ID, SUPPORT_CHAT, sudo_users


WRONG_FORMAT_TEXT = """Wrong ❌️ format...  
Example: `/upload Img_url muzan-kibutsuji Demon-slayer 3 1`

Format:  
img_url character-name anime-name rarity-number event-number  

Use rarity number accordingly:  
1. 🟢 Comman 
2. 🟣 Rare
3. 🟡 Legendary 
4. 💮 Special Edition 
5. 💫 Neon 
6. ✨ Manga 
7. 🎭 Cosplay 
8. 🎐 Celestial 
9. 🔮 Premium edition 
10.💋 Erotic 
11. 🌤 Summer 
12. ☃️ Winter 
13. ☔️ Monsoon 
14. 💝 Valentine 
15. 🎃 Halloween 
16. 🎄 Christmas 
17. 🏵 Mythic
18. 🎗 Spacial Events
19. 🎥 Amv

Use event number accordingly:  
1 🏖 Summer  
2 👘 Kimono  
3 ☃️ Winter  
4 💞 Valentine  
5 🎒 School  
6 🎃 Halloween  
7 🎮 Game  
8 🎩 Tuxedo  
9 👥 Duo  
10 🧹 Made  
11 ☔ Monsoon  
12 🐰 Bunny  
13 🤝🏻 Group  
14 🥻 Saree  
15 🎄 Christmas  
16 👑 Lord  
17 None (Skip event)
"""

REPLY_UPLOAD_TEXT = """Reply to a photo/video with:
`/upload character-name anime-name rarity-number event-number`

Example: `/upload muzan-kibutsuji Demon-slayer 3 1`
"""

EVENT_MAPPING = {
    1: {"name": "𝒔𝒖𝒎𝒎𝒆𝒓", "sign": "🏖"},
    2: {"name": "𝑲𝒊𝒎𝒐𝒏𝒐", "sign": "👘"},
    3: {"name": "𝑾𝒊𝒏𝒕𝒆𝒓", "sign": "☃️"},
    4: {"name": "𝑽𝒂𝒍𝒆𝒏𝒕𝒊𝒏𝒆", "sign": "💞"},
    5: {"name": "𝑺𝒄𝒉𝒐𝒐𝒍", "sign": "🎒"},
    6: {"name": "𝑯𝒂𝒍𝒍𝒐𝒘𝒆𝒆𝒏", "sign": "🎃"},
    7: {"name": "𝑮𝒂𝒎𝒆", "sign": "🎮"},
    8: {"name": "𝑻𝒖𝒙𝒆𝒅𝒐", "sign": "🎩"},
    9: {"name": "𝐃𝐮𝐨", "sign": "👥"},
    10: {"name": "𝑴𝒂𝒅𝒆", "sign": "🧹"},
    11: {"name": "𝑴𝒐𝒏𝒔𝒐𝒐𝒏", "sign": "☔"},
    12: {"name": "𝑩𝒖𝒏𝒏𝒚", "sign": "🐰"},
    13: {"name": "𝐆𝐫𝐨𝐮𝐩", "sign": "🤝🏻"},
    14: {"name": "𝑺𝒂𝒓𝒆𝒆", "sign": "🥻"},
    15: {"name": "𝑪𝒓𝒊𝒔𝒕𝒎𝒂𝒔", "sign": "🎄"},
    16: {"name": "𝑳𝒐𝒓𝒅", "sign": "👑"},
    17: None  # Skip event
}

RARITY_MAP = {
    1: "🟢 Comman",
    2: "🟣 Rare",
    3: "🟡 Legendary", 
    4: "💮 Special Edition", 
    5: "💫 Neon",
    6: "✨ Manga", 
    7: "🎭 Cosplay",
    8: "🎐 Celestial",
    9: "🔮 Premium edition",
    10: "💋 Erotic",
    11: "🌤 Summer",
    12: "☃️ Winter",
    13: "☔️ Monsoon",
    14: "💝 Valentine",
    15: "🎃 Halloween", 
    16: "🎄 Christmas",
    17: "🏵 Mythic",
    18: "🎗 Spacial Events",
    19: "🎥 Amv"
}


async def get_next_sequence_number(sequence_name):
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
    """Upload file to Catbox and return the URL"""
    url = "https://catbox.moe/user/api.php"
    
    try:
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            data.add_field('reqtype', 'fileupload')
            data.add_field('fileToUpload', file_bytes, filename=filename)
            
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.text()
                    return result.strip()
                else:
                    return None
    except Exception as e:
        print(f"Catbox upload error: {e}")
        return None


async def create_character_entry(img_url, character_name, anime, rarity, event, user_id, user_name, context, is_new=True):
    """Helper function to create character entry in database and channel"""
    char_id = str(await get_next_sequence_number('character_id')).zfill(2)
    
    character = {
        'img_url': img_url,
        'id': char_id,
        'name': character_name,
        'anime': anime,
        'rarity': rarity,
        'event': event
    }
    
    action_text = "𝑴𝒂𝒅𝒆" if is_new else "𝑼𝒑𝒅𝒂𝒕𝒆𝒅"
    
    caption = (
        f'<b>{char_id}:</b> {character_name}\n'
        f'<b>{anime}</b>\n'
        f'(<b>{rarity[0]} 𝙍𝘼𝙍𝙄𝙏𝙔:</b> {rarity[2:]})'
    )
    
    if event:
        caption += f'\n<b>Event:</b> {event["name"]} {event["sign"]}'
    
    caption += f'\n\n{action_text} 𝑩𝒚 ➥ <a href="tg://user?id={user_id}">{user_name}</a>'
    
    try:
        message = await context.bot.send_photo(
            chat_id=CHARA_CHANNEL_ID,
            photo=img_url,
            caption=caption,
            parse_mode='HTML'
        )
        character['message_id'] = message.message_id
        await collection.insert_one(character)
        return True, '✅ Character added successfully!'
    except Exception as e:
        await collection.insert_one(character)
        return False, f"Character added to database but not uploaded to channel.\nError: {str(e)}"


# ------------------------- /UPLOAD COMMAND -------------------------
async def upload(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('Ask My Owner...')
        return

    try:
        # Check if replying to a photo/video
        if update.message.reply_to_message:
            reply_msg = update.message.reply_to_message
            
            # Check if reply contains photo or video
            if not (reply_msg.photo or reply_msg.video or reply_msg.document):
                await update.message.reply_text('Please reply to a photo or video!')
                return
            
            args = context.args
            if len(args) != 4:
                await update.message.reply_text(REPLY_UPLOAD_TEXT)
                return
            
            # Send processing message
            processing_msg = await update.message.reply_text('⏳ Uploading to Catbox...')
            
            try:
                # Get the file
                if reply_msg.photo:
                    file = await reply_msg.photo[-1].get_file()
                    filename = f"character_{update.effective_user.id}.jpg"
                elif reply_msg.video:
                    file = await reply_msg.video.get_file()
                    filename = f"character_{update.effective_user.id}.mp4"
                else:  # document
                    file = await reply_msg.document.get_file()
                    filename = reply_msg.document.file_name or f"character_{update.effective_user.id}"
                
                # Download file to bytes
                file_bytes = await file.download_as_bytearray()
                
                # Upload to Catbox
                img_url = await upload_to_catbox(io.BytesIO(file_bytes), filename)
                
                if not img_url:
                    await processing_msg.edit_text('❌ Failed to upload to Catbox. Please try again.')
                    return
                
                await processing_msg.edit_text(f'✅ Uploaded to Catbox!\n🔗 {img_url}\n\n⏳ Adding to database...')
                
                character_name = args[0].replace('-', ' ').title()
                anime = args[1].replace('-', ' ').title()
                
                try:
                    rarity = RARITY_MAP[int(args[2])]
                except (KeyError, ValueError):
                    await processing_msg.edit_text('Invalid rarity number. Please check format guide.')
                    return
                
                try:
                    event_choice = int(args[3])
                    event = EVENT_MAPPING.get(event_choice)
                except (ValueError, KeyError):
                    await processing_msg.edit_text('Invalid event number. Please check format guide.')
                    return
                
                success, message = await create_character_entry(
                    img_url, character_name, anime, rarity, event,
                    update.effective_user.id, update.effective_user.first_name,
                    context
                )
                
                await processing_msg.edit_text(message)
                
            except Exception as e:
                await processing_msg.edit_text(f'❌ Error: {str(e)}')
                return
        
        else:
            # Original URL-based upload
            args = context.args
            if len(args) != 5:
                await update.message.reply_text(WRONG_FORMAT_TEXT)
                return

            img_url = args[0]
            character_name = args[1].replace('-', ' ').title()
            anime = args[2].replace('-', ' ').title()

            try:
                urllib.request.urlopen(img_url)
            except Exception:
                await update.message.reply_text('Invalid URL.')
                return

            try:
                rarity = RARITY_MAP[int(args[3])]
            except (KeyError, ValueError):
                await update.message.reply_text('Invalid rarity number. Please check format guide.')
                return

            try:
                event_choice = int(args[4])
                event = EVENT_MAPPING.get(event_choice)
            except (ValueError, KeyError):
                await update.message.reply_text('Invalid event number. Please check format guide.')
                return

            success, message = await create_character_entry(
                img_url, character_name, anime, rarity, event,
                update.effective_user.id, update.effective_user.first_name,
                context
            )
            
            await update.message.reply_text(message)

    except Exception as e:
        await update.message.reply_text(
            f'❌ Character Upload Failed.\nError: {str(e)}\nContact: {SUPPORT_CHAT}'
        )


# ------------------------- /DELETE COMMAND -------------------------
async def delete(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('Ask my Owner to use this Command...')
        return

    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text('Incorrect format. Use: /delete ID')
            return

        character = await collection.find_one_and_delete({'id': args[0]})

        if character:
            try:
                await context.bot.delete_message(
                    chat_id=CHARA_CHANNEL_ID, message_id=character['message_id']
                )
            except Exception:
                pass  # Message might already be deleted
            await update.message.reply_text('✅ Character deleted successfully.')
        else:
            await update.message.reply_text('Character not found in database.')
    except Exception as e:
        await update.message.reply_text(f'Error: {str(e)}')


# ------------------------- /UPDATE COMMAND -------------------------
async def update_character(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('You do not have permission to use this command.')
        return

    try:
        args = context.args
        if len(args) != 3:
            await update.message.reply_text('Incorrect format. Use: /update id field new_value')
            return

        char_id, field, new_value = args
        character = await collection.find_one({'id': char_id})

        if not character:
            await update.message.reply_text('Character not found.')
            return

        valid_fields = ['img_url', 'name', 'anime', 'rarity', 'event']
        if field not in valid_fields:
            await update.message.reply_text(
                f'Invalid field. Choose from: {", ".join(valid_fields)}'
            )
            return

        if field in ['name', 'anime']:
            new_value = new_value.replace('-', ' ').title()
        elif field == 'rarity':
            try:
                new_value = RARITY_MAP[int(new_value)]
            except (KeyError, ValueError):
                await update.message.reply_text('Invalid rarity number.')
                return
        elif field == 'event':
            try:
                new_value = EVENT_MAPPING[int(new_value)]
            except (KeyError, ValueError):
                await update.message.reply_text('Invalid event number.')
                return

        await collection.find_one_and_update({'id': char_id}, {'$set': {field: new_value}})

        # Refresh character data
        character = await collection.find_one({'id': char_id})

        # Update message caption or photo
        if field == 'img_url':
            try:
                await context.bot.delete_message(chat_id=CHARA_CHANNEL_ID, message_id=character['message_id'])
            except Exception:
                pass
            
            caption = (
                f'<b>{character["id"]}:</b> {character["name"]}\n'
                f'<b>{character["anime"]}</b>\n'
                f'(<b>{character["rarity"][0]} 𝙍𝘼𝙍𝙄𝙏𝙔:</b> {character["rarity"][2:]})'
            )
            
            if character.get("event"):
                caption += f'\n<b>Event:</b> {character["event"]["name"]} {character["event"]["sign"]}'
            
            caption += (
                f'\n\n𝑼𝒑𝒅𝒂𝒕𝒆𝒅 𝑩𝒚 ➥ <a href="tg://user?id={update.effective_user.id}">'
                f'{update.effective_user.first_name}</a>'
            )
            
            message = await context.bot.send_photo(
                chat_id=CHARA_CHANNEL_ID,
                photo=new_value,
                caption=caption,
                parse_mode='HTML'
            )
            await collection.find_one_and_update(
                {'id': char_id}, {'$set': {'message_id': message.message_id}}
            )
        else:
            caption = (
                f'<b>{character["id"]}:</b> {character["name"]}\n'
                f'<b>{character["anime"]}</b>\n'
                f'(<b>{character["rarity"][0]} 𝙍𝘼𝙍𝙄𝙏𝙔:</b> {character["rarity"][2:]})\n'
            )
            if character.get("event"):
                caption += f'<b>Event:</b> {character["event"]["name"]} {character["event"]["sign"]}\n'
            
            caption += (
                f'\n𝑼𝒑𝒅𝒂𝒕𝒆𝒅 𝑩𝒚 ➥ <a href="tg://user?id={update.effective_user.id}">'
                f'{update.effective_user.first_name}</a>'
            )

            try:
                await context.bot.edit_message_caption(
                    chat_id=CHARA_CHANNEL_ID,
                    message_id=character['message_id'],
                    caption=caption,
                    parse_mode='HTML'
                )
            except Exception as e:
                await update.message.reply_text(f'Note: Could not update channel message: {str(e)}')

        await update.message.reply_text('✅ Character updated successfully.')

    except Exception as e:
        await update.message.reply_text(f'Error: {str(e)}')


# ------------------------- HANDLER REGISTRATION -------------------------
application.add_handler(CommandHandler('upload', upload, block=False))
application.add_handler(CommandHandler('delete', delete, block=False))
application.add_handler(CommandHandler('update', update_character, block=False))