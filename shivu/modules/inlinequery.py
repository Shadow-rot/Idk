import re
import time
from html import escape
from cachetools import TTLCache
from pymongo import ASCENDING

# Telegram imports
from telegram import (
    Update, 
    InlineQueryResultPhoto, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
)
from telegram.ext import (
    InlineQueryHandler, 
    CallbackQueryHandler
)

# Your own imports
from shivu import user_collection, collection, application, db

# Create indexes
db.characters.create_index([('id', ASCENDING)])
db.characters.create_index([('anime', ASCENDING)])
db.characters.create_index([('img_url', ASCENDING)])

db.user_collection.create_index([('characters.id', ASCENDING)])
db.user_collection.create_index([('characters.name', ASCENDING)])
db.user_collection.create_index([('characters.img_url', ASCENDING)])

# Caches
all_characters_cache = TTLCache(maxsize=10000, ttl=36000)
user_collection_cache = TTLCache(maxsize=10000, ttl=60)

# Helper function for emoji captions
def add_emoji_caption(character_name: str, base_caption: str) -> str:
    emoji_map = {
        '🎃': "🎃𝑯𝒆𝒍𝒍𝒐𝒘𝒆𝒆𝒏🎃",
        '👘': "👘𝑲𝒊𝒎𝒐𝒏𝒐👘",
        '☃️': "☃️𝑾𝒊𝒏𝒕𝒆𝒓☃️",
        '🐰': "🐰𝑩𝒖𝒏𝒏𝒚🐰",
        '🎮': "🎮𝑮𝒂𝒎𝒆🎮",
        '🎄': "🎄𝑪𝒓𝒊𝒔𝒕𝒎𝒂𝒔🎄",
        '🏖️': "🏖️𝑺𝒖𝒎𝒎𝒆𝒓🏖️",
        '🧹': "🧹𝑴𝒂𝒅𝒆🧹",
        '🥻': "🥻𝑺𝒂𝒓𝒆𝒆🥻",
        '☔': "☔𝑴𝒐𝒏𝒔𝒐𝒐𝒏☔",
        '🎒': "🎒𝑺𝒄𝒉𝒐𝒐𝒍🎒",
        '🎩': "🎩𝑻𝒖𝒙𝒆𝒅𝒐🎩",
        '👥': "👥𝐃𝐮𝐨👥",
        '🤝🏻': "🤝🏻𝐆𝐫𝐨𝐮𝐩🤝🏻",
        '👑': "👑𝑳𝒐𝒓𝒅👑",
        '💞': "💞𝑽𝒂𝒍𝒆𝒏𝒕𝒊𝒏𝒆💞",
    }
    for key, value in emoji_map.items():
        if key in character_name:
            return base_caption + f"\n\n{value}"
    return base_caption

# Inline query handler
async def inlinequery(update: Update, context) -> None:
    query = update.inline_query.query
    offset = int(update.inline_query.offset) if update.inline_query.offset else 0

    # Determine which characters to fetch
    all_characters = []
    if query.startswith('collection.'):
        parts = query.split(' ')
        user_id = parts[0].split('.')[1]
        search_terms = ' '.join(parts[1:]) if len(parts) > 1 else ''

        if user_id.isdigit():
            if user_id in user_collection_cache:
                user = user_collection_cache[user_id]
            else:
                user = await user_collection.find_one({'id': int(user_id)})
                user_collection_cache[user_id] = user

            if user:
                all_characters = list({v['id']: v for v in user['characters']}.values())
                if search_terms:
                    regex = re.compile(search_terms, re.IGNORECASE)
                    all_characters = [
                        c for c in all_characters 
                        if regex.search(c['name']) or regex.search(c['rarity']) or regex.search(c['id']) or regex.search(c['anime'])
                    ]
    else:
        if query:
            regex = re.compile(query, re.IGNORECASE)
            all_characters = list(await collection.find({
                "$or": [{"name": regex}, {"rarity": regex}, {"id": regex}, {"anime": regex}]
            }).to_list(length=None))
        else:
            if 'all_characters' in all_characters_cache:
                all_characters = all_characters_cache['all_characters']
            else:
                all_characters = list(await collection.find({}).to_list(length=None))
                all_characters_cache['all_characters'] = all_characters

    # Pagination
    characters = all_characters[offset:offset+50]
    next_offset = str(offset + len(characters)) if len(characters) < 50 else str(offset + 50)

    results = []
    for character in characters:
        global_count = await user_collection.count_documents({'characters.id': character['id']})
        anime_characters = await collection.count_documents({'anime': character['anime']})

        if query.startswith('collection.') and user_id.isdigit() and user:
            user_character_count = sum(c['id'] == character['id'] for c in user['characters'])
            user_anime_count = sum(c['anime'] == character['anime'] for c in user['characters'])
            caption = (
                f"<b>Look at <a href='tg://user?id={user['id']}'>{escape(user.get('first_name', user['id']))}</a>'s Waifu!</b>\n\n"
                f"<b>{character['id']}:</b> {character['name']} x{user_character_count}\n"
                f"<b>{character['anime']}</b> {user_anime_count}/{anime_characters}\n"
                f"﹙<b>{character['rarity'][0]} RARITY:</b> {character['rarity'][2:]})\n\n"
            )
        else:
            caption = (
                f"<b>Look at this Waifu!</b>\n\n"
                f"<b>{character['id']}:</b> {character['name']}\n"
                f"<b>{character['anime']}</b>\n"
                f"﹙<b>{character['rarity'][0]} RARITY:</b> {character['rarity'][2:]})\n\n"
                f"<b>Globally grabbed {global_count} times...</b>"
            )

        # Add emoji caption
        caption = add_emoji_caption(character['name'], caption)

        # Inline button
        button = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Top Grabbers", callback_data=f"show_smashers_{character['id']}")]]
        )

        results.append(
            InlineQueryResultPhoto(
                id=f"{character['id']}_{time.time()}",
                photo_url=character['img_url'],
                thumbnail_url=character['img_url'],
                caption=caption,
                parse_mode='HTML',
                reply_markup=button
            )
        )

    await update.inline_query.answer(results, next_offset=next_offset, cache_time=5)

# Callback to show top grabbers
async def show_smashers_callback(update: Update, context) -> None:
    query = update.callback_query
    character_id = query.data.split('_')[2]

    top_users = await user_collection.aggregate([
        {'$match': {'characters.id': character_id}},
        {'$unwind': '$characters'},
        {'$match': {'characters.id': character_id}},
        {'$group': {'_id': '$id', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
        {'$limit': 10}
    ]).to_list(length=10)

    usernames = []
    for u in top_users:
        user_id = u['_id']
        try:
            user = await context.bot.get_chat(user_id)
            first_name = user.first_name
            usernames.append(user.username if user.username else f"➥ <a href='tg://user?id={user_id}'>{escape(first_name)}</a>")
        except:
            usernames.append(f"➥ <a href='tg://user?id={user_id}'>User {user_id}</a>")

    smasher_text = "\n\n🏅 <b>Top 10 Grabbers</b>\n\n" + "\n".join(
        [f"{i+1}. {usernames[i]} x{top_users[i]['count']}" for i in range(len(top_users))]
    )

    if query.message.caption:
        await query.edit_message_caption(caption=query.message.caption + smasher_text, parse_mode='HTML')
    else:
        await query.edit_message_text(text=query.message.text + smasher_text, parse_mode='HTML')


# Add handlers
application.add_handler(InlineQueryHandler(inlinequery, block=False))
application.add_handler(CallbackQueryHandler(show_smashers_callback, pattern=r'^show_smashers_'))