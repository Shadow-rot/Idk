import asyncio
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, user_collection, collection, user_totals_collection, SUPPORT_CHAT
import random

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
        # Get user's total collection from user_totals_collection
        user_totals = await user_totals_collection.find_one({'id': user_id})
        claimed_ids = []
        
        if user_totals and 'characters' in user_totals:
            # Extract character IDs from user's collection
            claimed_ids = [char['id'] for char in user_totals.get('characters', [])]

        # Find characters not yet claimed with target rarities
        available_characters = []
        async for character in collection.find({'rarity': {'$in': target_rarities}}):
            if character['id'] not in claimed_ids:
                available_characters.append(character)

        if available_characters:
            return [random.choice(available_characters)]
        return []
    except Exception as e:
        print(f"Error retrieving unique characters: {e}")
        return []

# Command handler for daily claim
async def hclaim(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username

    # Prevent multiple simultaneous claims
    if user_id in claim_lock:
        await update.message.reply_text(f"⏳ {to_small_caps('claim in progress please wait')}")
        return

    claim_lock[user_id] = True
    try:
        # Fetch or create user data
        user_data = await user_collection.find_one({'id': user_id})
        if not user_data:
            user_data = {
                'id': user_id,
                'first_name': first_name,
                'username': username,
                'characters': [],
                'last_daily_claim': None,
                'balance': 0
            }
            await user_collection.insert_one(user_data)

        # Check if already claimed today
        last_claimed = user_data.get('last_daily_claim')
        if last_claimed and isinstance(last_claimed, datetime) and last_claimed.date() == datetime.utcnow().date():
            remaining_time = timedelta(days=1) - (datetime.utcnow() - last_claimed)
            formatted_time = await format_time_delta(remaining_time)
            await update.message.reply_text(
                f"⏰ {to_small_caps('already claimed today')}\n\n"
                f"⏳ {to_small_caps('next claim in')}: `{formatted_time}`",
                parse_mode='Markdown'
            )
            return

        # Fetch unique character
        unique_characters = await get_unique_characters(user_id)
        if not unique_characters:
            await update.message.reply_text(f"❌ {to_small_caps('no new slaves available try again later')}")
            return

        character = unique_characters[0]
        
        # Update user_collection with last claim time
        await user_collection.update_one(
            {'id': user_id},
            {'$set': {'last_daily_claim': datetime.utcnow()}}
        )

        # Add character to user_totals_collection
        user_totals = await user_totals_collection.find_one({'id': user_id})
        if user_totals:
            # Update existing user totals
            await user_totals_collection.update_one(
                {'id': user_id},
                {
                    '$push': {'characters': character},
                    '$inc': {'count': 1}
                }
            )
        else:
            # Create new user totals entry
            await user_totals_collection.insert_one({
                'id': user_id,
                'username': username,
                'first_name': first_name,
                'characters': [character],
                'count': 1
            })

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
🎴 {to_small_caps('name')}: <b>{character['name']}</b>
⭐ {to_small_caps('rarity')}: <b>{character['rarity']}</b>
🎯 {to_small_caps('anime')}: <b>{character['anime']}</b>
🆔 {to_small_caps('id')}: <code>{character['id']}</code>{event_text}
━━━━━━━━━━━━━━━━━━━

✨ {to_small_caps('come back in 24 hours')}
"""

        await update.message.reply_photo(
            photo=character['img_url'],
            caption=caption,
            parse_mode='HTML'
        )

    except Exception as e:
        print(f"Error in hclaim command: {e}")
        await update.message.reply_text(f"❌ {to_small_caps('error occurred')}: {str(e)}")

    finally:
        # Release claim lock
        claim_lock.pop(user_id, None)

# Add handler
hclaim_handler = CommandHandler(['hclaim', 'claim'], hclaim, block=False)
application.add_handler(hclaim_handler)