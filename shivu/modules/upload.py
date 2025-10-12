import urllib.request
from pymongo import ReturnDocument
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu.modules.database.sudo import is_user_sudo
from shivu import application, collection, db, CHARA_CHANNEL_ID, SUPPORT_CHAT, sudo_users


WRONG_FORMAT_TEXT = """Wrong ❌️ format...  
Example: `/upload Img_url muzan-kibutsuji Demon-slayer 3 1`

Format:  
img_url character-name anime-name rarity-number event-number  

Use rarity number accordingly:  
1 🟢 Common  
2 🟣 Rare  
3 🟡 Legendary  
4 💮 Special Edition  
5 🔮 Premium Edition  
6 🎗️ Supreme  
7 🧜🏻‍♀️ Mermaid  

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


# ------------------------- /UPLOAD COMMAND -------------------------
async def upload(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('Ask My Owner...')
        return

    try:
        args = context.args
        if len(args) != 5:
            await update.message.reply_text(WRONG_FORMAT_TEXT)
            return

        img_url = args[0]
        character_name = args[1].replace('-', ' ').title()
        anime = args[2].replace('-', ' ').title()

        try:
            urllib.request.urlopen(img_url)
        except:
            await update.message.reply_text('Invalid URL.')
            return

        rarity_map = {
            1: "🟢 Common",
            2: "🟣 Rare",
            3: "🟡 Legendary",
            4: "💮 Special Edition",
            5: "🔮 Premium Edition",
            6: "🎗️ Supreme",
            7: "🧜🏻‍♀️ Mermaid"
        }

        try:
            rarity = rarity_map[int(args[3])]
        except KeyError:
            await update.message.reply_text('Invalid rarity number. Please check format guide.')
            return

        event_choice = int(args[4])
        event = EVENT_MAPPING.get(event_choice)

        char_id = str(await get_next_sequence_number('character_id')).zfill(2)

        character = {
            'img_url': img_url,
            'id': char_id,
            'name': character_name,
            'anime': anime,
            'rarity': rarity,
            'event': event
        }

        try:
            message = await context.bot.send_photo(
                chat_id=CHARA_CHANNEL_ID,
                photo=img_url,
                caption=f'<b>{char_id}:</b> {character_name}\n'
                        f'<b>{anime}</b>\n'
                        f'(<b>{rarity[0]} 𝙍𝘼𝙍𝙄𝙏𝙔:</b> {rarity[2:]})'
                        f'{f"\n<b>Event:</b> {event["name"]} {event["sign"]}" if event else ""}'
                        f'\n\n𝑨𝒅𝒅𝒆𝒅 𝑩𝒚 ➥ <a href="tg://user?id={update.effective_user.id}">'
                        f'{update.effective_user.first_name}</a>',
                parse_mode='HTML'
            )
            character['message_id'] = message.message_id
            await collection.insert_one(character)
            await update.message.reply_text('✅ Character added successfully!')
        except:
            await collection.insert_one(character)
            await update.message.reply_text("Character added but not uploaded to channel.")

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
            await context.bot.delete_message(
                chat_id=CHARA_CHANNEL_ID, message_id=character['message_id']
            )
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
            rarity_map = {
                1: "🟢 Common",
                2: "🟣 Rare",
                3: "🟡 Legendary",
                4: "💮 Special Edition",
                5: "🔮 Premium Edition",
                6: "🎗️ Supreme",
                7: "🧜🏻‍♀️ Mermaid"
            }
            try:
                new_value = rarity_map[int(new_value)]
            except KeyError:
                await update.message.reply_text('Invalid rarity number.')
                return
        elif field == 'event':
            try:
                new_value = EVENT_MAPPING[int(new_value)]
            except KeyError:
                await update.message.reply_text('Invalid event number.')
                return

        await collection.find_one_and_update({'id': char_id}, {'$set': {field: new_value}})

        # Update message caption or photo
        if field == 'img_url':
            await context.bot.delete_message(chat_id=CHARA_CHANNEL_ID, message_id=character['message_id'])
            message = await context.bot.send_photo(
                chat_id=CHARA_CHANNEL_ID,
                photo=new_value,
                caption=f'<b>{character["id"]}:</b> {character["name"]}\n'
                        f'<b>{character["anime"]}</b>\n'
                        f'(<b>{character["rarity"][0]} 𝙍𝘼𝙍𝙄𝙏𝙔:</b> {character["rarity"][2:]})'
                        f'\n{character["event"]["sign"] if character.get("event") else ""}'
                        f'\n\n𝑼𝒑𝒅𝒂𝒕𝒆𝒅 𝑩𝒚 ➥ <a href="tg://user?id={update.effective_user.id}">'
                        f'{update.effective_user.first_name}</a>',
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
                caption += f'{character["event"]["sign"]} {character["event"]["name"]}\n'
            caption += (
                f'\n𝑼𝒑𝒅𝒂𝒕𝒆𝒅 𝑩𝒚 ➥ <a href="tg://user?id={update.effective_user.id}">'
                f'{update.effective_user.first_name}</a>'
            )

            await context.bot.edit_message_caption(
                chat_id=CHARA_CHANNEL_ID,
                message_id=character['message_id'],
                caption=caption,
                parse_mode='HTML'
            )

        await update.message.reply_text('✅ Character updated successfully.')

    except Exception as e:
        await update.message.reply_text(f'Error: {str(e)}')


# ------------------------- HANDLER REGISTRATION -------------------------
application.add_handler(CommandHandler('upload', upload, block=False))
application.add_handler(CommandHandler('delete', delete, block=False))
application.add_handler(CommandHandler('update', update_character, block=False))