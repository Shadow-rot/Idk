import re
import time
from html import escape
from cachetools import TTLCache
from pymongo import ASCENDING

# Telegram imports
from telegram import (
    Update, 
    InlineQueryResultPhoto,
    InlineQueryResultVideo,
    InlineQueryResultMpeg4Gif,
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
)
from telegram.ext import (
    InlineQueryHandler, 
    CallbackQueryHandler
)

# Your own imports
from shivu import application, db, LOGGER

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


def is_video_url(url):
    """Check if URL points to a video file (MP4, etc)"""
    if not url:
        return False
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']
    return any(url.lower().endswith(ext) for ext in video_extensions)


def is_gif_url(url):
    """Check if URL points to a GIF file"""
    if not url:
        return False
    return url.lower().endswith('.gif')


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
    """Handle inline queries for character search - supports both images and videos"""
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

                    # Get favorite character - handle both dict and string
                    favorite_char_data = user.get('favorites')
                    favorite_char = None

                    if favorite_char_data:
                        if isinstance(favorite_char_data, dict):
                            # Favorite is stored as character object
                            favorite_char = favorite_char_data
                            LOGGER.info(f"[INLINE] Favorite is dict: {favorite_char.get('name')}")
                        elif isinstance(favorite_char_data, str):
                            # Favorite is stored as character ID
                            favorite_char = next(
                                (c for c in all_characters if c.get('id') == favorite_char_data),
                                None
                            )
                            LOGGER.info(f"[INLINE] Favorite is string ID, found: {favorite_char.get('name') if favorite_char else 'None'}")

                    # If no search terms and user has favorite, show favorite FIRST
                    if not search_terms and favorite_char:
                        LOGGER.info(f"[INLINE] Moving favorite to first position: {favorite_char.get('name')}")
                        # Remove favorite from list if it exists
                        all_characters = [c for c in all_characters if c.get('id') != favorite_char.get('id')]
                        # Insert at beginning
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
            is_video = character.get('is_video', False)  # Check if it's a video

            # Auto-detect if is_video flag is missing
            if not is_video and char_img:
                is_video = is_video_url(char_img)

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
                elif isinstance(fav, str) and fav == char_id:
                    is_favorite = True

            # Build caption based on query type
            if query.startswith('collection.') and user:
                # User collection caption
                user_character_count = sum(1 for c in user.get('characters', []) if c.get('id') == char_id)
                user_anime_count = sum(1 for c in user.get('characters', []) if c.get('anime') == char_anime)
                anime_total = await get_anime_count(char_anime)

                user_first_name = user.get('first_name', 'User')
                user_id_int = user.get('id')

                # Add favorite indicator and media type
                fav_indicator = "💖 " if is_favorite else ""
                media_indicator = "🎥 " if is_video else "🖼 "

                caption = (
                    f"<b>{fav_indicator}{media_indicator}🔮 {to_small_caps('look at')} <a href='tg://user?id={user_id_int}'>{escape(user_first_name)}</a>{to_small_caps('s waifu')}</b>\n\n"
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
                media_indicator = "🎥 " if is_video else "🖼 "

                caption = (
                    f"<b>{media_indicator}🔮 {to_small_caps('look at this waifu')}</b>\n\n"
                    f"<b>🆔 {to_small_caps('id')}</b> : <code>{char_id}</code>\n"
                    f"<b>🧬 {to_small_caps('name')}</b> : <code>{escape(char_name)}</code>\n"
                    f"<b>📺 {to_small_caps('anime')}</b> : <code>{escape(char_anime)}</code>\n"
                    f"<b>{rarity_emoji} {to_small_caps('rarity')}</b> : <code>{to_small_caps(rarity_text)}</code>\n\n"
                    f"<b>🌍 {to_small_caps('globally grabbed')} {global_count} {to_small_caps('times')}</b>"
                )

            # Inline button
            button = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    f"🏆 {to_small_caps('top grabbers')}", 
                    callback_data=f"show_smashers_{char_id}"
                )]
            ])

            # Create appropriate inline result based on media type
            result_id = f"{char_id}_{offset}_{time.time()}"

            # Skip if no valid URL
            if not char_img:
                continue

            # For inline queries, we need to use cached file_id from channel messages
            # External URLs often fail with WEBPAGE_MEDIA_EMPTY error
            message_id = character.get('message_id')
            
            # If we have a message_id, we can use InlineQueryResultCachedPhoto/Video
            # This is more reliable than using external URLs
            try:
                if message_id:
                    # Try to get the file_id from the channel message
                    # This requires the bot to have access to the channel
                    try:
                        from shivu import CHARA_CHANNEL_ID
                        channel_message = await context.bot.get_chat(CHARA_CHANNEL_ID)
                        # We'll use the message_id to reference the media
                        # For now, fallback to URL method with better error handling
                    except:
                        pass
                
                # Use URL-based results with proper validation
                if is_video:
                    # For videos, only use if URL is from trusted sources
                    # Catbox, Imgur, Telegraph, etc.
                    trusted_domains = ['catbox.moe', 'i.imgur.com', 'telegra.ph', 'te.legra.ph']
                    is_trusted = any(domain in char_img.lower() for domain in trusted_domains)
                    
                    if is_gif_url(char_img):
                        # GIFs work better with MPEG4Gif
                        results.append(
                            InlineQueryResultMpeg4Gif(
                                id=result_id,
                                mpeg4_url=char_img,
                                thumbnail_url=char_img,
                                caption=caption,
                                parse_mode='HTML',
                                reply_markup=button
                            )
                        )
                    elif is_trusted:
                        # Only use video result for trusted domains
                        results.append(
                            InlineQueryResultVideo(
                                id=result_id,
                                video_url=char_img,
                                mime_type='video/mp4',
                                thumbnail_url=char_img,
                                title=f"{char_name}",
                                description=f"{char_anime} - {rarity_text}",
                                caption=caption,
                                parse_mode='HTML',
                                reply_markup=button,
                                video_width=640,
                                video_height=360,
                                video_duration=0
                            )
                        )
                    else:
                        # For untrusted video URLs, fallback to photo
                        print(f"Skipping video from untrusted source: {char_img}")
                        results.append(
                            InlineQueryResultPhoto(
                                id=result_id,
                                photo_url=char_img,
                                thumbnail_url=char_img,
                                caption=caption + f"\n\n⚠️ {to_small_caps('video preview unavailable - see channel')}",
                                parse_mode='HTML',
                                reply_markup=button
                            )
                        )
                else:
                    # Use Photo result for images (usually more reliable)
                    results.append(
                        InlineQueryResultPhoto(
                            id=result_id,
                            photo_url=char_img,
                            thumbnail_url=char_img,
                            caption=caption,
                            parse_mode='HTML',
                            reply_markup=button
                        )
                    )
            except Exception as result_error:
                # If any result fails, log and skip
                print(f"Error creating inline result for {char_id}: {result_error}")
                print(f"URL: {char_img}")
                # Don't add broken results - just skip this character
                continue

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


# Add handlers
application.add_handler(InlineQueryHandler(inlinequery, block=False))
application.add_handler(CallbackQueryHandler(show_smashers_callback, pattern=r'^show_smashers_', block=False))

LOGGER.info("[INLINE] Handlers registered successfully with video support")