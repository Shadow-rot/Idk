import re
import time
from html import escape
from cachetools import TTLCache
from pymongo import MongoClient, ASCENDING

# Telegram imports
from telegram import (
    Update, 
    InlineQueryResultPhoto, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    InlineQueryResultArticle, 
    InputTextMessageContent,
)
from telegram.ext import (
    Updater, 
    InlineQueryHandler, 
    CallbackQueryHandler, 
    CommandHandler, 
    CallbackContext
)

# Your own imports
from shivu import user_collection, collection, application, db 


# collection
db.characters.create_index([('id', ASCENDING)])
db.characters.create_index([('anime', ASCENDING)])
db.characters.create_index([('img_url', ASCENDING)])

# user_collection
db.user_collection.create_index([('characters.id', ASCENDING)])
db.user_collection.create_index([('characters.name', ASCENDING)])
db.user_collection.create_index([('characters.img_url', ASCENDING)])

all_characters_cache = TTLCache(maxsize=10000, ttl=36000)
user_collection_cache = TTLCache(maxsize=10000, ttl=60)

async def inlinequery(update: Update, context: CallbackContext) -> None:
    query = update.inline_query.query
    offset = int(update.inline_query.offset) if update.inline_query.offset else 0

    if query.startswith('collection.'):
        user_id, *search_terms = query.split(' ')[0].split('.')[1], ' '.join(query.split(' ')[1:])
        if user_id.isdigit():
            if user_id in user_collection_cache:
                user = user_collection_cache[user_id]
            else:
                user = await user_collection.find_one({'id': int(user_id)})
                user_collection_cache[user_id] = user

            if user:
                all_characters = list({v['id']:v for v in user['characters']}.values())
                if search_terms:
                    regex = re.compile(' '.join(search_terms), re.IGNORECASE)
                    all_characters = [character for character in all_characters if regex.search(character['name']) or regex.search(character['rarity']) or regex.search(character['id']) or regex.search(character['anime'])]
            else:
                all_characters = []
        else:
            all_characters = []
    else:
        if query:
            regex = re.compile(query, re.IGNORECASE)
            all_characters = list(await collection.find({"$or": [{"name": regex}, {"rarity": regex}, {"id": regex}, {"anime": regex}]}).to_list(length=None))
        else:
            if 'all_characters' in all_characters_cache:
                all_characters = all_characters_cache['all_characters']
            else:
                all_characters = list(await collection.find({}).to_list(length=None))
                all_characters_cache['all_characters'] = all_characters

    characters = all_characters[offset:offset+50]
    if len(characters) > 50:
        characters = characters[:50]
        next_offset = str(offset + 50)
    else:
        next_offset = str(offset + len(characters))

    results = []
    for character in characters:
        global_count = await user_collection.count_documents({'characters.id': character['id']})
        anime_characters = await collection.count_documents({'anime': character['anime']})

        if query.startswith('collection.'):
            user_character_count = sum(c['id'] == character['id'] for c in user['characters'])
            user_anime_characters = sum(c['anime'] == character['anime'] for c in user['characters'])
            caption = f"<b> Lᴏᴏᴋ Aᴛ <a href='tg://user?id={user['id']}'>{(escape(user.get('first_name', user['id'])))}</a>'s Wᴀɪғᴜ....!!</b>\n\n <b>{character['id']}:</b> {character['name']} x{user_character_count}\n<b>{character['anime']}</b> {user_anime_characters}/{anime_characters}\n﹙<b>{character['rarity'][0]} 𝙍𝘼𝙍𝙄𝙏𝙔:</b> {character['rarity'][2:]})\n\n"
        else:
            caption = (
            f"<b>Lᴏᴏᴋ Aᴛ Tʜɪs Wᴀɪғᴜ....!!</b>\n\n"
            f"<b>{character['id']}:</b> {character['name']}\n"
            f"<b>{character['anime']}</b>\n"
            f"﹙<b>{character['rarity'][0]} 𝙍𝘼𝙍𝙄𝙏𝙔:</b> {character['rarity'][2:]})"
        )

        # Initialize event_details as an empty string
        event_details = "" 

        if 'event' in character and character['event']:
            event_details = f"\n\n{character['event']['sign']} {character['event']['name']} {character['event']['sign']}"

        caption += f"\n\n<b>Gʟᴏʙᴀʟʟʏ Gʀᴀʙ {global_count} Times...</b>"
        caption += event_details # Now event_details is guaranteed to be defined

        # Add inline button for showing smashers
        button = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Top Grabbes", callback_data=f"show_smashers_{character['id']}")]]
        ) 

        results.append(
            InlineQueryResultPhoto(
                thumbnail_url=character['img_url'],
                id=f"{character['id']}_{time.time()}",
                photo_url=character['img_url'],
                caption=caption,
                parse_mode='HTML',
                reply_markup=button
            )
        )

    await update.inline_query.answer(results, next_offset=next_offset, cache_time=5)


async def show_smashers_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    character_id = query.data.split('_')[2]

    # Find the top 10 users who have the specified character
    top_users = await user_collection.aggregate([
        {'$match': {'characters.id': character_id}},
        {'$unwind': '$characters'},
        {'$match': {'characters.id': character_id}},
        {'$group': {'_id': '$id', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
        {'$limit': 10}
    ]).to_list(length=10)

    # Get usernames for each user in the top 10
    usernames = []
    for user_info in top_users:
        user_id = user_info['_id']
        try:
            user = await context.bot.get_chat(user_id)
            first_name = user.first_name
            usernames.append(user.username if user.username else f"➥ <a href='tg://user?id={user_id}'>{escape(first_name)}</a>")
        except Exception as e:
            # Log the exception if needed
            print(f"Error fetching user data for ID {user_id}: {e}")
            usernames.append(f"➥ <a href='tg://user?id={user_id}'>User {user_id}</a>")

    # Construct the top 10 grabbers list
    smasher_text = "\n\n🏅 <b>Top 10 Grabbers</b>\n\n" + "\n".join(
        [f"{i + 1}. {usernames[i]} x{top_users[i]['count']}" for i in range(len(top_users))]
    )

    # Check if the message is a media message with a caption or a text message
    if query.message.caption is not None:
        # Media message with caption
        current_caption = query.message.caption or ""
        new_caption = current_caption + smasher_text
        await query.edit_message_caption(caption=new_caption, parse_mode='HTML')
    else:
        # Text message, no caption
        current_text = query.message.text or ""
        new_text = current_text + smasher_text
        await query.edit_message_text(text=new_text, parse_mode='HTML')


# Adding handlers to the application
application.add_handler(CallbackQueryHandler(show_smashers_callback, pattern=r'^show_smashers_'))
application.add_handler(InlineQueryHandler(inlinequery, block=False))