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

# Create indexes for better performance
try:
    db.characters.create_index([('id', ASCENDING)])
    db.characters.create_index([('anime', ASCENDING)])
    db.characters.create_index([('name', ASCENDING)])
    db.characters.create_index([('rarity', ASCENDING)])
    
    db.user_collection.create_index([('id', ASCENDING)])
    db.user_collection.create_index([('characters.id', ASCENDING)])
    db.user_collection.create_index([('characters.name', ASCENDING)])
except Exception as e:
    print(f"Index creation error: {e}")

# Caches
all_characters_cache = TTLCache(maxsize=10000, ttl=36000)
user_collection_cache = TTLCache(maxsize=10000, ttl=60)
character_count_cache = TTLCache(maxsize=10000, ttl=300)

# Small caps conversion function
def to_small_caps(text):
    """Convert text to small caps"""
    small_caps_map = {
        'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ',
        'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ',
        's': 's', 't': 'ᴛ', 'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
        'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ғ', 'G': 'ɢ', 'H': 'ʜ', 'I': 'ɪ',
        'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ', 'O': 'ᴏ', 'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ',
        'S': 's', 'T': 'ᴛ', 'U': 'ᴜ', 'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x', 'Y': 'ʏ', 'Z': 'ᴢ',
        '0': '0', '1': '1', '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9'
    }
    return ''.join(small_caps_map.get(c, c) for c in text)

# Helper function for event captions
def get_event_caption(character: dict) -> str:
    """Get event caption with emoji"""
    event = character.get('event')
    if not event or not isinstance(event, dict):
        return ""
    
    event_name = event.get('name', '')
    event_sign = event.get('sign', '')
    
    if event_name and event_sign:
        return f"\n{event_sign} {to_small_caps('event')} {event_name} {event_sign}"
    return ""


async def get_global_count(character_id: str) -> int:
    """Get global grab count with caching"""
    cache_key = f"global_{character_id}"
    if cache_key in character_count_cache:
        return character_count_cache[cache_key]
    
    try:
        count = await user_collection.count_documents({'characters.id': character_id})
        character_count_cache[cache_key] = count
        return count
    except Exception as e:
        print(f"Error getting global count: {e}")
        return 0


async def get_anime_count(anime_name: str) -> int:
    """Get total characters in anime with caching"""
    cache_key = f"anime_{anime_name}"
    if cache_key in character_count_cache:
        return character_count_cache[cache_key]
    
    try:
        count = await collection.count_documents({'anime': anime_name})
        character_count_cache[cache_key] = count
        return count
    except Exception as e:
        print(f"Error getting anime count: {e}")
        return 0


# Inline query handler
async def inlinequery(update: Update, context) -> None:
    """Handle inline queries for character search"""
    query = update.inline_query.query
    offset = int(update.inline_query.offset) if update.inline_query.offset else 0

    # Determine which characters to fetch
    all_characters = []
    user = None
    user_id = None
    
    try:
        if query.startswith('collection.'):
            # User collection search
            parts = query.split(' ', 1)
            user_id = parts[0].split('.')[1]
            search_terms = parts[1] if len(parts) > 1 else ''

            if user_id.isdigit():
                user_id_int = int(user_id)
                
                # Get user from cache or database
                if user_id in user_collection_cache:
                    user = user_collection_cache[user_id]
                else:
                    user = await user_collection.find_one({'id': user_id_int})
                    if user:
                        user_collection_cache[user_id] = user

                if user:
                    # Get unique characters from user's collection
                    characters_dict = {c.get('id'): c for c in user.get('characters', []) if c.get('id')}
                    all_characters = list(characters_dict.values())
                    
                    # Apply search filter
                    if search_terms:
                        regex = re.compile(search_terms, re.IGNORECASE)
                        all_characters = [
                            c for c in all_characters 
                            if regex.search(c.get('name', '')) 
                            or regex.search(c.get('rarity', '')) 
                            or regex.search(c.get('id', '')) 
                            or regex.search(c.get('anime', ''))
                        ]
        else:
            # Global character search
            if query:
                regex = re.compile(re.escape(query), re.IGNORECASE)
                all_characters = await collection.find({
                    "$or": [
                        {"name": regex}, 
                        {"rarity": regex}, 
                        {"id": regex}, 
                        {"anime": regex}
                    ]
                }).to_list(length=200)
            else:
                # Get all characters
                if 'all_characters' in all_characters_cache:
                    all_characters = all_characters_cache['all_characters']
                else:
                    all_characters = await collection.find({}).limit(200).to_list(length=200)
                    all_characters_cache['all_characters'] = all_characters

        # Pagination
        characters = all_characters[offset:offset+50]
        has_more = len(all_characters) > offset + 50
        next_offset = str(offset + 50) if has_more else ""

        results = []
        for character in characters:
            char_id = character.get('id')
            if not char_id:
                continue

            char_name = character.get('name', 'Unknown')
            char_anime = character.get('anime', 'Unknown')
            char_rarity = character.get('rarity', '🟢 Common')
            char_img = character.get('img_url', '')

            # Extract rarity emoji and text
            if isinstance(char_rarity, str):
                rarity_parts = char_rarity.split(' ', 1)
                rarity_emoji = rarity_parts[0] if len(rarity_parts) > 0 else '🟢'
                rarity_text = rarity_parts[1] if len(rarity_parts) > 1 else 'Common'
            else:
                rarity_emoji = '🟢'
                rarity_text = 'Common'

            # Build caption based on query type
            if query.startswith('collection.') and user:
                # User collection caption
                user_character_count = sum(1 for c in user.get('characters', []) if c.get('id') == char_id)
                user_anime_count = sum(1 for c in user.get('characters', []) if c.get('anime') == char_anime)
                anime_total = await get_anime_count(char_anime)
                
                user_first_name = user.get('first_name', 'User')
                user_id_int = user.get('id')
                
                caption = (
                    f"<b>{to_small_caps('look at')} <a href='tg://user?id={user_id_int}'>{escape(user_first_name)}</a>{to_small_caps('s waifu')}</b>\n\n"
                    f"<b>{to_small_caps('id')}</b> <code>{char_id}</code>\n"
                    f"<b>{to_small_caps('name')}</b> <code>{escape(char_name)}</code> x{user_character_count}\n"
                    f"<b>{to_small_caps('anime')}</b> <code>{escape(char_anime)}</code> {user_anime_count}/{anime_total}\n"
                    f"<b>{rarity_emoji} {to_small_caps('rarity')}</b> <code>{to_small_caps(rarity_text)}</code>"
                )
            else:
                # Global search caption
                global_count = await get_global_count(char_id)
                
                caption = (
                    f"<b>{to_small_caps('look at this waifu')}</b>\n\n"
                    f"<b>{to_small_caps('id')}</b> <code>{char_id}</code>\n"
                    f"<b>{to_small_caps('name')}</b> <code>{escape(char_name)}</code>\n"
                    f"<b>{to_small_caps('anime')}</b> <code>{escape(char_anime)}</code>\n"
                    f"<b>{rarity_emoji} {to_small_caps('rarity')}</b> <code>{to_small_caps(rarity_text)}</code>\n\n"
                    f"<b>{to_small_caps('globally grabbed')} {global_count} {to_small_caps('times')}</b>"
                )

            # Add event info
            event_caption = get_event_caption(character)
            caption += event_caption

            # Inline button
            button = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    f"🏆 {to_small_caps('top grabbers')}", 
                    callback_data=f"show_smashers_{char_id}"
                )]
            ])

            results.append(
                InlineQueryResultPhoto(
                    id=f"{char_id}_{offset}_{time.time()}",
                    photo_url=char_img,
                    thumbnail_url=char_img,
                    caption=caption,
                    parse_mode='HTML',
                    reply_markup=button
                )
            )

        await update.inline_query.answer(results, next_offset=next_offset, cache_time=5)
        
    except Exception as e:
        print(f"Error in inline query: {e}")
        await update.inline_query.answer([], next_offset="", cache_time=5)


# Callback to show top grabbers
async def show_smashers_callback(update: Update, context) -> None:
    """Show top 10 users who grabbed this character"""
    query = update.callback_query
    await query.answer()
    
    try:
        character_id = query.data.split('_')[2]

        # Get top users who grabbed this character
        top_users = await user_collection.aggregate([
            {'$match': {'characters.id': character_id}},
            {'$unwind': '$characters'},
            {'$match': {'characters.id': character_id}},
            {'$group': {'_id': '$id', 'count': {'$sum': 1}, 'first_name': {'$first': '$first_name'}, 'username': {'$first': '$username'}}},
            {'$sort': {'count': -1}},
            {'$limit': 10}
        ]).to_list(length=10)

        if not top_users:
            await query.answer(to_small_caps("no one has grabbed this character yet"), show_alert=True)
            return

        # Build top grabbers list
        grabbers_list = []
        for i, user_data in enumerate(top_users, 1):
            user_id = user_data['_id']
            count = user_data['count']
            first_name = user_data.get('first_name', 'User')
            username = user_data.get('username')
            
            if username:
                user_link = f"<a href='https://t.me/{username}'>@{escape(username)}</a>"
            else:
                user_link = f"<a href='tg://user?id={user_id}'>{escape(first_name)}</a>"
            
            # Medal emojis for top 3
            medal = ""
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"
            else:
                medal = f"{i}."
            
            grabbers_list.append(f"{medal} {user_link} x{count}")

        smasher_text = f"\n\n<b>🏆 {to_small_caps('top 10 grabbers')}</b>\n\n" + "\n".join(grabbers_list)

        # Edit message caption
        if query.message.caption:
            new_caption = query.message.caption.split('\n\n🏆')[0] + smasher_text
            await query.edit_message_caption(caption=new_caption, parse_mode='HTML')
        else:
            await query.edit_message_text(text=query.message.text + smasher_text, parse_mode='HTML')
            
    except Exception as e:
        print(f"Error showing grabbers: {e}")
        await query.answer(to_small_caps("error loading top grabbers"), show_alert=True)


# Add handlers
application.add_handler(InlineQueryHandler(inlinequery, block=False))
application.add_handler(CallbackQueryHandler(show_smashers_callback, pattern=r'^show_smashers_', block=False))