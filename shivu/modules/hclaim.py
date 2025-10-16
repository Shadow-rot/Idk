import asyncio
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, user_collection, collection, LOGGER
import random
import traceback

claim_lock = {}

# Small caps conversion function
def to_small_caps(text):
    small_caps_map = {
        'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ',
        'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ',
        's': 's', 't': 'ᴛ', 'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
        'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ғ', 'G': 'ɢ', 'H': 'ʜ', 'I': 'ɪ',
        'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ', 'O': 'ᴏ', 'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ',
        'S': 's', 'T': 'ᴛ', 'U': 'ᴜ', 'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x', 'Y': 'ʏ', 'Z': 'ᴢ'
    }
    return ''.join(small_caps_map.get(c, c) for c in text)

# Helper function to format time remaining
async def format_time_delta(delta):
    seconds = delta.total_seconds()
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours)}ʜ {int(minutes)}ᴍ {int(seconds)}s" if hours or minutes or seconds else "0s"

# Fetch unique characters not yet claimed by the user
async def get_unique_characters(user_id, target_rarities=['🟢 Common', '🟣 Rare', '🟡 Legendary']):
    try:
        LOGGER.info(f"[HCLAIM] Fetching unique characters for user {user_id}")
        
        # Get user's current collection from user_collection
        user_data = await user_collection.find_one({'id': user_id})
        claimed_ids = []

        if user_data and 'characters' in user_data:
            # Extract character IDs from user's collection
            claimed_ids = [char.get('id') for char in user_data.get('characters', []) if isinstance(char, dict)]
            LOGGER.info(f"[HCLAIM] User has {len(claimed_ids)} characters already")

        # Find characters not yet claimed with target rarities
        available_characters = []
        async for character in collection.find({'rarity': {'$in': target_rarities}}):
            if character.get('id') not in claimed_ids:
                available_characters.append(character)

        LOGGER.info(f"[HCLAIM] Found {len(available_characters)} available characters")

        if available_characters:
            selected = random.choice(available_characters)
            LOGGER.info(f"[HCLAIM] Selected character: {selected.get('name')} (ID: {selected.get('id')})")
            return [selected]
        return []
    except Exception as e:
        LOGGER.error(f"[HCLAIM ERROR] Error retrieving unique characters: {e}")
        LOGGER.error(traceback.format_exc())
        return []

# Command handler for daily claim
async def hclaim(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username

    LOGGER.info(f"[HCLAIM] Command called by user {user_id} ({first_name})")

    # Prevent multiple simultaneous claims
    if user_id in claim_lock:
        await update.message.reply_text(f"⏳ {to_small_caps('claim in progress please wait')}")
        return

    claim_lock[user_id] = True
    try:
        # Fetch or create user data
        user_data = await user_collection.find_one({'id': user_id})
        
        if not user_data:
            LOGGER.info(f"[HCLAIM] Creating new user entry for {user_id}")
            user_data = {
                'id': user_id,
                'first_name': first_name,
                'username': username,
                'characters': [],
                'last_daily_claim': None
            }
            await user_collection.insert_one(user_data)
        else:
            LOGGER.info(f"[HCLAIM] User {user_id} found in database")

        # Check if already claimed today
        last_claimed = user_data.get('last_daily_claim')
        if last_claimed and isinstance(last_claimed, datetime) and last_claimed.date() == datetime.utcnow().date():
            remaining_time = timedelta(days=1) - (datetime.utcnow() - last_claimed)
            formatted_time = await format_time_delta(remaining_time)
            LOGGER.info(f"[HCLAIM] User {user_id} already claimed today")
            await update.message.reply_text(
                f"⏰ {to_small_caps('already claimed today')}\n\n"
                f"⏳ {to_small_caps('next claim in')}: `{formatted_time}`",
                parse_mode='Markdown'
            )
            return

        # Fetch unique character
        unique_characters = await get_unique_characters(user_id)
        if not unique_characters:
            LOGGER.warning(f"[HCLAIM] No unique characters available for user {user_id}")
            await update.message.reply_text(f"❌ {to_small_caps('no new characters available try again later')}")
            return

        character = unique_characters[0]
        LOGGER.info(f"[HCLAIM] Adding character {character.get('name')} to user {user_id}")

        # Update user_collection - Add character AND update last claim time
        update_result = await user_collection.update_one(
            {'id': user_id},
            {
                '$push': {'characters': character},
                '$set': {
                    'last_daily_claim': datetime.utcnow(),
                    'first_name': first_name,
                    'username': username
                }
            }
        )

        LOGGER.info(f"[HCLAIM] Database update result - modified={update_result.modified_count}, matched={update_result.matched_count}")

        if update_result.modified_count > 0 or update_result.matched_count > 0:
            # Get event info if available
            event_text = ""
            if character.get('event') and character['event'] and character['event'].get('name'):
                event_text = f"\n{character['event']['sign']} {to_small_caps('event')}: {character['event']['name']}"

            # Send character with attractive message
            caption = f"""
┏━━━━━━━━━━━━━━━━━━━┓
  🎊 <b>{to_small_caps('daily claim success')}</b>
┗━━━━━━━━━━━━━━━━━━━┛

🌟 {to_small_caps('congrats')} <a href='tg://user?id={user_id}'>{first_name}</a>

━━━━━━━━━━━━━━━━━━━
🎴 {to_small_caps('name')}: <b>{character.get('name', 'Unknown')}</b>
⭐ {to_small_caps('rarity')}: <b>{character.get('rarity', 'Unknown')}</b>
🎯 {to_small_caps('anime')}: <b>{character.get('anime', 'Unknown')}</b>
🆔 {to_small_caps('id')}: <code>{character.get('id', 'N/A')}</code>{event_text}
━━━━━━━━━━━━━━━━━━━

✨ {to_small_caps('come back in 24 hours')}
"""

            await update.message.reply_photo(
                photo=character.get('img_url', 'https://i.imgur.com/placeholder.png'),
                caption=caption,
                parse_mode='HTML'
            )

            LOGGER.info(f"[HCLAIM] Successfully claimed character for user {user_id}")
        else:
            LOGGER.error(f"[HCLAIM] Failed to update database for user {user_id}")
            await update.message.reply_text(f"❌ {to_small_caps('failed to claim character please try again')}")

    except Exception as e:
        LOGGER.error(f"[HCLAIM ERROR] Error in hclaim command: {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text(f"❌ {to_small_caps('error occurred')}: {str(e)}")

    finally:
        # Release claim lock
        claim_lock.pop(user_id, None)

# Add handler
def register_hclaim_handler():
    """Register hclaim command handler"""
    hclaim_handler = CommandHandler(['hclaim', 'claim'], hclaim, block=False)
    application.add_handler(hclaim_handler)
    LOGGER.info("[HCLAIM] Handler registered")

# Register handler
register_hclaim_handler()