import asyncio
import time
import random
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, user_collection, collection, user_totals_collection

# Cooldown storage
cooldowns = {}

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

# Fetch unique characters for user
async def get_unique_characters(user_id, target_rarities=['🟢 Common', '🟣 Rare', '🟡 Legendary']):
    try:
        # Get user's collection from user_totals_collection
        user_totals = await user_totals_collection.find_one({'id': user_id})
        claimed_ids = []
        
        if user_totals and 'characters' in user_totals:
            claimed_ids = [char['id'] for char in user_totals.get('characters', [])]

        # Find available characters
        available_characters = []
        async for character in collection.find({'rarity': {'$in': target_rarities}}):
            if character['id'] not in claimed_ids:
                available_characters.append(character)

        if available_characters:
            return [random.choice(available_characters)]
        return []
    except Exception as e:
        print(f"Error in get_unique_characters: {e}")
        return []

# Success messages for winning
SUCCESS_MESSAGES = [
    "💍 {name} ᴀᴄᴄᴇᴘᴛᴇᴅ ʏᴏᴜʀ ᴘʀᴏᴘᴏsᴀʟ",
    "💕 {name} sᴀɪᴅ ʏᴇs ᴛᴏ ʏᴏᴜʀ ʜᴇᴀʀᴛ",
    "✨ {name} ɪs ɴᴏᴡ ʏᴏᴜʀs ғᴏʀᴇᴠᴇʀ",
    "🌸 {name} ᴊᴏɪɴᴇᴅ ʏᴏᴜʀ ʜᴀʀᴇᴍ",
    "💫 {name} ғᴇʟʟ ғᴏʀ ʏᴏᴜ"
]

# Fail messages
FAIL_MESSAGES = [
    "💔 sʜᴇ ʀᴇᴊᴇᴄᴛᴇᴅ ʏᴏᴜ ᴀɴᴅ ʀᴀɴ ᴀᴡᴀʏ",
    "😢 sʜᴇ sᴀɪᴅ ɴᴏ ᴀɴᴅ ʟᴇғᴛ",
    "🚪 sʜᴇ ᴡᴀʟᴋᴇᴅ ᴀᴡᴀʏ ғʀᴏᴍ ʏᴏᴜ",
    "💨 sʜᴇ ᴅɪsᴀᴘᴘᴇᴀʀᴇᴅ ɪɴ ᴛʜᴇ ᴡɪɴᴅ",
    "❌ ʙᴇᴛᴛᴇʀ ʟᴜᴄᴋ ɴᴇxᴛ ᴛɪᴍᴇ"
]

# Dice/Marry command
async def dice_marry(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    chat_id = update.effective_chat.id

    # Check cooldown (60 seconds)
    if user_id in cooldowns:
        time_elapsed = time.time() - cooldowns[user_id]
        if time_elapsed < 60:
            cooldown_remaining = int(60 - time_elapsed)
            await update.message.reply_text(
                f"⏰ {to_small_caps('wait')} <b>{cooldown_remaining}s</b> {to_small_caps('before rolling again')}",
                parse_mode='HTML'
            )
            return

    # Update cooldown
    cooldowns[user_id] = time.time()

    # Check if user exists in database
    user_data = await user_collection.find_one({'id': user_id})
    if not user_data:
        await update.message.reply_text(
            f"❌ {to_small_caps('you need to start the bot first')}\n{to_small_caps('use')} /start",
            parse_mode='HTML'
        )
        return

    # Send dice animation
    dice_msg = await context.bot.send_dice(chat_id=chat_id, emoji='🎲')
    dice_value = dice_msg.dice.value

    # Wait for dice animation
    await asyncio.sleep(3)

    # Check if user won (1 or 6)
    if dice_value in [1, 6]:
        # Get unique character
        unique_characters = await get_unique_characters(user_id)

        if not unique_characters:
            await update.message.reply_text(
                f"❌ {to_small_caps('no available slaves right now')}\n{to_small_caps('try again later')}",
                parse_mode='HTML'
            )
            return

        character = unique_characters[0]

        # Add to user_totals_collection
        user_totals = await user_totals_collection.find_one({'id': user_id})
        if user_totals:
            await user_totals_collection.update_one(
                {'id': user_id},
                {
                    '$push': {'characters': character},
                    '$inc': {'count': 1}
                }
            )
        else:
            await user_totals_collection.insert_one({
                'id': user_id,
                'username': update.effective_user.username,
                'first_name': first_name,
                'characters': [character],
                'count': 1
            })

        # Get event info if available
        event_text = ""
        if character.get('event') and character['event'] and character['event'].get('name'):
            event_text = f"\n{character['event']['sign']} {to_small_caps('event')}: {character['event']['name']}"

        # Success message
        success_msg = random.choice(SUCCESS_MESSAGES).format(name=character['name'])
        
        caption = f"""
┏━━━━━━━━━━━━━━━━━━━┓
  🎲 <b>{to_small_caps('dice result')}: {dice_value}</b>
┗━━━━━━━━━━━━━━━━━━━┛

🎊 {to_small_caps('congratulations')} <a href='tg://user?id={user_id}'>{first_name}</a>

{success_msg}

━━━━━━━━━━━━━━━━━━━
🎴 {to_small_caps('name')}: <b>{character['name']}</b>
⭐ {to_small_caps('rarity')}: <b>{character['rarity']}</b>
🎯 {to_small_caps('anime')}: <b>{character['anime']}</b>
🆔 {to_small_caps('id')}: <code>{character['id']}</code>{event_text}
━━━━━━━━━━━━━━━━━━━

💕 {to_small_caps('she joined your harem')}
"""

        await update.message.reply_photo(
            photo=character['img_url'],
            caption=caption,
            parse_mode='HTML'
        )

    else:
        # Failed - didn't get 1 or 6
        fail_msg = random.choice(FAIL_MESSAGES)
        
        caption = f"""
┏━━━━━━━━━━━━━━━━━━━┓
  🎲 <b>{to_small_caps('dice result')}: {dice_value}</b>
┗━━━━━━━━━━━━━━━━━━━┛

{fail_msg}

━━━━━━━━━━━━━━━━━━━
👤 {to_small_caps('player')}: <a href='tg://user?id={user_id}'>{first_name}</a>
🎯 {to_small_caps('needed')}: <b>1</b> {to_small_caps('or')} <b>6</b>
━━━━━━━━━━━━━━━━━━━

⏰ {to_small_caps('try again in 60 seconds')}
"""

        await update.message.reply_text(
            caption,
            parse_mode='HTML'
        )

# Add handler
dice_handler = CommandHandler(['dice', 'marry'], dice_marry, block=False)
application.add_handler(dice_handler)