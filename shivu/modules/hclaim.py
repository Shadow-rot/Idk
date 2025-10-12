import asyncio
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, user_collection, collection, SUPPORT_CHAT

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
        # Get already claimed character IDs
        user_data = await user_collection.find_one({'id': user_id}, {'characters': 1})
        claimed_ids = [char['id'] for char in user_data.get('characters', [])] if user_data else []

        # Find characters not yet claimed
        characters = await collection.find({
            'rarity': {'$in': target_rarities},
            'id': {'$nin': claimed_ids}
        }).to_list(length=100)

        if characters:
            import random
            return [random.choice(characters)]
        return []
    except Exception as e:
        print(f"Error retrieving unique characters: {e}")
        return []

# Command handler for daily claim
async def hclaim(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    chat_id = update.effective_chat.id

    # Prevent multiple simultaneous claims
    if user_id in claim_lock:
        await update.message.reply_text(f"⏳ {to_small_caps('claim in progress wait')}")
        return

    claim_lock[user_id] = True
    try:
        # Check if command is used in support chat
        if str(chat_id) != str(SUPPORT_CHAT).replace('@', '').replace('-100', ''):
            join_button = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🌟 {to_small_caps('join channel')}", url=f'https://t.me/{SUPPORT_CHAT}')]
            ])
            return await update.message.reply_text(
                f"🔒 {to_small_caps('join channel to claim daily slave')}",
                reply_markup=join_button
            )

        # Fetch or create user data
        user_data = await user_collection.find_one({'id': user_id})
        if not user_data:
            user_data = {
                'id': user_id,
                'first_name': first_name,
                'username': update.effective_user.username,
                'characters': [],
                'last_daily_claim': None
            }
            await user_collection.insert_one(user_data)

        # Check if already claimed today
        last_claimed = user_data.get('last_daily_claim')
        if last_claimed and last_claimed.date() == datetime.utcnow().date():
            remaining_time = timedelta(days=1) - (datetime.utcnow() - last_claimed)
            formatted_time = await format_time_delta(remaining_time)
            return await update.message.reply_text(
                f"⏰ {to_small_caps('already claimed today')}\n\n"
                f"⏳ {to_small_caps('next claim in')}: `{formatted_time}`",
                parse_mode='Markdown'
            )

        # Fetch unique character
        unique_characters = await get_unique_characters(user_id)
        if not unique_characters:
            return await update.message.reply_text(f"❌ {to_small_caps('no slaves available right now')}")

        # Update user data with new character
        character = unique_characters[0]
        await user_collection.update_one(
            {'id': user_id},
            {
                '$push': {'characters': character},
                '$set': {'last_daily_claim': datetime.utcnow()}
            }
        )

        # Get event info if available
        event_text = ""
        if character.get('event') and character['event'].get('name'):
            event_text = f"\n{character['event']['sign']} {to_small_caps('event')}: {character['event']['name']}"

        # Send character with attractive message
        caption = f"""
┏━━━━━━━━━━━━━━━━━━━┓
  🎊 <b>{to_small_caps('daily claim')}</b> 🎊
┗━━━━━━━━━━━━━━━━━━━┛

🌟 {to_small_caps('congrats')} <a href='tg://user?id={user_id}'>{first_name}</a>

━━━━━━━━━━━━━━━━━━━
🎴 {to_small_caps('name')}: <b>{character['name']}</b>
⭐ {to_small_caps('rarity')}: <b>{character['rarity']}</b>
🎯 {to_small_caps('anime')}: <b>{character['anime']}</b>{event_text}
━━━━━━━━━━━━━━━━━━━

✨ {to_small_caps('come back tomorrow for more')}
"""

        await update.message.reply_photo(
            photo=character['img_url'],
            caption=caption,
            parse_mode='HTML'
        )

    except Exception as e:
        print(f"Error in hclaim command: {e}")
        await update.message.reply_text(f"❌ {to_small_caps('error occurred try again')}")

    finally:
        # Release claim lock
        claim_lock.pop(user_id, None)

# Add handler
hclaim_handler = CommandHandler(['hclaim', 'claim'], hclaim, block=False)
application.add_handler(hclaim_handler)