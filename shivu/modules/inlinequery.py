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
    CallbackQueryHandler,
)

# Your own imports
from shivu import application, db

# Database collections
collection = db['anime_characters_lol']
user_collection = db['user_collection_lmaoooo']

# Create indexes for better performance
try:
    collection.create_index([('id', ASCENDING)])
    collection.create_index([('anime', ASCENDING)])
    collection.create_index([('name', ASCENDING)])
    collection.create_index([('rarity', ASCENDING)])
    user_collection.create_index([('id', ASCENDING)])
    user_collection.create_index([('characters.id', ASCENDING)])
except Exception as e:
    print(f"Index creation error: {e}")

# Caches
all_characters_cache = TTLCache(maxsize=10000, ttl=36000)
user_collection_cache = TTLCache(maxsize=10000, ttl=60)
character_count_cache = TTLCache(maxsize=10000, ttl=300)

# Small caps conversion
def to_small_caps(text):
    small_caps_map = {
        'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ',
        'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ',
        's': 's', 't': 'ᴛ', 'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
        'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ғ', 'G': 'ɢ', 'H': 'ʜ', 'I': 'ɪ',
        'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ', 'O': 'ᴏ', 'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ',
        'S': 's', 'T': 'ᴛ', 'U': 'ᴜ', 'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x', 'Y': 'ʏ', 'Z': 'ᴢ',
    }
    return ''.join(small_caps_map.get(c, c) for c in text)


# ------------------- Helper functions -------------------

async def get_global_count(character_id: str) -> int:
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


# ------------------- Inline Query -------------------

async def inlinequery(update: Update, context) -> None:
    """Handle inline character search"""
    query = update.inline_query.query
    offset = int(update.inline_query.offset) if update.inline_query.offset else 0

    all_characters = []
    user = None

    try:
        # Searching user collection
        if query.startswith('collection.'):
            parts = query.split(' ', 1)
            user_id = parts[0].split('.')[1]
            search_terms = parts[1] if len(parts) > 1 else ''

            if user_id.isdigit():
                user_id_int = int(user_id)
                user = user_collection_cache.get(user_id) or await user_collection.find_one({'id': user_id_int})
                if user:
                    user_collection_cache[user_id] = user
                    characters_dict = {c.get('id'): c for c in user.get('characters', []) if isinstance(c, dict)}
                    all_characters = list(characters_dict.values())
                    if search_terms:
                        regex = re.compile(search_terms, re.IGNORECASE)
                        all_characters = [
                            c for c in all_characters
                            if regex.search(c.get('name', ''))
                            or regex.search(c.get('rarity', ''))
                            or regex.search(c.get('anime', ''))
                            or regex.search(c.get('id', ''))
                        ]
        else:
            # Global search
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
                all_characters = all_characters_cache.get('all_characters') or await collection.find({}).limit(200).to_list(length=200)
                all_characters_cache['all_characters'] = all_characters

        # Pagination
        characters = all_characters[offset:offset+50]
        next_offset = str(offset + 50) if len(all_characters) > offset + 50 else ""

        results = []
        for character in characters:
            char_id = character.get('id')
            if not char_id:
                continue

            char_name = character.get('name', 'Unknown')
            char_anime = character.get('anime', 'Unknown')
            char_rarity = character.get('rarity', '🟢 Common')
            char_img = character.get('img_url', '')

            rarity_parts = char_rarity.split(' ', 1)
            rarity_emoji = rarity_parts[0] if rarity_parts else '🟢'
            rarity_text = rarity_parts[1] if len(rarity_parts) > 1 else 'Common'

            # Caption
            if query.startswith('collection.') and user:
                user_character_count = sum(1 for c in user.get('characters', []) if c.get('id') == char_id)
                user_anime_count = sum(1 for c in user.get('characters', []) if c.get('anime') == char_anime)
                anime_total = await get_anime_count(char_anime)
                user_first_name = user.get('first_name', 'User')
                user_id_int = user.get('id')

                caption = (
                    f"<b>{to_small_caps('look at')} <a href='tg://user?id={user_id_int}'>{escape(user_first_name)}</a>"
                    f"{to_small_caps('s waifu')}</b>\n\n"
                    f"<b>{to_small_caps('id')}</b> <code>{char_id}</code>\n"
                    f"<b>{to_small_caps('name')}</b> <code>{escape(char_name)}</code> x{user_character_count}\n"
                    f"<b>{to_small_caps('anime')}</b> <code>{escape(char_anime)}</code> {user_anime_count}/{anime_total}\n"
                    f"<b>{rarity_emoji} {to_small_caps('rarity')}</b> <code>{to_small_caps(rarity_text)}</code>"
                )
            else:
                global_count = await get_global_count(char_id)
                caption = (
                    f"<b>🔮 {to_small_caps('look at this waifu')}</b>\n\n"
                    f"<b>🆔 {to_small_caps('id')}</b>: <code>{char_id}</code>\n"
                    f"<b>🧬 {to_small_caps('name')}</b>: <code>{escape(char_name)}</code>\n"
                    f"<b>📺 {to_small_caps('anime')}</b>: <code>{escape(char_anime)}</code>\n"
                    f"<b>{rarity_emoji} {to_small_caps('rarity')}</b>: <code>{to_small_caps(rarity_text)}</code>\n\n"
                    f"<b>🌍 {to_small_caps('globally grabbed')} {global_count} {to_small_caps('times')}</b>"
                )

            button = InlineKeyboardMarkup([[
                InlineKeyboardButton(f"🏆 {to_small_caps('top grabbers')}", callback_data=f"show_smashers_{char_id}")
            ]])

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
        import traceback
        traceback.print_exc()
        await update.inline_query.answer([], next_offset="", cache_time=5)


# ------------------- Callback -------------------

async def show_smashers_callback(update: Update, context) -> None:
    """Show top grabbers"""
    query = update.callback_query
    try:
        await query.answer()
        if not query.data or len(query.data.split('_')) < 3:
            await query.answer(to_small_caps("invalid data"), show_alert=True)
            return

        character_id = query.data.split('_')[2]
        character = await collection.find_one({'id': character_id})
        if not character:
            await query.answer(to_small_caps("character not found"), show_alert=True)
            return

        users_with_char = await user_collection.find({'characters.id': character_id}).to_list(length=None)
        if not users_with_char:
            await query.answer(to_small_caps("no one has grabbed this character yet"), show_alert=True)
            return

        user_counts = []
        for user in users_with_char:
            count = sum(1 for c in user.get('characters', []) if c.get('id') == character_id)
            if count > 0:
                user_counts.append({
                    'id': user.get('id'),
                    'first_name': user.get('first_name', 'User'),
                    'username': user.get('username'),
                    'count': count
                })
        user_counts.sort(key=lambda x: x['count'], reverse=True)
        top_users = user_counts[:10]

        grabbers_list = []
        for i, u in enumerate(top_users, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}"
            link = f"<a href='tg://user?id={u['id']}'>{escape(u['first_name'])}</a>"
            if u.get('username'):
                link += f" (@{escape(u['username'])})"
            grabbers_list.append(f"{medal} {link} <b>x{u['count']}</b>")

        total_grabbed = sum(u['count'] for u in user_counts)
        smasher_text = (
            f"\n\n<b>🏆 {to_small_caps('top 10 grabbers')}</b>\n"
            f"<b>{to_small_caps('total grabbed')} {total_grabbed} {to_small_caps('times')}</b>\n\n"
            + "\n".join(grabbers_list)
        )

        original_caption = query.message.caption or query.message.text
        if '🏆' in original_caption:
            original_caption = original_caption.split('\n\n🏆')[0]
        new_caption = original_caption + smasher_text
        if len(new_caption) > 1020:
            grabbers_list = grabbers_list[:5]
            smasher_text = (
                f"\n\n<b>🏆 {to_small_caps('top 5 grabbers')}</b>\n"
                f"<b>{to_small_caps('total grabbed')} {total_grabbed} {to_small_caps('times')}</b>\n\n"
                + "\n".join(grabbers_list)
            )
            new_caption = original_caption + smasher_text

        await query.edit_message_caption(caption=new_caption, parse_mode='HTML', reply_markup=query.message.reply_markup)

    except Exception as e:
        print(f"Error showing grabbers: {e}")
        await query.answer(to_small_caps("error loading top grabbers"), show_alert=True)


# ------------------- Register Handlers -------------------
application.add_handler(InlineQueryHandler(inlinequery, block=False))
application.add_handler(CallbackQueryHandler(show_smashers_callback, pattern=r'^show_smashers_', block=False))