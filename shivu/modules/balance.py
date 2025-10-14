import math
import random
import time
import asyncio
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler
from shivu import application, user_collection

# Cooldowns and helpers
pay_cooldown = {}

# ──────────────────────────────
# Helper Functions
# ──────────────────────────────

def to_small_caps(text):
    smallcaps = str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"
    )
    return text.translate(smallcaps)

async def format_time_delta(delta):
    seconds = int(delta.total_seconds())
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}ʜ {minutes}ᴍ {seconds}s"

# ──────────────────────────────
# ʙᴀʟᴀɴᴄᴇ ᴄᴏᴍᴍᴀɴᴅ
# ──────────────────────────────

async def balance(update, context):
    user = update.effective_user
    user_id = user.id

    user_data = await user_collection.find_one({'id': user_id})

    if not user_data:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🌸 sᴛᴀʀᴛ ᴡᴀɪꜰᴜᴋᴜɴ ʙᴏᴛ", url="https://t.me/waifukunbot")]]
        )
        await update.message.reply_text(
            f"🌸 ʜᴇʏ {user.first_name}, ʏᴏᴜ'ʀᴇ ɴᴏᴛ ʏᴇᴛ ᴀ ʀᴇɢɪꜱᴛᴇʀᴇᴅ ʜᴜɴᴛᴇʀ.\n\n"
            f"ᴄʟɪᴄᴋ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ꜱᴛᴀʀᴛ ʏᴏᴜʀ ᴊᴏᴜʀɴᴇʏ ᴡɪᴛʜ ᴡᴀɪꜰᴜᴋᴜɴ ʙᴏᴛ 🌸",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        return

    balance_amount = math.floor(user_data.get('balance', 0))
    bank_balance = math.floor(user_data.get('bank', 0))

    balance_message = (
        f"🏦 **{to_small_caps('hunter balance report')}** 🏦\n\n"
        f"💰 ᴡᴀʟʟᴇᴛ: `{balance_amount}` ɢᴏʟᴅ ᴄᴏɪɴꜱ\n"
        f"💳 ʙᴀɴᴋ: `{bank_balance}` ɢᴏʟᴅ ᴄᴏɪɴꜱ\n\n"
        f"ᴋᴇᴇᴘ ʜᴜɴᴛɪɴɢ, ᴡᴀʀʀɪᴏʀ 🍂"
    )
    await update.message.reply_markdown(balance_message)

# ──────────────────────────────
# ᴘᴀʏ ᴄᴏᴍᴍᴀɴᴅ
# ──────────────────────────────

async def pay(update, context):
    sender_id = update.effective_user.id

    if not update.message.reply_to_message:
        await update.message.reply_text(f"ᴘʟᴇᴀꜱᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ʜᴜɴᴛᴇʀ ᴛᴏ ᴜꜱᴇ `/pay`.", parse_mode="Markdown")
        return

    recipient = update.message.reply_to_message.from_user

    if recipient.id == sender_id:
        await update.message.reply_text("ʏᴏᴜ ᴄᴀɴ'ᴛ ᴘᴀʏ ʏᴏᴜʀꜱᴇʟꜰ!")
        return

    # Cooldown
    if sender_id in pay_cooldown:
        last_time = pay_cooldown[sender_id]
        if (datetime.utcnow() - last_time) < timedelta(minutes=30):
            await update.message.reply_text("⏳ ʏᴏᴜ ᴄᴀɴ ᴜꜱᴇ /pay ᴀɢᴀɪɴ ᴀꜰᴛᴇʀ 30 ᴍɪɴᴜᴛᴇꜱ.")
            return

    try:
        amount = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("ᴜꜱᴀɢᴇ: `/pay <amount>`", parse_mode="Markdown")
        return

    if amount <= 0:
        await update.message.reply_text("ᴀᴍᴏᴜɴᴛ ᴍᴜꜱᴛ ʙᴇ ᴘᴏꜱɪᴛɪᴠᴇ.")
        return
    elif amount > 1_000_000:
        await update.message.reply_text("ʏᴏᴜ ᴄᴀɴ ᴏɴʟʏ ᴘᴀʏ ᴜᴘ ᴛᴏ `1,000,000` ɢᴏʟᴅ ᴄᴏɪɴꜱ.", parse_mode="Markdown")
        return

    sender_data = await user_collection.find_one({'id': sender_id})
    if not sender_data or sender_data.get('balance', 0) < amount:
        await update.message.reply_text("ɪɴꜱᴜꜰꜰɪᴄɪᴇɴᴛ ꜰᴜɴᴅꜱ.")
        return

    await user_collection.update_one({'id': sender_id}, {'$inc': {'balance': -amount}})
    await user_collection.update_one({'id': recipient.id}, {'$inc': {'balance': amount}})

    pay_cooldown[sender_id] = datetime.utcnow()
    recipient_link = f"[{recipient.first_name}](https://t.me/{recipient.username})" if recipient.username else recipient.first_name

    await update.message.reply_markdown(
        f"✅ ʏᴏᴜ ᴘᴀɪᴅ **${amount}** ɢᴏʟᴅ ᴄᴏɪɴꜱ ᴛᴏ {recipient_link}!"
    )

# ──────────────────────────────
# ᴛᴏᴘʜᴜɴᴛᴇʀꜱ ᴄᴏᴍᴍᴀɴᴅ
# ──────────────────────────────

async def mtop(update, context):
    top_users = await user_collection.find(
        {}, projection={'id': 1, 'first_name': 1, 'last_name': 1, 'balance': 1}
    ).sort('balance', -1).limit(10).to_list(10)

    message = f"🏆 **{to_small_caps('top 10 rich hunters')}** 🏆\n\n"
    for i, user in enumerate(top_users, start=1):
        first_name = user.get('first_name', 'ᴜɴᴋɴᴏᴡɴ')
        last_name = user.get('last_name', '')
        full_name = f"{first_name} {last_name}".strip()
        user_id = user.get('id')
        balance = user.get('balance', 0)
        message += f"{i}. <a href='tg://user?id={user_id}'>{full_name}</a> — `{balance}` ɢᴏʟᴅ ᴄᴏɪɴꜱ\n"

    await update.message.reply_photo(
        photo='https://telegra.ph/file/07283c3102ae87f3f2833.png',
        caption=message,
        parse_mode="HTML"
    )

# ──────────────────────────────
# ᴅᴀɪʟʏ ᴄʟᴀɪᴍ ᴄᴏᴍᴍᴀɴᴅ
# ──────────────────────────────

async def daily_reward(update, context):
    user = update.effective_user
    user_id = user.id

    user_data = await user_collection.find_one({'id': user_id}, projection={'last_daily_reward': 1, 'balance': 1})

    if not user_data:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🌸 sᴛᴀʀᴛ Jᴏɪɴ ɢʀᴏᴜᴘ", url="https://t.me/PICK_X_SUPPORT")]]
        )
        await update.message.reply_text(
            f"🌸 ʜᴇʏ {user.first_name}, ʏᴏᴜ'ʀᴇ ɴᴏᴛ ʏᴇᴛ ᴀ ʜᴜɴᴛᴇʀ.\n\n"
            f"ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ᴛᴏ ʙᴇɢɪɴ ᴡɪᴛʜ ᴡᴀɪꜰᴜᴋᴜɴ ʙᴏᴛ 🌸",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        return

    last_claimed = user_data.get('last_daily_reward')
    if last_claimed and last_claimed.date() == datetime.utcnow().date():
        remaining = timedelta(days=1) - (datetime.utcnow() - last_claimed)
        formatted = await format_time_delta(remaining)
        await update.message.reply_text(
            f"⏳ ʏᴏᴜ ᴀʟʀᴇᴀᴅʏ ᴄʟᴀɪᴍᴇᴅ ᴛᴏᴅᴀʏ.\nɴᴇxᴛ ʀᴇᴡᴀʀᴅ ɪɴ: `{formatted}`",
            parse_mode="Markdown"
        )
        return

    await user_collection.update_one(
        {'id': user_id},
        {'$inc': {'balance': 2000}, '$set': {'last_daily_reward': datetime.utcnow()}}
    )
    await update.message.reply_text("🎉 ʏᴏᴜ ᴄʟᴀɪᴍᴇᴅ `$2000` ɢᴏʟᴅ ᴄᴏɪɴꜱ ᴀꜱ ʏᴏᴜʀ ᴅᴀɪʟʏ ʀᴇᴡᴀʀᴅ!", parse_mode="Markdown")

# ──────────────────────────────
# ʀᴏʟʟ ᴄᴏᴍᴍᴀɴᴅ
# ──────────────────────────────

async def roll(update, context):
    user_id = update.effective_user.id
    try:
        amount = int(context.args[0])
        choice = context.args[1].upper()
    except (IndexError, ValueError):
        await update.message.reply_text("ᴜꜱᴀɢᴇ: `/roll <amount> <ODD/EVEN>`", parse_mode="Markdown")
        return

    user_data = await user_collection.find_one({'id': user_id})
    if not user_data:
        await update.message.reply_text("ᴜꜱᴇʀ ᴅᴀᴛᴀ ɴᴏᴛ ꜰᴏᴜɴᴅ.")
        return

    balance = user_data.get('balance', 0)
    if balance < amount:
        await update.message.reply_text("ɪɴꜱᴜꜰꜰɪᴄɪᴇɴᴛ ʙᴀʟᴀɴᴄᴇ.")
        return

    dice_message = await context.bot.send_dice(update.effective_chat.id, "🎲")
    dice_value = dice_message.dice.value
    result = "ODD" if dice_value % 2 != 0 else "EVEN"

    xp_change = 4 if choice == result else -2
    balance_change = amount if choice == result else -amount
    await user_collection.update_one({'id': user_id}, {'$inc': {'balance': balance_change, 'user_xp': xp_change}})

    msg = (
        f"🎲 ᴅɪᴄᴇ: `{dice_value}`\n"
        f"{'🟢 ʏᴏᴜ ᴡᴏɴ!' if choice == result else '🔴 ʏᴏᴜ ʟᴏꜱᴛ!'}\n"
        f"ʙᴀʟᴀɴᴄᴇ ᴄʜᴀɴɢᴇ: `{balance_change}`\n"
        f"XP ᴄʜᴀɴɢᴇ: `{xp_change}`"
    )
    await update.message.reply_markdown(msg)

# ──────────────────────────────
# XP ᴄᴏᴍᴍᴀɴᴅ
# ──────────────────────────────

async def xp(update, context):
    user_id = update.effective_user.id
    user_data = await user_collection.find_one({'id': user_id})
    if not user_data:
        await update.message.reply_text("ᴜꜱᴇʀ ᴅᴀᴛᴀ ɴᴏᴛ ꜰᴏᴜɴᴅ.")
        return

    xp = user_data.get('user_xp', 0)
    level = min(math.floor(math.sqrt(xp / 100)) + 1, 100)
    ranks = {1: "E", 10: "D", 30: "C", 50: "B", 70: "A", 90: "S"}
    rank = next((r for lim, r in ranks.items() if level <= lim), "S")

    await update.message.reply_text(f"⚡ ʏᴏᴜʀ ʟᴇᴠᴇʟ: `{level}`\nʀᴀɴᴋ: `{rank}`", parse_mode="Markdown")

# ──────────────────────────────
# ʜᴀɴᴅʟᴇʀꜱ
# ──────────────────────────────

application.add_handler(CommandHandler("bal", balance, block=False))
application.add_handler(CommandHandler("pay", pay, block=False))
application.add_handler(CommandHandler("Tophunters", mtop, block=False))
application.add_handler(CommandHandler("cclaim", daily_reward, block=False))
application.add_handler(CommandHandler("roll", roll, block=False))
application.add_handler(CommandHandler("xp", xp, block=False))