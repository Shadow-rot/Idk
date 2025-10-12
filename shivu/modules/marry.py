import asyncio
import time
import random
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, user_collection, collection

# Cooldown storage
dice_cooldowns = {}
propose_cooldowns = {}

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
async def get_unique_characters(user_id, target_rarities=None, count=1):
    """
    Fetch unique characters not in user's collection
    """
    try:
        if target_rarities is None:
            target_rarities = ['🟢 Common', '🟣 Rare', '🟡 Legendary']
        
        # Get user's existing characters
        user_data = await user_collection.find_one({'id': user_id})
        claimed_ids = []

        if user_data and 'characters' in user_data:
            claimed_ids = [char.get('id') for char in user_data.get('characters', []) if 'id' in char]

        # Find available characters not in user's collection
        pipeline = [
            {
                '$match': {
                    'rarity': {'$in': target_rarities},
                    'id': {'$nin': claimed_ids}
                }
            },
            {'$sample': {'size': count}}
        ]

        cursor = collection.aggregate(pipeline)
        characters = await cursor.to_list(length=None)
        
        return characters if characters else []

    except Exception as e:
        print(f"Error in get_unique_characters: {e}")
        return []


# Success messages for winning
SUCCESS_MESSAGES = [
    "ᴀᴄᴄᴇᴘᴛᴇᴅ ʏᴏᴜʀ ᴘʀᴏᴘᴏsᴀʟ",
    "sᴀɪᴅ ʏᴇs ᴛᴏ ʏᴏᴜʀ ʜᴇᴀʀᴛ",
    "ɪs ɴᴏᴡ ʏᴏᴜʀs ғᴏʀᴇᴠᴇʀ",
    "ᴊᴏɪɴᴇᴅ ʏᴏᴜʀ ʜᴀʀᴇᴍ",
    "ғᴇʟʟ ғᴏʀ ʏᴏᴜ"
]

# Fail messages
FAIL_MESSAGES = [
    "sʜᴇ ʀᴇᴊᴇᴄᴛᴇᴅ ʏᴏᴜ ᴀɴᴅ ʀᴀɴ ᴀᴡᴀʏ",
    "sʜᴇ sᴀɪᴅ ɴᴏ ᴀɴᴅ ʟᴇғᴛ",
    "sʜᴇ ᴡᴀʟᴋᴇᴅ ᴀᴡᴀʏ ғʀᴏᴍ ʏᴏᴜ",
    "sʜᴇ ᴅɪsᴀᴘᴘᴇᴀʀᴇᴅ ɪɴ ᴛʜᴇ ᴡɪɴᴅ",
    "ʙᴇᴛᴛᴇʀ ʟᴜᴄᴋ ɴᴇxᴛ ᴛɪᴍᴇ"
]


async def add_character_to_user(user_id, username, first_name, character):
    """
    Add character to user's collection in database
    """
    try:
        user_data = await user_collection.find_one({'id': user_id})
        
        if user_data:
            # User exists, update their collection
            await user_collection.update_one(
                {'id': user_id},
                {
                    '$push': {'characters': character},
                    '$set': {
                        'username': username,
                        'first_name': first_name
                    }
                }
            )
        else:
            # New user, create entry
            await user_collection.insert_one({
                'id': user_id,
                'username': username,
                'first_name': first_name,
                'characters': [character]
            })
        
        return True
    except Exception as e:
        print(f"Error adding character to user: {e}")
        return False


# ========================== DICE/MARRY COMMAND ==========================
async def dice_marry(update: Update, context: CallbackContext):
    """
    Dice/Marry command - Roll 1 or 6 to get a character
    Cooldown: 60 seconds
    """
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username
    chat_id = update.effective_chat.id

    # Check cooldown (60 seconds)
    if user_id in dice_cooldowns:
        time_elapsed = time.time() - dice_cooldowns[user_id]
        if time_elapsed < 60:
            cooldown_remaining = int(60 - time_elapsed)
            await update.message.reply_text(
                f"{to_small_caps('wait')} <b>{cooldown_remaining}s</b> {to_small_caps('before rolling again')}",
                parse_mode='HTML'
            )
            return

    # Update cooldown
    dice_cooldowns[user_id] = time.time()

    # Check if user exists in database
    user_data = await user_collection.find_one({'id': user_id})
    if not user_data:
        await update.message.reply_text(
            f"{to_small_caps('you need to grab a character first')}\n{to_small_caps('use')} /grab",
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
                f"{to_small_caps('no available characters right now')}\n{to_small_caps('try again later')}",
                parse_mode='HTML'
            )
            return

        character = unique_characters[0]

        # Add character to user's collection
        success = await add_character_to_user(user_id, username, first_name, character)

        if not success:
            await update.message.reply_text(
                f"{to_small_caps('error adding character please try again')}",
                parse_mode='HTML'
            )
            return

        # Get event info if available
        event_text = ""
        if character.get('event') and character['event'] and character['event'].get('name'):
            event_text = f"\n{to_small_caps('event')} {character['event']['name']}"

        # Success message
        success_msg = random.choice(SUCCESS_MESSAGES)

        caption = f"""{to_small_caps('dice result')} <b>{dice_value}</b>

{to_small_caps('congratulations')} <a href='tg://user?id={user_id}'>{first_name}</a>

{character['name']} {success_msg}

{to_small_caps('name')} <b>{character['name']}</b>
{to_small_caps('rarity')} <b>{character['rarity']}</b>
{to_small_caps('anime')} <b>{character['anime']}</b>
{to_small_caps('id')} <code>{character['id']}</code>{event_text}

{to_small_caps('added to your harem')}
"""

        await update.message.reply_photo(
            photo=character['img_url'],
            caption=caption,
            parse_mode='HTML'
        )

    else:
        # Failed - didn't get 1 or 6
        fail_msg = random.choice(FAIL_MESSAGES)

        caption = f"""{to_small_caps('dice result')} <b>{dice_value}</b>

{fail_msg}

{to_small_caps('player')} <a href='tg://user?id={user_id}'>{first_name}</a>
{to_small_caps('needed')} <b>1</b> {to_small_caps('or')} <b>6</b>

{to_small_caps('try again in 60 seconds')}
"""

        await update.message.reply_text(
            caption,
            parse_mode='HTML'
        )


# ========================== PROPOSE COMMAND ==========================
async def propose(update: Update, context: CallbackContext):
    """
    Propose command - 60% chance to get a character
    Cooldown: 300 seconds (5 minutes)
    """
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username
    chat_id = update.effective_chat.id

    # Check cooldown (300 seconds = 5 minutes)
    if user_id in propose_cooldowns:
        time_elapsed = time.time() - propose_cooldowns[user_id]
        if time_elapsed < 300:
            cooldown_remaining = int(300 - time_elapsed)
            minutes = cooldown_remaining // 60
            seconds = cooldown_remaining % 60
            await update.message.reply_text(
                f"{to_small_caps('cooldown you can propose again in')} <b>{minutes}m {seconds}s</b>",
                parse_mode='HTML'
            )
            return

    # Update cooldown
    propose_cooldowns[user_id] = time.time()

    # Check if user exists in database
    user_data = await user_collection.find_one({'id': user_id})
    if not user_data:
        await update.message.reply_text(
            f"{to_small_caps('you need to grab a character first')}\n{to_small_caps('use')} /grab",
            parse_mode='HTML'
        )
        return

    # Send initial proposal message
    proposal_message = to_small_caps('finally the time to propose')
    photo_path = 'https://te.legra.ph/file/4d0f83726fe8cd637d3ff.jpg'
    await update.message.reply_photo(photo=photo_path, caption=proposal_message)
    await asyncio.sleep(2)

    # Send proposing text
    await update.message.reply_text(f"{to_small_caps('proposing')}")
    await asyncio.sleep(2)

    # Generate random result (60% chance to win)
    if random.random() > 0.6:  # 40% chance to fail
        # Rejection
        rejection_message = to_small_caps('she rejected your proposal and ran away')
        rejection_photo_path = 'https://graph.org/file/48c147582d2742105e6ec.jpg'
        await update.message.reply_photo(
            photo=rejection_photo_path,
            caption=rejection_message
        )
    else:
        # Success - Get character
        unique_characters = await get_unique_characters(
            user_id,
            target_rarities=['🟢 Common', '🟣 Rare', '🟡 Legendary', '💮 Special Edition', '🔮 Premium Edition', '🎗️ Supreme']
        )

        if not unique_characters:
            await update.message.reply_text(
                f"{to_small_caps('no available characters right now')}\n{to_small_caps('try again later')}",
                parse_mode='HTML'
            )
            return

        character = unique_characters[0]

        # Add character to user's collection
        success = await add_character_to_user(user_id, username, first_name, character)

        if not success:
            await update.message.reply_text(
                f"{to_small_caps('error adding character please try again')}",
                parse_mode='HTML'
            )
            return

        # Get event info if available
        event_text = ""
        if character.get('event') and character['event'] and character['event'].get('name'):
            event_text = f"\n{to_small_caps('event')} {character['event']['name']}"

        # Success caption
        caption = f"""{to_small_caps('congratulations she accepted you')} <a href='tg://user?id={user_id}'>{first_name}</a>

{to_small_caps('your girl is ready in your harem')}

{to_small_caps('name')} <b>{character['name']}</b>
{to_small_caps('rarity')} <b>{character['rarity']}</b>
{to_small_caps('anime')} <b>{character['anime']}</b>
{to_small_caps('id')} <code>{character['id']}</code>{event_text}

{to_small_caps('added to your harem')}
"""

        await update.message.reply_photo(
            photo=character['img_url'],
            caption=caption,
            parse_mode='HTML'
        )


# ========================== HANDLER REGISTRATION ==========================
dice_handler = CommandHandler(['dice', 'marry'], dice_marry, block=False)
propose_handler = CommandHandler(['propose'], propose, block=False)

application.add_handler(dice_handler)
application.add_handler(propose_handler)