import re
import time
import random
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
    CommandHandler,
    CallbackContext
)

# Your own imports
from shivu import application, db, LOGGER
import traceback

# Database collections
collection = db['anime_characters_lol']
user_collection = db['user_collection_lmaoooo']

# Log chat ID
LOG_CHAT_ID = -1003071132623

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


# Inline query handler with favorite character priority
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
                    characters_dict = {}
                    for c in user.get('characters', []):
                        if isinstance(c, dict) and c.get('id'):
                            characters_dict[c.get('id')] = c
                    all_characters = list(characters_dict.values())

                    # Check if user has a favorite character
                    favorite_char = user.get('favorites')
                    
                    # If no search terms and user has favorite, show favorite first
                    if not search_terms and favorite_char and isinstance(favorite_char, dict):
                        # Remove favorite from all_characters if it exists
                        all_characters = [c for c in all_characters if c.get('id') != favorite_char.get('id')]
                        # Add favorite at the beginning
                        all_characters.insert(0, favorite_char)
                    
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

            # Check if this is user's favorite
            is_favorite = False
            if user and user.get('favorites'):
                fav = user.get('favorites')
                if isinstance(fav, dict) and fav.get('id') == char_id:
                    is_favorite = True

            # Build caption based on query type
            if query.startswith('collection.') and user:
                # User collection caption
                user_character_count = sum(1 for c in user.get('characters', []) if c.get('id') == char_id)
                user_anime_count = sum(1 for c in user.get('characters', []) if c.get('anime') == char_anime)
                anime_total = await get_anime_count(char_anime)

                user_first_name = user.get('first_name', 'User')
                user_id_int = user.get('id')

                # Add favorite indicator
                fav_indicator = "💖 " if is_favorite else ""

                                caption = (
                    f"<b>{fav_indicator}🔮 {to_small_caps('look at')} <a href='tg://user?id={user_id_int}'>{escape(user_first_name)}</a>{to_small_caps('s waifu')}</b>\n\n"
                    f"<b>🆔 {to_small_caps('id')}</b> <code>{char_id}</code>\n"
                    f"<b>🧬 {to_small_caps('name')}</b> <code>{escape(char_name)}</code> x{user_character_count}\n"
                    f"<b>📺 {to_small_caps('anime')}</b> <code>{escape(char_anime)}</code> {user_anime_count}/{anime_total}\n"
                    f"<b>{rarity_emoji} {to_small_caps('rarity')}</b> <code>{to_small_caps(rarity_text)}</code>"
                )
                
                if is_favorite:
                    caption += f"\n\n💖 <b>{to_small_caps('favorite character')}</b>"
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
        import traceback
        traceback.print_exc()
        await update.inline_query.answer([], next_offset="", cache_time=5)


# Callback to show top grabbers
async def show_smashers_callback(update: Update, context) -> None:
    """Show top 10 users who grabbed this character"""
    query = update.callback_query

    try:
        await query.answer()

        # Validate query data
        if not query.data or len(query.data.split('_')) < 3:
            await query.answer(to_small_caps("invalid data"), show_alert=True)
            return

        character_id = query.data.split('_')[2]

        # Get character info first
        character = await collection.find_one({'id': character_id})
        if not character:
            await query.answer(to_small_caps("character not found"), show_alert=True)
            return

        # Get all users who have this character
        users_with_char = await user_collection.find({
            'characters.id': character_id
        }).to_list(length=None)

        if not users_with_char:
            await query.answer(to_small_caps("no one has grabbed this character yet"), show_alert=True)
            return

        # Count characters for each user and sort
        user_counts = []
        for user in users_with_char:
            user_id = user.get('id')
            first_name = user.get('first_name', 'User')
            username = user.get('username')

            # Count how many times this user has this character
            count = sum(1 for char in user.get('characters', []) if char.get('id') == character_id)

            if count > 0:
                user_counts.append({
                    'id': user_id,
                    'first_name': first_name,
                    'username': username,
                    'count': count
                })

        # Sort by count descending
        user_counts.sort(key=lambda x: x['count'], reverse=True)

        # Get top 10
        top_users = user_counts[:10]

        if not top_users:
            await query.answer(to_small_caps("no grabbers found"), show_alert=True)
            return

        # Build top grabbers list
        grabbers_list = []
        for i, user_data in enumerate(top_users, 1):
            user_id = user_data.get('id')
            count = user_data.get('count', 0)
            first_name = user_data.get('first_name', 'User')
            username = user_data.get('username')

            # Build user link with mention
            if username:
                user_link = f"<a href='tg://user?id={user_id}'>{escape(first_name)}</a> (@{escape(username)})"
            else:
                user_link = f"<a href='tg://user?id={user_id}'>{escape(first_name)}</a>"

            # Medal emojis for top 3
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"
            else:
                medal = f"{i}"

            grabbers_list.append(f"{medal} {user_link} <b>x{count}</b>")

        # Get total global count
        total_grabbed = sum(u['count'] for u in user_counts)

        smasher_text = (
            f"\n\n<b>🏆 {to_small_caps('top 10 grabbers')}</b>\n"
            f"<b>{to_small_caps('total grabbed')} {total_grabbed} {to_small_caps('times')}</b>\n\n"
            + "\n".join(grabbers_list)
        )

        # Check if message and caption exist
        if not query.message:
            await query.answer(to_small_caps("message not found"), show_alert=True)
            return

        # Get original caption
        original_caption = query.message.caption if query.message.caption else query.message.text

        if not original_caption:
            await query.answer(to_small_caps("caption not found"), show_alert=True)
            return

        # Remove old grabbers section if exists
        if '🏆' in original_caption:
            original_caption = original_caption.split('\n\n🏆')[0]

        new_caption = original_caption + smasher_text

        # Truncate if too long (Telegram limit is 1024 for captions)
        if len(new_caption) > 1020:
            # Keep top 5 only
            grabbers_list_short = grabbers_list[:5]
            smasher_text = (
                f"\n\n<b>🏆 {to_small_caps('top 5 grabbers')}</b>\n"
                f"<b>{to_small_caps('total grabbed')} {total_grabbed} {to_small_caps('times')}</b>\n\n"
                + "\n".join(grabbers_list_short)
            )
            new_caption = original_caption + smasher_text

        # Edit message caption
        try:
            if query.message.caption:
                await query.edit_message_caption(
                    caption=new_caption,
                    parse_mode='HTML',
                    reply_markup=query.message.reply_markup
                )
            else:
                await query.edit_message_text(
                    text=new_caption,
                    parse_mode='HTML',
                    reply_markup=query.message.reply_markup
                )
        except Exception as edit_error:
            print(f"Error editing message: {edit_error}")
            # Try without reply_markup
            try:
                if query.message.caption:
                    await query.edit_message_caption(
                        caption=new_caption,
                        parse_mode='HTML'
                    )
                else:
                    await query.edit_message_text(
                        text=new_caption,
                        parse_mode='HTML'
                    )
            except:
                await query.answer(to_small_caps("could not update message"), show_alert=True)

    except Exception as e:
        print(f"Error showing grabbers: {e}")
        import traceback
        traceback.print_exc()
        try:
            await query.answer(to_small_caps("error loading top grabbers"), show_alert=True)
        except:
            pass


# FAV COMMAND
async def fav(update: Update, context: CallbackContext) -> None:
    """Set a character as favorite"""
    user_id = update.effective_user.id

    LOGGER.info(f"[FAV] Command called by user {user_id}")

    if not context.args:
        await update.message.reply_text('𝙋𝙡𝙚𝙖𝙨𝙚 𝙥𝙧𝙤𝙫𝙞𝙙𝙚 𝙒𝘼𝙄𝙁𝙐 𝙞𝙙...')
        return

    character_id = str(context.args[0])

    try:
        user = await user_collection.find_one({'id': user_id})
        if not user:
            LOGGER.warning(f"[FAV] User {user_id} not found in database")
            await update.message.reply_text('𝙔𝙤𝙪 𝙝𝙖𝙫𝙚 𝙣𝙤𝙩 𝙂𝙤𝙩 𝘼𝙣𝙮 𝙒𝘼𝙄𝙁𝙐 𝙮𝙚𝙩...')
            return

        character = next(
            (c for c in user.get('characters', []) if str(c.get('id')) == character_id),
            None
        )

        if not character:
            LOGGER.warning(f"[FAV] Character {character_id} not found for user {user_id}")
            await update.message.reply_text('𝙏𝙝𝙞𝙨 𝙒𝘼𝙄𝙁𝙐 𝙞𝙨 𝙉𝙤𝙩 𝙄𝙣 𝙮𝙤𝙪𝙧 𝙒𝘼𝙄𝙁𝙐 𝙡𝙞𝙨𝙩')
            return

        # Create confirmation buttons
        buttons = [
            [
                InlineKeyboardButton("✅ ʏᴇs", callback_data=f"fc_{user_id}_{character_id}"),
                InlineKeyboardButton("❌ ɴᴏ", callback_data=f"fx_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)

        await update.message.reply_photo(
            photo=character.get("img_url", ""),
            caption=(
                f"<b>💖 ᴅᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴍᴀᴋᴇ ᴛʜɪs ᴡᴀɪғᴜ ʏᴏᴜʀ ғᴀᴠᴏʀɪᴛᴇ?</b>\n\n"
                f"✨ <b>ɴᴀᴍᴇ:</b> <code>{character.get('name', 'Unknown')}</code>\n"
                f"📺 <b>ᴀɴɪᴍᴇ:</b> <code>{character.get('anime', 'Unknown')}</code>\n"
                f"🆔 <b>ɪᴅ:</b> <code>{character.get('id', 'Unknown')}</code>"
            ),
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

        LOGGER.info(f"[FAV] Confirmation message sent for user {user_id}, character {character_id}")

    except Exception as e:
        LOGGER.error(f"[FAV ERROR] Command failed: {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text('ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴡʜɪʟᴇ ᴘʀᴏᴄᴇssɪɴɢ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ.')


async def handle_fav_callback(update: Update, context: CallbackContext) -> None:
    """Handle favorite button callbacks"""
    query = update.callback_query

    try:
        LOGGER.info(f"[FAV CALLBACK] Received callback: {query.data} from user {query.from_user.id}")

        # Extract data from callback
        data = query.data

        # Check if it's a fav callback
        if not (data.startswith('fc_') or data.startswith('fx_')):
            LOGGER.info(f"[FAV CALLBACK] Not a fav callback: {data}")
            return

        # Parse callback data
        parts = data.split('_')
        LOGGER.info(f"[FAV CALLBACK] Parsed parts: {parts}")

        if len(parts) < 2:
            LOGGER.error(f"[FAV CALLBACK] Malformed data: {data}")
            await query.answer("❌ ɪɴᴠᴀʟɪᴅ ᴄᴀʟʟʙᴀᴄᴋ ᴅᴀᴛᴀ!", show_alert=True)
            return

        action_code = parts[0]  # 'fc' (confirm) or 'fx' (cancel)

        if action_code == 'fc':  # Confirm
            if len(parts) != 3:
                LOGGER.error(f"[FAV CALLBACK] Invalid parts length for confirm: {len(parts)}")
                await query.answer("❌ ɪɴᴠᴀʟɪᴅ ᴅᴀᴛᴀ!", show_alert=True)
                return

            try:
                user_id = int(parts[1])
                character_id = str(parts[2])
            except ValueError as ve:
                LOGGER.error(f"[FAV CALLBACK] Error parsing user_id or character_id: {ve}")
                await query.answer("❌ ɪɴᴠᴀʟɪᴅ ᴅᴀᴛᴀ ғᴏʀᴍᴀᴛ!", show_alert=True)
                return

            LOGGER.info(f"[FAV CALLBACK] Processing confirmation - user={user_id}, char={character_id}")

            # Verify user
            if query.from_user.id != user_id:
                LOGGER.warning(f"[FAV CALLBACK] Unauthorized access by {query.from_user.id} for user {user_id}")
                await query.answer("⚠️ ᴛʜɪs ɪs ɴᴏᴛ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ!", show_alert=True)
                return

            # Get user and character
            LOGGER.info(f"[FAV CALLBACK] Fetching user from database...")
            user = await user_collection.find_one({'id': user_id})
            if not user:
                LOGGER.error(f"[FAV CALLBACK] User {user_id} not found in database")
                await query.answer("❌ ᴜsᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ!", show_alert=True)
                return

            LOGGER.info(f"[FAV CALLBACK] User found, searching for character...")
            character = next(
                (c for c in user.get('characters', []) if str(c.get('id')) == character_id),
                None
            )

            if not character:
                LOGGER.error(f"[FAV CALLBACK] Character {character_id} not found for user {user_id}")
                await query.answer("❌ ᴄʜᴀʀᴀᴄᴛᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ!", show_alert=True)
                return

            LOGGER.info(f"[FAV CALLBACK] Character found, updating database...")
            # Update favorite character
            result = await user_collection.update_one(
                {'id': user_id},
                {'$set': {'favorites': character}}
            )

            LOGGER.info(f"[FAV CALLBACK] Database update result: matched={result.matched_count}, modified={result.modified_count}")

            if result.matched_count == 0:
                LOGGER.error(f"[FAV CALLBACK] Failed to update database - no user matched")
                await query.answer("❌ ғᴀɪʟᴇᴅ ᴛᴏ ᴜᴘᴅᴀᴛᴇ ᴅᴀᴛᴀʙᴀsᴇ!", show_alert=True)
                return

            # Clear user cache to force refresh
            if str(user_id) in user_collection_cache:
                del user_collection_cache[str(user_id)]

            # Get rarity information
            rarity = character.get('rarity', '🟢 Common')
            if isinstance(rarity, str):
                rarity_parts = rarity.split(' ', 1)
                rarity_emoji = rarity_parts[0] if len(rarity_parts) > 0 else '🟢'
                rarity_text = rarity_parts[1] if len(rarity_parts) > 1 else 'Common'
            else:
                rarity_emoji = '🟢'
                rarity_text = 'Common'

            # Answer the callback query
            await query.answer("✅ ғᴀᴠᴏʀɪᴛᴇ sᴇᴛ sᴜᴄᴄᴇssғᴜʟʟʏ!", show_alert=False)

            # Edit message with success
            LOGGER.info(f"[FAV CALLBACK] Editing message with success caption...")
            await query.edit_message_caption(
                caption=(
                    f"<b>✅ sᴜᴄᴄᴇssғᴜʟʟʏ sᴇᴛ ᴀs ғᴀᴠᴏʀɪᴛᴇ!</b>\n\n"
                    f"💖 <b>ɴᴀᴍᴇ:</b> <code>{character.get('name', 'Unknown')}</code>\n"
                    f"📺 <b>ᴀɴɪᴍᴇ:</b> <code>{character.get('anime', 'Unknown')}</code>\n"
                    f"{rarity_emoji} <b>ʀᴀʀɪᴛʏ:</b> <code>{rarity_text}</code>\n"
                    f"🆔 <b>ɪᴅ:</b> <code>{character.get('id', 'Unknown')}</code>"
                ),
                parse_mode='HTML'
            )

            # Send log to log chat
            try:
                log_message = (
                    f"<b>💖 FAVORITE SET</b>\n\n"
                    f"👤 <b>User:</b> <a href='tg://user?id={user_id}'>{escape(query.from_user.first_name)}</a> (<code>{user_id}</code>)\n"
                    f"🎀 <b>Character:</b> <code>{character.get('name', 'Unknown')}</code>\n"
                    f"📺 <b>Anime:</b> <code>{character.get('anime', 'Unknown')}</code>\n"
                    f"{rarity_emoji} <b>Rarity:</b> <code>{rarity_text}</code>\n"
                    f"🆔 <b>Character ID:</b> <code>{character.get('id', 'Unknown')}</code>"
                )

                await context.bot.send_photo(
                    chat_id=LOG_CHAT_ID,
                    photo=character.get('img_url', ''),
                    caption=log_message,
                    parse_mode='HTML'
                )
                LOGGER.info(f"[FAV CALLBACK] Log sent to {LOG_CHAT_ID}")
            except Exception as log_error:
                LOGGER.error(f"[FAV CALLBACK] Failed to send log: {log_error}")

            LOGGER.info(f"[FAV CALLBACK] Successfully set favorite for user {user_id}")

        elif action_code == 'fx':  # Cancel
            if len(parts) < 2:
                LOGGER.error(f"[FAV CALLBACK] Invalid parts for cancel: {len(parts)}")
                await query.answer("❌ ɪɴᴠᴀʟɪᴅ ᴅᴀᴛᴀ!", show_alert=True)
                return

            try:
                user_id = int(parts[1])
            except ValueError as ve:
                LOGGER.error(f"[FAV CALLBACK] Error parsing user_id for cancel: {ve}")
                await query.answer("❌ ɪɴᴠᴀʟɪᴅ ᴅᴀᴛᴀ ғᴏʀᴍᴀᴛ!", show_alert=True)
                return

            # Verify user
            if query.from_user.id != user_id:
                await query.answer("⚠️ ᴛʜɪs ɪs ɴᴏᴛ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ!", show_alert=True)
                return

            await query.answer("❌ ᴀᴄᴛɪᴏɴ ᴄᴀɴᴄᴇʟᴇᴅ", show_alert=False)
            await query.edit_message_caption(
                caption="❌ ᴀᴄᴛɪᴏɴ ᴄᴀɴᴄᴇʟᴇᴅ. ɴᴏ ᴄʜᴀɴɢᴇs ᴍᴀᴅᴇ.",
                parse_mode='HTML'
            )
            LOGGER.info(f"[FAV CALLBACK] Action cancelled by user {user_id}")

    except Exception as e:
        LOGGER.error(f"[FAV CALLBACK] Callback handler failed with error: {e}")
        LOGGER.error(f"[FAV CALLBACK] Full traceback: {traceback.format_exc()}")
        try:
            await query.answer(f"❌ ᴇʀʀᴏʀ: {str(e)[:100]}", show_alert=True)
        except Exception as answer_error:
            LOGGER.error(f"[FAV CALLBACK] Failed to send error answer: {answer_error}")


# Add handlers
application.add_handler(InlineQueryHandler(inlinequery, block=False))
application.add_handler(CallbackQueryHandler(show_smashers_callback, pattern=r'^show_smashers_', block=False))
application.add_handler(CommandHandler('fav', fav, block=False))
application.add_handler(CallbackQueryHandler(handle_fav_callback, pattern="^f[cx]_", block=False))

LOGGER.info("[INLINE & FAV] All handlers registered successfully")