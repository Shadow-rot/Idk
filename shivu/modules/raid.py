import logging
import asyncio
import random
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from telegram.ext import Application

# Import your existing setup
from shivu.config import Development as Config
from shivu import shivuu, db, user_collection, collection, sudo_users

# Collections
raid_settings_collection = db['raid_settings']
raid_cooldown_collection = db['raid_cooldown']
active_raids_collection = db['active_raids']

LOGGER = logging.getLogger(__name__)

OWNER_ID = 5147822244

# Rarity mapping
RARITY_MAP = {
    1: "🟢 ᴄᴏᴍᴍᴏɴ",
    2: "🟣 ʀᴀʀᴇ",
    3: "🟡 ʟᴇɢᴇɴᴅᴀʀʏ",
    4: "💮 sᴘᴇᴄɪᴀʟ ᴇᴅɪᴛɪᴏɴ",
    5: "💫 ɴᴇᴏɴ",
    6: "✨ ᴍᴀɴɢᴀ",
    7: "🎭 ᴄᴏsᴘʟᴀʏ",
    8: "🎐 ᴄᴇʟᴇsᴛɪᴀʟ",
    9: "🔮 ᴘʀᴇᴍɪᴜᴍ ᴇᴅɪᴛɪᴏɴ",
    10: "💋 ᴇʀᴏᴛɪᴄ",
    11: "🌤 sᴜᴍᴍᴇʀ",
    12: "☃️ ᴡɪɴᴛᴇʀ",
    13: "☔️ ᴍᴏɴsᴏᴏɴ",
    14: "💝 ᴠᴀʟᴇɴᴛɪɴᴇ",
    15: "🎃 ʜᴀʟʟᴏᴡᴇᴇɴ",
    16: "🎄 ᴄʜʀɪsᴛᴍᴀs",
    17: "🏵 ᴍʏᴛʜɪᴄ",
    18: "🎗 sᴘᴇᴄɪᴀʟ ᴇᴠᴇɴᴛs",
    19: "🎥 ᴀᴍᴠ",
    20: "👼 ᴛɪɴʏ"
}

# Default settings
DEFAULT_SETTINGS = {
    "start_charge": 500,
    "join_phase_duration": 30,
    "cooldown_minutes": 5,
    "min_balance": 500,
    "allowed_rarities": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    "coin_min": 500,
    "coin_max": 2000,
    "coin_loss_min": 200,
    "coin_loss_max": 500,
    "character_chance": 20,
    "coin_chance": 40,
    "loss_chance": 20,
    "nothing_chance": 20
}


async def get_raid_settings(chat_id):
    """Get raid settings for a chat"""
    settings = await raid_settings_collection.find_one({"chat_id": chat_id})
    if not settings:
        settings = DEFAULT_SETTINGS.copy()
        settings["chat_id"] = chat_id
        await raid_settings_collection.insert_one(settings)
    return settings


async def check_user_cooldown(user_id, chat_id):
    """Check if user is on cooldown"""
    cooldown_data = await raid_cooldown_collection.find_one({
        "user_id": user_id,
        "chat_id": chat_id
    })
    
    if cooldown_data:
        cooldown_until = cooldown_data.get("cooldown_until")
        if cooldown_until and datetime.utcnow() < cooldown_until:
            remaining = (cooldown_until - datetime.utcnow()).total_seconds()
            return False, int(remaining)
    
    return True, 0


async def set_user_cooldown(user_id, chat_id, minutes):
    """Set cooldown for user"""
    cooldown_until = datetime.utcnow() + timedelta(minutes=minutes)
    await raid_cooldown_collection.update_one(
        {"user_id": user_id, "chat_id": chat_id},
        {"$set": {"cooldown_until": cooldown_until}},
        upsert=True
    )


async def get_user_data(user_id):
    """Get user data from database"""
    user = await user_collection.find_one({"id": user_id})
    if not user:
        user = {
            "id": user_id,
            "balance": 0,
            "characters": []
        }
        await user_collection.insert_one(user)
    return user


async def update_user_balance(user_id, amount):
    """Update user balance"""
    await user_collection.update_one(
        {"id": user_id},
        {"$inc": {"balance": amount}},
        upsert=True
    )


async def get_random_character(allowed_rarities):
    """Get a random character from allowed rarities"""
    characters = await collection.find({"rarity": {"$in": allowed_rarities}}).to_list(length=None)
    if characters:
        return random.choice(characters)
    return None


async def add_character_to_user(user_id, character):
    """Add character to user's collection"""
    await user_collection.update_one(
        {"id": user_id},
        {"$push": {"characters": {
            "id": character["id"],
            "name": character["name"],
            "anime": character["anime"],
            "rarity": character["rarity"],
            "img_url": character.get("img_url", "")
        }}},
        upsert=True
    )


@shivuu.on_message(filters.command(["raid"]) & filters.group)
async def start_raid(client, message):
    """Start a raid event"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # Check if raid is already active
    active_raid = await active_raids_collection.find_one({"chat_id": chat_id})
    if active_raid:
        await message.reply_text("⚠️ ᴀ ʀᴀɪᴅ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴄᴛɪᴠᴇ ɪɴ ᴛʜɪs ɢʀᴏᴜᴘ!")
        return
    
    # Get settings
    settings = await get_raid_settings(chat_id)
    
    # Check cooldown
    can_raid, remaining = await check_user_cooldown(user_id, chat_id)
    if not can_raid:
        mins = remaining // 60
        secs = remaining % 60
        await message.reply_text(
            f"⏳ ʏᴏᴜ'ʀᴇ ᴏɴ ᴄᴏᴏʟᴅᴏᴡɴ!\n"
            f"ᴛɪᴍᴇ ʟᴇғᴛ: `{mins}m {secs}s`"
        )
        return
    
    # Check balance
    user_data = await get_user_data(user_id)
    if user_data.get("balance", 0) < settings["start_charge"]:
        await message.reply_text(
            f"💰 ɪɴsᴜғғɪᴄɪᴇɴᴛ ʙᴀʟᴀɴᴄᴇ!\n"
            f"ʏᴏᴜ ɴᴇᴇᴅ `{settings['start_charge']}` ᴄᴏɪɴs ᴛᴏ sᴛᴀʀᴛ ᴀ ʀᴀɪᴅ."
        )
        return
    
    # Deduct start charge
    await update_user_balance(user_id, -settings["start_charge"])
    
    # Create raid
    raid_id = f"{chat_id}_{datetime.utcnow().timestamp()}"
    raid_data = {
        "raid_id": raid_id,
        "chat_id": chat_id,
        "starter_id": user_id,
        "participants": [user_id],
        "started_at": datetime.utcnow(),
        "settings": settings
    }
    await active_raids_collection.insert_one(raid_data)
    
    # Set cooldown for starter
    await set_user_cooldown(user_id, chat_id, settings["cooldown_minutes"])
    
    # Send announcement
    join_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ ᴊᴏɪɴ ʀᴀɪᴅ ⚔️", callback_data=f"join_raid:{raid_id}")]
    ])
    
    announcement = (
        f"<blockquote>⚔️ <b>sʜᴀᴅᴏᴡ ʀᴀɪᴅ ʜᴀs ʙᴇɢᴜɴ!</b> ⚔️</blockquote>\n\n"
        f"<code>ᴊᴏɪɴ ɴᴏᴡ ᴀɴᴅ ʜᴇʟᴘ ᴜɴᴄᴏᴠᴇʀ ᴀɴᴄɪᴇɴᴛ ᴛʀᴇᴀsᴜʀᴇs!</code>\n"
        f"<code>ʙᴇғᴏʀᴇ ᴛʜᴇ sʜᴀᴅᴏᴡs ᴄʟᴏsᴇ ɪɴ...</code>\n\n"
        f"⏱ <b>ᴛɪᴍᴇ ʟᴇғᴛ:</b> <code>{settings['join_phase_duration']}s</code>\n"
        f"💰 <b>ᴇɴᴛʀʏ ғᴇᴇ:</b> <code>{settings['start_charge']} ᴄᴏɪɴs</code>\n"
        f"👥 <b>ᴘᴀʀᴛɪᴄɪᴘᴀɴᴛs:</b> <code>1</code>\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"<i>sᴛᴀʀᴛᴇᴅ ʙʏ</i> {message.from_user.mention}"
    )
    
    raid_msg = await message.reply_text(announcement, reply_markup=join_button)
    
    # Wait for join phase
    await asyncio.sleep(settings["join_phase_duration"])
    
    # Execute raid
    await execute_raid(client, raid_msg, raid_id)


@shivuu.on_callback_query(filters.regex(r"^join_raid:"))
async def join_raid_callback(client, callback_query: CallbackQuery):
    """Handle join raid button"""
    user_id = callback_query.from_user.id
    raid_id = callback_query.data.split(":")[1]
    
    # Get raid data
    raid = await active_raids_collection.find_one({"raid_id": raid_id})
    if not raid:
        await callback_query.answer("⚠️ ᴛʜɪs ʀᴀɪᴅ ʜᴀs ᴇɴᴅᴇᴅ!", show_alert=True)
        return
    
    # Check if already joined
    if user_id in raid["participants"]:
        await callback_query.answer("✅ ʏᴏᴜ'ᴠᴇ ᴀʟʀᴇᴀᴅʏ ᴊᴏɪɴᴇᴅ!", show_alert=False)
        return
    
    settings = raid["settings"]
    
    # Check cooldown
    can_raid, remaining = await check_user_cooldown(user_id, raid["chat_id"])
    if not can_raid:
        mins = remaining // 60
        secs = remaining % 60
        await callback_query.answer(
            f"⏳ ʏᴏᴜ'ʀᴇ ᴏɴ ᴄᴏᴏʟᴅᴏᴡɴ! {mins}m {secs}s ʟᴇғᴛ",
            show_alert=True
        )
        return
    
    # Check balance
    user_data = await get_user_data(user_id)
    if user_data.get("balance", 0) < settings["start_charge"]:
        await callback_query.answer(
            f"💰 ɪɴsᴜғғɪᴄɪᴇɴᴛ ʙᴀʟᴀɴᴄᴇ! ɴᴇᴇᴅ {settings['start_charge']} ᴄᴏɪɴs",
            show_alert=True
        )
        return
    
    # Deduct entry fee
    await update_user_balance(user_id, -settings["start_charge"])
    
    # Add to participants
    await active_raids_collection.update_one(
        {"raid_id": raid_id},
        {"$push": {"participants": user_id}}
    )
    
    # Set cooldown
    await set_user_cooldown(user_id, raid["chat_id"], settings["cooldown_minutes"])
    
    await callback_query.answer("⚔️ ʏᴏᴜ'ᴠᴇ ᴊᴏɪɴᴇᴅ ᴛʜᴇ ʀᴀɪᴅ!", show_alert=False)


async def execute_raid(client, message, raid_id):
    """Execute the raid and distribute rewards"""
    raid = await active_raids_collection.find_one({"raid_id": raid_id})
    if not raid:
        return
    
    participants = raid["participants"]
    settings = raid["settings"]
    
    if len(participants) == 0:
        await message.edit_text("❌ ɴᴏ ᴏɴᴇ ᴊᴏɪɴᴇᴅ ᴛʜᴇ ʀᴀɪᴅ!")
        await active_raids_collection.delete_one({"raid_id": raid_id})
        return
    
    # Calculate outcomes
    results = []
    total_coins_gained = 0
    total_characters = 0
    
    for user_id in participants:
        # Weighted random outcome
        rand = random.randint(1, 100)
        
        if rand <= settings["character_chance"]:
            # Character reward
            character = await get_random_character(settings["allowed_rarities"])
            if character:
                await add_character_to_user(user_id, character)
                rarity_text = RARITY_MAP.get(character["rarity"], "🟢 ᴄᴏᴍᴍᴏɴ")
                results.append({
                    "user_id": user_id,
                    "type": "character",
                    "character": character,
                    "rarity": rarity_text
                })
                total_characters += 1
            else:
                # Fallback to coins if no character found
                coins = random.randint(settings["coin_min"], settings["coin_max"])
                await update_user_balance(user_id, coins)
                results.append({"user_id": user_id, "type": "coins", "amount": coins})
                total_coins_gained += coins
        
        elif rand <= settings["character_chance"] + settings["coin_chance"]:
            # Coin reward
            coins = random.randint(settings["coin_min"], settings["coin_max"])
            await update_user_balance(user_id, coins)
            results.append({"user_id": user_id, "type": "coins", "amount": coins})
            total_coins_gained += coins
        
        elif rand <= settings["character_chance"] + settings["coin_chance"] + settings["loss_chance"]:
            # Coin loss
            loss = random.randint(settings["coin_loss_min"], settings["coin_loss_max"])
            await update_user_balance(user_id, -loss)
            results.append({"user_id": user_id, "type": "loss", "amount": loss})
        
        else:
            # Nothing
            results.append({"user_id": user_id, "type": "nothing"})
    
    # Build result message
    result_text = (
        f"<blockquote>⚔️ <b>ʀᴀɪᴅ ᴄᴏᴍᴘʟᴇᴛᴇ</b> ⚔️</blockquote>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👥 <b>ᴘᴀʀᴛɪᴄɪᴘᴀɴᴛs:</b> <code>{len(participants)}</code>\n\n"
        f"<b>🏆 ʟᴏᴏᴛ ʀᴇᴘᴏʀᴛ:</b>\n"
    )
    
    for result in results:
        try:
            user = await client.get_users(result["user_id"])
            username = f"@{user.username}" if user.username else user.first_name
        except:
            username = "Unknown"
        
        if result["type"] == "character":
            result_text += f"• {username} — <code>ᴄᴀᴘᴛᴜʀᴇᴅ</code> 🎴 {result['rarity']}\n"
        elif result["type"] == "coins":
            result_text += f"• {username} — <code>ғᴏᴜɴᴅ {result['amount']} ᴄᴏɪɴs</code> 💰\n"
        elif result["type"] == "loss":
            result_text += f"• {username} — <code>ʟᴏsᴛ {result['amount']} ᴄᴏɪɴs</code> 💀\n"
        else:
            result_text += f"• {username} — <code>ғᴏᴜɴᴅ ɴᴏᴛʜɪɴɢ...</code> ❌\n"
    
    result_text += (
        f"\n━━━━━━━━━━━━━━━\n"
        f"💰 <b>ᴛᴏᴛᴀʟ ʟᴏᴏᴛ ᴠᴀʟᴜᴇ:</b> <code>{total_coins_gained:,} ᴄᴏɪɴs</code>\n"
        f"🎴 <b>ɴᴇᴡ ʀᴇʟɪᴄs ғᴏᴜɴᴅ:</b> <code>{total_characters}</code>\n\n"
        f"<i>ᴍᴇssᴀɢᴇ ᴘʀᴏᴠɪᴅᴇᴅ ʙʏ</i> <a href='https://t.me/siyaprobot'>sɪʏᴀ</a>"
    )
    
    await message.edit_text(result_text)
    await active_raids_collection.delete_one({"raid_id": raid_id})


# Admin commands
@shivuu.on_message(filters.command(["setraidcharge"]) & filters.user(OWNER_ID))
async def set_raid_charge(client, message):
    """Set raid start charge"""
    if len(message.command) < 2:
        await message.reply_text("ᴜsᴀɢᴇ: `/setraidcharge <amount>`")
        return
    
    try:
        amount = int(message.command[1])
        chat_id = message.chat.id
        
        await raid_settings_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"start_charge": amount}},
            upsert=True
        )
        
        await message.reply_text(f"✅ ʀᴀɪᴅ sᴛᴀʀᴛ ᴄʜᴀʀɢᴇ sᴇᴛ ᴛᴏ `{amount}` ᴄᴏɪɴs")
    except ValueError:
        await message.reply_text("❌ ɪɴᴠᴀʟɪᴅ ᴀᴍᴏᴜɴᴛ!")


@shivuu.on_message(filters.command(["setraidcooldown"]) & filters.user(OWNER_ID))
async def set_raid_cooldown(client, message):
    """Set raid cooldown"""
    if len(message.command) < 2:
        await message.reply_text("ᴜsᴀɢᴇ: `/setraidcooldown <minutes>`")
        return
    
    try:
        minutes = int(message.command[1])
        chat_id = message.chat.id
        
        await raid_settings_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"cooldown_minutes": minutes}},
            upsert=True
        )
        
        await message.reply_text(f"✅ ʀᴀɪᴅ ᴄᴏᴏʟᴅᴏᴡɴ sᴇᴛ ᴛᴏ `{minutes}` ᴍɪɴᴜᴛᴇs")
    except ValueError:
        await message.reply_text("❌ ɪɴᴠᴀʟɪᴅ ᴠᴀʟᴜᴇ!")


@shivuu.on_message(filters.command(["setraidrarities"]) & filters.user(OWNER_ID))
async def set_raid_rarities(client, message):
    """Set allowed rarities for raid rewards"""
    if len(message.command) < 2:
        await message.reply_text(
            "ᴜsᴀɢᴇ: `/setraidrarities <rarity_ids>`\n"
            "ᴇxᴀᴍᴘʟᴇ: `/setraidrarities 1,2,3,4,5`"
        )
        return
    
    try:
        rarities = [int(r.strip()) for r in message.command[1].split(",")]
        chat_id = message.chat.id
        
        await raid_settings_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"allowed_rarities": rarities}},
            upsert=True
        )
        
        rarity_names = [RARITY_MAP.get(r, f"Rarity {r}") for r in rarities]
        await message.reply_text(
            f"✅ ᴀʟʟᴏᴡᴇᴅ ʀᴀʀɪᴛɪᴇs:\n" + "\n".join(rarity_names)
        )
    except ValueError:
        await message.reply_text("❌ ɪɴᴠᴀʟɪᴅ ғᴏʀᴍᴀᴛ!")


@shivuu.on_message(filters.command(["raidsettings"]) & filters.user(OWNER_ID))
async def show_raid_settings(client, message):
    """Show current raid settings"""
    chat_id = message.chat.id
    settings = await get_raid_settings(chat_id)
    
    rarity_names = [RARITY_MAP.get(r, f"Rarity {r}") for r in settings["allowed_rarities"]]
    
    settings_text = (
        f"<blockquote><b>⚙️ ʀᴀɪᴅ sᴇᴛᴛɪɴɢs</b></blockquote>\n\n"
        f"💰 <b>sᴛᴀʀᴛ ᴄʜᴀʀɢᴇ:</b> `{settings['start_charge']}` ᴄᴏɪɴs\n"
        f"⏱ <b>ᴊᴏɪɴ ᴘʜᴀsᴇ:</b> `{settings['join_phase_duration']}s`\n"
        f"⏳ <b>ᴄᴏᴏʟᴅᴏᴡɴ:</b> `{settings['cooldown_minutes']}` ᴍɪɴᴜᴛᴇs\n"
        f"💵 <b>ᴍɪɴ ʙᴀʟᴀɴᴄᴇ:</b> `{settings['min_balance']}` ᴄᴏɪɴs\n\n"
        f"<b>💰 ʀᴇᴡᴀʀᴅ ʀᴀɴɢᴇs:</b>\n"
        f"├ ᴄᴏɪɴs: `{settings['coin_min']}-{settings['coin_max']}`\n"
        f"└ ʟᴏss: `{settings['coin_loss_min']}-{settings['coin_loss_max']}`\n\n"
        f"<b>🎲 ᴄʜᴀɴᴄᴇs:</b>\n"
        f"├ 🎴 ᴄʜᴀʀᴀᴄᴛᴇʀ: `{settings['character_chance']}%`\n"
        f"├ 💰 ᴄᴏɪɴs: `{settings['coin_chance']}%`\n"
        f"├ 💀 ʟᴏss: `{settings['loss_chance']}%`\n"
        f"└ ❌ ɴᴏᴛʜɪɴɢ: `{settings['nothing_chance']}%`\n\n"
        f"<b>🎴 ᴀʟʟᴏᴡᴇᴅ ʀᴀʀɪᴛɪᴇs:</b>\n" + 
        "\n".join([f"├ {r}" for r in rarity_names[:-1]]) +
        f"\n└ {rarity_names[-1]}"
    )
    
    await message.reply_text(settings_text)


LOGGER.info("Shadow Raid module loaded successfully!")