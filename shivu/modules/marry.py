import asyncio
import time
import random
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, user_collection, collection

# Configuration
DICE_COOLDOWN = 1800  # 30 minutes
PROPOSE_COOLDOWN = 300  # 5 minutes
PROPOSAL_COST = 2000

# Cooldown storage
cooldowns = {'dice': {}, 'propose': {}}

# Messages
SUCCESS_MSGS = [
    "ᴀᴄᴄᴇᴘᴛᴇᴅ ʏᴏᴜʀ ᴘʀᴏᴘᴏsᴀʟ",
    "sᴀɪᴅ ʏᴇs ᴛᴏ ʏᴏᴜʀ ʜᴇᴀʀᴛ",
    "ɪs ɴᴏᴡ ʏᴏᴜʀs ғᴏʀᴇᴠᴇʀ",
    "ᴊᴏɪɴᴇᴅ ʏᴏᴜʀ ʜᴀʀᴇᴍ",
    "ғᴇʟʟ ғᴏʀ ʏᴏᴜ"
]

FAIL_MSGS = [
    "sʜᴇ ʀᴇᴊᴇᴄᴛᴇᴅ ʏᴏᴜ ᴀɴᴅ ʀᴀɴ ᴀᴡᴀʏ",
    "sʜᴇ sᴀɪᴅ ɴᴏ ᴀɴᴅ ʟᴇғᴛ",
    "sʜᴇ ᴡᴀʟᴋᴇᴅ ᴀᴡᴀʏ ғʀᴏᴍ ʏᴏᴜ",
    "sʜᴇ ᴅɪsᴀᴘᴘᴇᴀʀᴇᴅ ɪɴ ᴛʜᴇ ᴡɪɴᴅ",
    "ʙᴇᴛᴛᴇʀ ʟᴜᴄᴋ ɴᴇxᴛ ᴛɪᴍᴇ"
]

def check_cooldown(user_id, cmd_type, cooldown_time):
    """Check and update cooldown"""
    if user_id in cooldowns[cmd_type]:
        elapsed = time.time() - cooldowns[cmd_type][user_id]
        if elapsed < cooldown_time:
            return False, int(cooldown_time - elapsed)
    cooldowns[cmd_type][user_id] = time.time()
    return True, 0

async def get_unique_chars(user_id, rarities=None):
    """Optimized character fetching with aggregation pipeline"""
    try:
        rarities = rarities or ['🟢 Common', '🟣 Rare', '🟡 Legendary']
        
        # Single optimized query
        pipeline = [
            {'$match': {'rarity': {'$in': rarities}}},
            {
                '$lookup': {
                    'from': user_collection.name,
                    'let': {'char_id': '$id'},
                    'pipeline': [
                        {'$match': {'id': user_id}},
                        {'$project': {'characters.id': 1}}
                    ],
                    'as': 'user_chars'
                }
            },
            {
                '$match': {
                    '$expr': {
                        '$not': {
                            '$in': ['$id', {'$ifNull': [{'$arrayElemAt': ['$user_chars.characters.id', 0]}, []]}]
                        }
                    }
                }
            },
            {'$sample': {'size': 1}}
        ]
        
        chars = await collection.aggregate(pipeline).to_list(1)
        return chars if chars else []
    except:
        # Fallback to simple method if aggregation fails
        user_data = await user_collection.find_one({'id': user_id}, {'characters.id': 1})
        claimed_ids = [c.get('id') for c in user_data.get('characters', [])] if user_data else []
        
        chars = await collection.aggregate([
            {'$match': {'rarity': {'$in': rarities}, 'id': {'$nin': claimed_ids}}},
            {'$sample': {'size': 1}}
        ]).to_list(1)
        return chars if chars else []

async def add_char(user_id, username, first_name, char):
    """Optimized character addition with upsert"""
    try:
        await user_collection.update_one(
            {'id': user_id},
            {
                '$push': {'characters': char},
                '$set': {'username': username, 'first_name': first_name},
                '$setOnInsert': {'balance': 0}
            },
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error adding character: {e}")
        return False

def format_caption(user_id, first_name, char, dice_val=None):
    """Format character caption"""
    event = f"\nᴇᴠᴇɴᴛ: {char['event']['name']}" if char.get('event', {}).get('name') else ""
    origin = f"\nᴏʀɪɢɪɴ: <b>{char['origin']}</b>" if char.get('origin') else ""
    abilities = f"\nᴀʙɪʟɪᴛɪᴇs: <b>{char['abilities']}</b>" if char.get('abilities') else ""
    
    msg = random.choice(SUCCESS_MSGS)
    dice_txt = f"ᴅɪᴄᴇ ʀᴇsᴜʟᴛ: <b>{dice_val}</b>\n" if dice_val else ""
    
    return f"""{dice_txt}ᴄᴏɴɢʀᴀᴛᴜʟᴀᴛɪᴏɴs <a href='tg://user?id={user_id}'>{first_name}</a>
{char['name']} {msg}
ɴᴀᴍᴇ: <b>{char['name']}</b>
ʀᴀʀɪᴛʏ: <b>{char['rarity']}</b>
ᴀɴɪᴍᴇ: <b>{char['anime']}</b>
ɪᴅ: <code>{char['id']}</code>{event}{origin}{abilities}
ᴀᴅᴅᴇᴅ ᴛᴏ ʏᴏᴜʀ ʜᴀʀᴇᴍ ✨"""

async def dice_marry(update: Update, context: CallbackContext):
    """Dice marry command"""
    try:
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        username = update.effective_user.username

        can_use, remaining = check_cooldown(user_id, 'dice', DICE_COOLDOWN)
        if not can_use:
            mins, secs = divmod(remaining, 60)
            await update.message.reply_text(
                f"ᴡᴀɪᴛ <b>{mins}ᴍ {secs}s</b> ʙᴇғᴏʀᴇ ʀᴏʟʟɪɴɢ ᴀɢᴀɪɴ ⏳",
                parse_mode='HTML'
            )
            return

        # Check user exists (quick query)
        user_exists = await user_collection.count_documents({'id': user_id}, limit=1)
        if not user_exists:
            await update.message.reply_text("ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ɢʀᴀʙ ᴀ ᴄʜᴀʀᴀᴄᴛᴇʀ ғɪʀsᴛ\nᴜsᴇ /grab", parse_mode='HTML')
            return

        dice_msg = await context.bot.send_dice(chat_id=update.effective_chat.id, emoji='🎲')
        dice_val = dice_msg.dice.value
        await asyncio.sleep(3)

        if dice_val in [1, 6]:
            chars = await get_unique_chars(user_id)
            if not chars:
                await update.message.reply_text("ɴᴏ ᴀᴠᴀɪʟᴀʙʟᴇ ᴄʜᴀʀᴀᴄᴛᴇʀs\nᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ 💔", parse_mode='HTML')
                return

            char = chars[0]
            if not await add_char(user_id, username, first_name, char):
                await update.message.reply_text("ᴇʀʀᴏʀ ᴀᴅᴅɪɴɢ ᴄʜᴀʀᴀᴄᴛᴇʀ ⚠️", parse_mode='HTML')
                return

            await update.message.reply_photo(
                photo=char['img_url'],
                caption=format_caption(user_id, first_name, char, dice_val),
                parse_mode='HTML'
            )
        else:
            fail_msg = random.choice(FAIL_MSGS)
            await update.message.reply_text(
                f"ᴅɪᴄᴇ ʀᴇsᴜʟᴛ: <b>{dice_val}</b>\n{fail_msg}\nᴘʟᴀʏᴇʀ: <a href='tg://user?id={user_id}'>{first_name}</a>\nɴᴇᴇᴅᴇᴅ: <b>1</b> ᴏʀ <b>6</b>\nᴛʀʏ ᴀɢᴀɪɴ ɪɴ 30 ᴍɪɴᴜᴛᴇs ⏰",
                parse_mode='HTML'
            )

    except Exception as e:
        print(f"Error in dice_marry: {e}")
        await update.message.reply_text("ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ⚠️", parse_mode='HTML')

async def propose(update: Update, context: CallbackContext):
    """Propose command"""
    try:
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        username = update.effective_user.username

        can_use, remaining = check_cooldown(user_id, 'propose', PROPOSE_COOLDOWN)
        if not can_use:
            mins, secs = divmod(remaining, 60)
            await update.message.reply_text(
                f"ᴄᴏᴏʟᴅᴏᴡɴ: ᴡᴀɪᴛ <b>{mins}ᴍ {secs}s</b> ⏳",
                parse_mode='HTML'
            )
            return

        # Check balance with single query
        user_data = await user_collection.find_one({'id': user_id}, {'balance': 1})
        if not user_data:
            await update.message.reply_text("ᴘʟᴇᴀsᴇ sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ ғɪʀsᴛ\nᴄʟɪᴄᴋ /start", parse_mode='HTML')
            return

        balance = user_data.get('balance', 0)
        if balance < PROPOSAL_COST:
            await update.message.reply_text(
                f"💰 ʏᴏᴜ ɴᴇᴇᴅ <b>{PROPOSAL_COST}</b> ɢᴏʟᴅ ᴄᴏɪɴs ᴛᴏ ᴘʀᴏᴘᴏsᴇ\nʏᴏᴜʀ ʙᴀʟᴀɴᴄᴇ: <b>{balance}</b>",
                parse_mode='HTML'
            )
            return

        # Deduct cost immediately
        await user_collection.update_one({'id': user_id}, {'$inc': {'balance': -PROPOSAL_COST}})

        await update.message.reply_photo(
            photo='https://te.legra.ph/file/4d0f83726fe8cd637d3ff.jpg',
            caption='ғɪɴᴀʟʟʏ ᴛʜᴇ ᴛɪᴍᴇ ᴛᴏ ᴘʀᴏᴘᴏsᴇ 💍'
        )
        await asyncio.sleep(2)
        await update.message.reply_text("ᴘʀᴏᴘᴏsɪɴɢ... 💕")
        await asyncio.sleep(2)

        # 40% success rate
        if random.random() > 0.4:
            await update.message.reply_photo(
                photo='https://files.catbox.moe/kvd5h7.jpg',
                caption='sʜᴇ ʀᴇᴊᴇᴄᴛᴇᴅ ʏᴏᴜʀ ᴘʀᴏᴘᴏsᴀʟ ᴀɴᴅ ʀᴀɴ ᴀᴡᴀʏ 💔'
            )
        else:
            chars = await get_unique_chars(user_id, ['💮 Special Edition', '💫 Neon', '✨ Manga', '🎐 Celestial'])
            if not chars:
                # Refund on no characters
                await user_collection.update_one({'id': user_id}, {'$inc': {'balance': PROPOSAL_COST}})
                await update.message.reply_text("ɴᴏ ᴀᴠᴀɪʟᴀʙʟᴇ ᴄʜᴀʀᴀᴄᴛᴇʀs\nᴄᴏɪɴs ʀᴇғᴜɴᴅᴇᴅ 💔", parse_mode='HTML')
                return

            char = chars[0]
            if not await add_char(user_id, username, first_name, char):
                # Refund on error
                await user_collection.update_one({'id': user_id}, {'$inc': {'balance': PROPOSAL_COST}})
                await update.message.reply_text("ᴇʀʀᴏʀ ᴀᴅᴅɪɴɢ ᴄʜᴀʀᴀᴄᴛᴇʀ\nᴄᴏɪɴs ʀᴇғᴜɴᴅᴇᴅ ⚠️", parse_mode='HTML')
                return

            await update.message.reply_photo(
                photo=char['img_url'],
                caption=format_caption(user_id, first_name, char),
                parse_mode='HTML'
            )

    except Exception as e:
        print(f"Error in propose: {e}")
        # Refund on error
        try:
            await user_collection.update_one({'id': user_id}, {'$inc': {'balance': PROPOSAL_COST}})
        except:
            pass
        await update.message.reply_text("ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ\nᴄᴏɪɴs ʀᴇғᴜɴᴅᴇᴅ ⚠️", parse_mode='HTML')

application.add_handler(CommandHandler(['dice', 'marry'], dice_marry, block=False))
application.add_handler(CommandHandler(['propose'], propose, block=False))