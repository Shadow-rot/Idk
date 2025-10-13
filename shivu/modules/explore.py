import random
from telegram.ext import CommandHandler, CallbackContext
from telegram import Update
from datetime import datetime, timedelta

from shivu import (
    application,
    user_collection,
    LOGGER
)

# Constants
COOLDOWN_DURATION = 73  # seconds
EXPLORE_FEE = 300
MIN_REWARD = 600
MAX_REWARD = 1000
MIN_BALANCE = 500

# Cooldown tracking
user_cooldowns = {}

# Exploration messages
EXPLORE_MESSAGES = [
    "explored a dungeon",
    "ventured into a dark forest",
    "discovered ancient ruins",
    "infiltrated an elvish village",
    "raided a goblin nest",
    "survived an orc den"
]

async def explore_cmd(update: Update, context: CallbackContext) -> None:
    """Command to explore and get random rewards"""
    try:
        # Check if command is used in private
        if update.effective_chat.type == "private":
            await update.message.reply_text(
                "❌ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ᴄᴀɴ ᴏɴʟʏ ʙᴇ ᴜsᴇᴅ ɪɴ ɢʀᴏᴜᴘs!"
            )
            return

        # Check if command is a reply
        if update.message.reply_to_message:
            await update.message.reply_text(
                "❌ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ᴄᴀɴɴᴏᴛ ʙᴇ ᴜsᴇᴅ ᴀs ᴀ ʀᴇᴘʟʏ!"
            )
            return

        user_id = update.effective_user.id
        current_time = datetime.utcnow()

        # Check cooldown
        if user_id in user_cooldowns:
            time_passed = (current_time - user_cooldowns[user_id]).total_seconds()
            if time_passed < COOLDOWN_DURATION:
                remaining = int(COOLDOWN_DURATION - time_passed)
                await update.message.reply_text(
                    f"⏰ ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ {remaining} sᴇᴄᴏɴᴅs ʙᴇғᴏʀᴇ ᴇxᴘʟᴏʀɪɴɢ ᴀɢᴀɪɴ!"
                )
                return

        # Get user's balance
        user = await user_collection.find_one({'id': user_id})
        if not user:
            await update.message.reply_text("❌ ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴀɴ ᴀᴄᴄᴏᴜɴᴛ ʏᴇᴛ!")
            return

        balance = user.get('balance', 0)
        
        # Check minimum balance
        if balance < MIN_BALANCE:
            await update.message.reply_text(
                f"❌ ʏᴏᴜ ɴᴇᴇᴅ ᴀᴛ ʟᴇᴀsᴛ {MIN_BALANCE} ᴛᴏᴋᴇɴs ᴛᴏ ᴇxᴘʟᴏʀᴇ!"
            )
            return

        # Deduct exploration fee
        await user_collection.update_one(
            {'id': user_id},
            {'$inc': {'balance': -EXPLORE_FEE}}
        )

        # Calculate reward and update balance
        reward = random.randint(MIN_REWARD, MAX_REWARD)
        await user_collection.update_one(
            {'id': user_id},
            {'$inc': {'balance': reward}}
        )

        # Update cooldown
        user_cooldowns[user_id] = current_time

        # Send result message
        action = random.choice(EXPLORE_MESSAGES)
        await update.message.reply_text(
            f"🗺️ ʏᴏᴜ {action} ᴀɴᴅ ғᴏᴜɴᴅ {reward} ᴛᴏᴋᴇɴs!\n"
            f"💰 ᴇxᴘʟᴏʀᴀᴛɪᴏɴ ғᴇᴇ: -{EXPLORE_FEE} ᴛᴏᴋᴇɴs"
        )

    except Exception as e:
        LOGGER.error(f"Error in explore command: {e}")
        await update.message.reply_text(
            "❌ ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴡʜɪʟᴇ ᴇxᴘʟᴏʀɪɴɢ!"
        )

def register_handlers():
    """Register the explore command handler"""
    application.add_handler(CommandHandler("explore", explore_cmd))

# Register handlers
register_handlers()