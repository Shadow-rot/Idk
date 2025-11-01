import math
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler
from shivu import application, user_collection

xay_cooldown = {}
pending_xay = {}

def sc(text):
    return text.translate(str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"
    ))

async def fmt_time(delta):
    s = int(delta.total_seconds())
    h, r = divmod(s, 3600)
    m, s = divmod(r, 60)
    return f"{h}ʜ {m}ᴍ {s}s"

async def balance(update, context):
    user_data = await user_collection.find_one({'id': update.effective_user.id})
    if not user_data:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🌸 sᴛᴀʀᴛ ʙᴏᴛ", url="https://t.me/waifukunbot")]])
        await update.message.reply_text("🌸 ʜᴇʏ, ʏᴏᴜ'ʀᴇ ɴᴏᴛ ʀᴇɢɪsᴛᴇʀᴇᴅ ʏᴇᴛ.\nᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ᴛᴏ sᴛᴀʀᴛ 🌸", reply_markup=kb)
        return

    bal = math.floor(user_data.get('balance', 0))
    bank = math.floor(user_data.get('bank', 0))
    await update.message.reply_markdown(
        f"🏦 **{sc('balance report')}** 🏦\n\n"
        f"💰 ᴡᴀʟʟᴇᴛ: `{bal}` ɢᴏʟᴅ\n💳 ʙᴀɴᴋ: `{bank}` ɢᴏʟᴅ\n\nᴋᴇᴇᴘ ʜᴜɴᴛɪɴɢ 🍂"
    )

async def xay(update, context):
    sender_id = update.effective_user.id
    if not update.message.reply_to_message:
        await update.message.reply_text("ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜsᴇʀ ᴛᴏ ᴘᴀʏ ᴛʜᴇᴍ.")
        return

    recipient = update.message.reply_to_message.from_user
    if recipient.id == sender_id:
        await update.message.reply_text("ʏᴏᴜ ᴄᴀɴ'ᴛ ᴘᴀʏ ʏᴏᴜʀsᴇʟғ!")
        return

    if sender_id in xay_cooldown and (datetime.utcnow() - xay_cooldown[sender_id]) < timedelta(minutes=10):
        await update.message.reply_text("⏳ ᴡᴀɪᴛ 10 ᴍɪɴᴜᴛᴇs ʙᴇғᴏʀᴇ ɴᴇxᴛ ᴘᴀʏᴍᴇɴᴛ.")
        return

    try:
        amount = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("ᴜsᴀɢᴇ: `/pay <amount>`", parse_mode="Markdown")
        return

    if amount <= 0:
        await update.message.reply_text("ᴀᴍᴏᴜɴᴛ ᴍᴜsᴛ ʙᴇ ᴘᴏsɪᴛɪᴠᴇ.")
        return
    if amount > 1_000_000:
        await update.message.reply_text("ᴍᴀx ᴘᴀʏᴍᴇɴᴛ: `1,000,000` ɢᴏʟᴅ", parse_mode="Markdown")
        return

    sender_data = await user_collection.find_one({'id': sender_id})
    if not sender_data or sender_data.get('balance', 0) < amount:
        await update.message.reply_text("ɪɴsᴜғғɪᴄɪᴇɴᴛ ʙᴀʟᴀɴᴄᴇ.")
        return

    xay_id = f"{sender_id}_{recipient.id}_{amount}"
    pending_xay[xay_id] = {'time': datetime.utcnow()}

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ ᴄᴏɴғɪʀᴍ", callback_data=f"xay_confirm_{xay_id}"),
        InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data=f"xay_cancel_{xay_id}")
    ]])

    msg = await update.message.reply_markdown(
        f"💸 **ᴘᴀʏᴍᴇɴᴛ ᴄᴏɴғɪʀᴍᴀᴛɪᴏɴ**\n\n"
        f"sᴇɴᴅ `{amount}` ɢᴏʟᴅ ᴛᴏ **{recipient.first_name}**?\n\n⏱️ ᴇxᴘɪʀᴇs ɪɴ 30 sᴇᴄᴏɴᴅs",
        reply_markup=kb
    )
    context.application.job_queue.run_once(lambda c: delete_expired_xay(msg, xay_id), 30)

async def delete_expired_xay(msg, xay_id):
    if xay_id in pending_xay:
        del pending_xay[xay_id]
        try:
            await msg.delete()
        except:
            pass

async def xay_callback(update, context):
    query = update.callback_query
    await query.answer()

    data = query.data.split('_')
    action = data[1]
    xay_id = '_'.join(data[2:])

    if xay_id not in pending_xay:
        await query.edit_message_text("⏱️ ᴘᴀʏᴍᴇɴᴛ ᴇxᴘɪʀᴇᴅ.")
        return

    sender_id = int(xay_id.split('_')[0])
    if query.from_user.id != sender_id:
        await query.answer("ᴏɴʟʏ sᴇɴᴅᴇʀ ᴄᴀɴ ᴄᴏɴғɪʀᴍ!", show_alert=True)
        return

    if action == "cancel":
        del pending_xay[xay_id]
        await query.edit_message_text("❌ ᴘᴀʏᴍᴇɴᴛ ᴄᴀɴᴄᴇʟʟᴇᴅ.")
        return

    recipient_id = int(xay_id.split('_')[1])
    amount = int(xay_id.split('_')[2])

    await user_collection.update_one({'id': sender_id}, {'$inc': {'balance': -amount}})
    await user_collection.update_one({'id': recipient_id}, {'$inc': {'balance': amount}})

    xay_cooldown[sender_id] = datetime.utcnow()
    del pending_xay[xay_id]

    recipient_data = await user_collection.find_one({'id': recipient_id})
    recipient_name = recipient_data.get('first_name', 'ᴜɴᴋɴᴏᴡɴ')
    await query.edit_message_text(f"✅ ᴘᴀɪᴅ `{amount}` ɢᴏʟᴅ ᴛᴏ **{recipient_name}**!", parse_mode="Markdown")

async def mtop(update, context):
    top_users = await user_collection.find(
        {}, projection={'id': 1, 'first_name': 1, 'last_name': 1, 'balance': 1}
    ).sort('balance', -1).limit(10).to_list(10)

    msg = f"🏆 <b>{sc('top 10 rich hunters')}</b> 🏆\n\n"
    for i, u in enumerate(top_users, 1):
        name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
        msg += f"{i}. <a href='tg://user?id={u['id']}'>{name}</a> — <code>{u.get('balance', 0)}</code> ɢᴏʟᴅ\n"
    
    msg += f"\n<a href='https://files.catbox.moe/ydjas6.mp4'>&#8205;</a>"
    await update.message.reply_text(msg, parse_mode="HTML")

async def daily_reward(update, context):
    user_id = update.effective_user.id
    user_data = await user_collection.find_one({'id': user_id}, projection={'last_daily_reward': 1})

    if not user_data:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🌸 ᴊᴏɪɴ", url="https://t.me/PICK_X_SUPPORT")]])
        await update.message.reply_text("🌸 ɴᴏᴛ ʀᴇɢɪsᴛᴇʀᴇᴅ ʏᴇᴛ.", reply_markup=kb)
        return

    last = user_data.get('last_daily_reward')
    if last and last.date() == datetime.utcnow().date():
        rem = timedelta(days=1) - (datetime.utcnow() - last)
        await update.message.reply_text(f"⏳ ɴᴇxᴛ ʀᴇᴡᴀʀᴅ ɪɴ: `{await fmt_time(rem)}`", parse_mode="Markdown")
        return

    await user_collection.update_one(
        {'id': user_id},
        {'$inc': {'balance': 2000}, '$set': {'last_daily_reward': datetime.utcnow()}}
    )
    await update.message.reply_text("🎉 ᴄʟᴀɪᴍᴇᴅ `2000` ɢᴏʟᴅ!", parse_mode="Markdown")

async def roll(update, context):
    user_id = update.effective_user.id
    try:
        amount, choice = int(context.args[0]), context.args[1].upper()
    except (IndexError, ValueError):
        await update.message.reply_text("ᴜsᴀɢᴇ: `/roll <amount> <ODD/EVEN>`", parse_mode="Markdown")
        return

    user_data = await user_collection.find_one({'id': user_id})
    if not user_data or user_data.get('balance', 0) < amount:
        await update.message.reply_text("ɪɴsᴜғғɪᴄɪᴇɴᴛ ʙᴀʟᴀɴᴄᴇ.")
        return

    dice = await context.bot.send_dice(update.effective_chat.id, "🎲")
    result = "ODD" if dice.dice.value % 2 else "EVEN"
    won = choice == result
    bal_change = amount if won else -amount
    xp_change = 4 if won else -2

    await user_collection.update_one(
        {'id': user_id},
        {'$inc': {'balance': bal_change, 'user_xp': xp_change}}
    )
    await update.message.reply_markdown(
        f"🎲 `{dice.dice.value}` | {'🟢 ᴡᴏɴ' if won else '🔴 ʟᴏsᴛ'}\n"
        f"ʙᴀʟ: `{bal_change:+}` | XP: `{xp_change:+}`"
    )

async def xp(update, context):
    user_data = await user_collection.find_one({'id': update.effective_user.id})
    if not user_data:
        await update.message.reply_text("ᴜsᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ.")
        return

    xp_val = user_data.get('user_xp', 0)
    lvl = min(math.floor(math.sqrt(xp_val / 100)) + 1, 100)
    rank = next((r for l, r in [(1, "E"), (10, "D"), (30, "C"), (50, "B"), (70, "A"), (90, "S")] if lvl <= l), "S")
    await update.message.reply_text(f"⚡ ʟᴠʟ: `{lvl}` | ʀᴀɴᴋ: `{rank}`", parse_mode="Markdown")

# Register command handlers
application.add_handler(CommandHandler("bal", balance, block=False))
application.add_handler(CommandHandler("pay", xay, block=False))
application.add_handler(CommandHandler("Tophunters", mtop, block=False))
application.add_handler(CommandHandler("cclaim", daily_reward, block=False))
application.add_handler(CommandHandler("roll", roll, block=False))
application.add_handler(CommandHandler("xp", xp, block=False))