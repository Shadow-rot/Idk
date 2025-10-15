import asyncio
import time
import random
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, user_collection, collection

# Cooldown storage
dice_cooldowns = {}
propose_cooldowns = {}

# Proposal cost
PROPOSAL_COST = 500  # coins to spend per proposal

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
                    '$set': {'username': username, 'first_name': first_name}
                }
            )
        else:
            # New user
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
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username
    chat_id = update.effective_chat.id

    # Cooldown 60 sec
    if user_id in dice_cooldowns:
        time_elapsed = time.time() - dice_cooldowns[user_id]
        if time_elapsed < 3600:
            cooldown_remaining = int(3600 - time_elapsed)
            await update.message.reply_text(
                f"{to_small_caps('wait')} <b>{cooldown_remaining}s</b> {to_small_caps('before rolling again')}",
                parse_mode='HTML'
            )
            return
    dice_cooldowns[user_id] = time.time()

    user_data = await user_collection.find_one({'id': user_id})
    if not user_data:
        await update.message.reply_text(
            f"{to_small_caps('you need to grab a character first')}\n{to_small_caps('use')} /grab",
            parse_mode='HTML'
        )
        return

    dice_msg = await context.bot.send_dice(chat_id=chat_id, emoji='🎲')
    dice_value = dice_msg.dice.value
    await asyncio.sleep(3)

    if dice_value in [1, 6]:
        unique_characters = await get_unique_characters(user_id)
        if not unique_characters:
            await update.message.reply_text(
                f"{to_small_caps('no available characters right now')}\n{to_small_caps('try again later')}",
                parse_mode='HTML'
            )
            return

        character = unique_characters[0]
        success = await add_character_to_user(user_id, username, first_name, character)
        if not success:
            await update.message.reply_text(
                f"{to_small_caps('error adding character please try again')}",
                parse_mode='HTML'
            )
            return

        event_text = ""
        if character.get('event') and character['event'] and character['event'].get('name'):
            event_text = f"\n{to_small_caps('event')} {character['event']['name']}"

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
        await update.message.reply_photo(photo=character['img_url'], caption=caption, parse_mode='HTML')
    else:
        fail_msg = random.choice(FAIL_MESSAGES)
        caption = f"""{to_small_caps('dice result')} <b>{dice_value}</b>

{fail_msg}

{to_small_caps('player')} <a href='tg://user?id={user_id}'>{first_name}</a>
{to_small_caps('needed')} <b>1</b> {to_small_caps('or')} <b>6</b>

{to_small_caps('try again in 60 seconds')}
"""
        await update.message.reply_text(caption, parse_mode='HTML')


# ========================== PROPOSE COMMAND ==========================
async def propose(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username

    # Cooldown check (5 mins)
    if user_id in propose_cooldowns:
        time_elapsed = time.time() - propose_cooldowns[user_id]
        if time_elapsed < 300:
            cooldown_remaining = int(300 - time_elapsed)
            await update.message.reply_text(
                f"{to_small_caps('cooldown you can propose again in')} <b>{cooldown_remaining // 60}m {cooldown_remaining % 60}s</b>",
                parse_mode='HTML'
            )
            return
    propose_cooldowns[user_id] = time.time()

    user_data = await user_collection.find_one({'id': user_id})
    if not user_data:
        await update.message.reply_text(
            f"{to_small_caps('you need to grab a character first')}\n{to_small_caps('use')} /grab",
            parse_mode='HTML'
        )
        return

    balance = user_data.get('balance', 0)
    if balance < PROPOSAL_COST:
        await update.message.reply_text(
            f"💰 {to_small_caps('you need at least')} {PROPOSAL_COST} ɢᴏʟᴅ ᴄᴏɪɴꜱ {to_small_caps('to propose')}.",
            parse_mode='HTML'
        )
        return

    # Deduct cost
    await user_collection.update_one({'id': user_id}, {'$inc': {'balance': -PROPOSAL_COST}})

    proposal_message = to_small_caps('finally the time to propose')
    await update.message.reply_photo(
        photo='https://te.legra.ph/file/4d0f83726fe8cd637d3ff.jpg', caption=proposal_message
    )
    await asyncio.sleep(2)
    await update.message.reply_text(f"{to_small_caps('proposing...')}")
    await asyncio.sleep(2)

    if random.random() > 0.6:  # 40% fail
        await update.message.reply_photo(
            photo='https://graph.org/file/48c147582d2742105e6ec.jpg',
            caption=to_small_caps('she rejected your proposal and ran away')
        )
    else:
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
        success = await add_character_to_user(user_id, username, first_name, character)
        if not success:
            await update.message.reply_text(
                f"{to_small_caps('error adding character please try again')}",
                parse_mode='HTML'
            )
            return

        event_text = ""
        if character.get('event') and character['event'] and character['event'].get('name'):
            event_text = f"\n{to_small_caps('event')} {character['event']['name']}"

        caption = f"""{to_small_caps('congratulations she accepted you')} <a href='tg://user?id={user_id}'>{first_name}</a>

{to_small_caps('your girl is ready in your harem')}

{to_small_caps('name')} <b>{character['name']}</b>
{to_small_caps('rarity')} <b>{character['rarity']}</b>
{to_small_caps('anime')} <b>{character['anime']}</b>
{to_small_caps('id')} <code>{character['id']}</code>{event_text}

{to_small_caps('added to your harem')}
"""
        await update.message.reply_photo(photo=character['img_url'], caption=caption, parse_mode='HTML')


# ========================== HANDLER REGISTRATION ==========================
dice_handler = CommandHandler(['dice', 'marry'], dice_marry, block=False)
propose_handler = CommandHandler(['propose'], propose, block=False)

application.add_handler(dice_handler)
application.add_handler(propose_handler)