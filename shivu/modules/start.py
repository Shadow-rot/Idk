import random
from html import escape 

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler

from shivu import application, PHOTO_URL, SUPPORT_CHAT, UPDATE_CHAT, BOT_USERNAME, db, GROUP_ID
from shivu import user_collection, user_totals_collection

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

async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username
    args = context.args
    referring_user_id = None

    if args and args[0].startswith('r_'):
        referring_user_id = int(args[0][2:])

    user_data = await user_collection.find_one({"id": user_id})
    total_users = await user_collection.count_documents({})

    if user_data is None:
        new_user = {
            "id": user_id, 
            "first_name": first_name, 
            "username": username, 
            "tokens": 500, 
            "characters": [],
            "referred_users": 0
        }
        await user_collection.insert_one(new_user)

        if referring_user_id:
            referring_user_data = await user_collection.find_one({"id": referring_user_id})
            if referring_user_data:
                await user_collection.update_one(
                    {"id": referring_user_id}, 
                    {"$inc": {"tokens": 1000, "referred_users": 1}}
                )
                referrer_message = f"🎊 <b>{to_small_caps('referral success')}</b>\n\n🌟 {escape(first_name)} {to_small_caps('joined using your link')}\n💎 {to_small_caps('earned')} <b>1000 {to_small_caps('tokens')}</b>"
                try:
                    await context.bot.send_message(
                        chat_id=referring_user_id, 
                        text=referrer_message,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    print(f"Failed to send referral message: {e}")

        await context.bot.send_message(
            chat_id=GROUP_ID, 
            text=f"✦ <b>{to_small_caps('new player')}</b>\n\n👤 {to_small_caps('user')}: <a href='tg://user?id={user_id}'>{escape(first_name)}</a>\n🆔 {to_small_caps('id')}: <code>{user_id}</code>\n👥 {to_small_caps('total')}: <b>{total_users}</b>", 
            parse_mode='HTML'
        )
        user_data = new_user
    else:
        if user_data['first_name'] != first_name or user_data['username'] != username:
            await user_collection.update_one(
                {"id": user_id}, 
                {"$set": {"first_name": first_name, "username": username}}
            )

    # Get actual user stats from database
    user_balance = user_data.get('balance', 0)  # Gold coins from wallet
    user_totals = await user_totals_collection.find_one({'id': user_id})
    total_characters = user_totals['count'] if user_totals else 0
    referred_count = user_data.get('referred_users', 0)

    if update.effective_chat.type == "private":
        referral_link = f"https://t.me/{BOT_USERNAME}?start=r_{user_id}"
        
        caption = f"""
┏━━━━━━━━━━━━━━━━━━━┓
  ⚡ <b>{to_small_caps('anime catcher')}</b> ⚡
┗━━━━━━━━━━━━━━━━━━━┛

🌟 {to_small_caps('hey')} <a href='tg://user?id={user_id}'>{escape(first_name)}</a>

🎯 {to_small_caps('catch collect dominate')}
✨ {to_small_caps('build your empire now')}

━━━━━━━━━━━━━━━━━━━
🪙 {to_small_caps('wallet')}: <b>{user_balance}</b> {to_small_caps('gold')}
🎴 {to_small_caps('slaves')}: <b>{total_characters}</b>
👤 {to_small_caps('referrals')}: <b>{referred_count}</b>
━━━━━━━━━━━━━━━━━━━

🎁 {to_small_caps('invite get')} <b>1000 🪙</b>
"""

        keyboard = [
            [
                InlineKeyboardButton(f"⚔️ {to_small_caps('play')}", url=f'https://t.me/{BOT_USERNAME}?startgroup=new'),
                InlineKeyboardButton(f"🪙 {to_small_caps('earn')}", callback_data='earn')
            ],
            [
                InlineKeyboardButton(f"📊 {to_small_caps('stats')}", callback_data='stats'),
                InlineKeyboardButton(f"❔ {to_small_caps('help')}", callback_data='help')
            ],
            [
                InlineKeyboardButton(f"🔗 {to_small_caps('invite')}", callback_data='referral')
            ],
            [
                InlineKeyboardButton(f"💬 {to_small_caps('support')}", url=f'https://t.me/PICK_X_SUPPORT'),
                InlineKeyboardButton(f"📣 {to_small_caps('updates')}", url=f'https://t.me/PICK_X_UPDATE')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        video_url = "https://checker.in/go/10483702"
        
        await context.bot.send_video(
            chat_id=update.effective_chat.id, 
            video=video_url, 
            caption=caption, 
            reply_markup=reply_markup, 
            parse_mode='HTML'
        )
    else:
        caption = f"""
⚡ <b>{to_small_caps('hey')} {escape(first_name)}</b>

✨ {to_small_caps('im alive and ready')}
🎴 {to_small_caps('catch anime with me')}
"""
        keyboard = [
            [InlineKeyboardButton(f"🌟 {to_small_caps('start')}", url=f'https://t.me/{BOT_USERNAME}?start=true')],
            [InlineKeyboardButton(f"➕ {to_small_caps('add me')}", url=f'https://t.me/{BOT_USERNAME}?startgroup=new')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        video_url = "https://checker.in/go/10590132"
        
        await context.bot.send_video(
            chat_id=update.effective_chat.id, 
            video=video_url, 
            caption=caption, 
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

async def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = await user_collection.find_one({"id": user_id})
    user_totals = await user_totals_collection.find_one({'id': user_id})
    
    if query.data == 'stats':
        user_balance = user_data.get('balance', 0)
        total_characters = user_totals['count'] if user_totals else 0
        referred_count = user_data.get('referred_users', 0)
        
        stats_text = f"""
┏━━━━━━━━━━━━━━━━━━━┓
  📊 <b>{to_small_caps('your stats')}</b>
┗━━━━━━━━━━━━━━━━━━━┛

👤 {to_small_caps('name')}: {escape(user_data.get('first_name', 'unknown'))}
🆔 {to_small_caps('id')}: <code>{user_id}</code>

━━━━━━━━━━━━━━━━━━━
🪙 {to_small_caps('wallet')}: <b>{user_balance}</b> {to_small_caps('gold')}
🎴 {to_small_caps('total slaves')}: <b>{total_characters}</b>
👤 {to_small_caps('referrals')}: <b>{referred_count}</b>
━━━━━━━━━━━━━━━━━━━

⚡ {to_small_caps('keep grinding warrior')}
"""
        await query.edit_message_caption(
            caption=stats_text,
            reply_markup=query.message.reply_markup,
            parse_mode='HTML'
        )
    
    elif query.data == 'earn':
        earn_text = f"""
┏━━━━━━━━━━━━━━━━━━━┓
  🪙 <b>{to_small_caps('earn gold')}</b>
┗━━━━━━━━━━━━━━━━━━━┛

🎁 {to_small_caps('referral rewards')}
━━━━━━━━━━━━━━━━━━━
✨ {to_small_caps('you earn')}: <b>1000 🪙</b>
🌟 {to_small_caps('friend gets')}: <b>500 🪙</b>

📝 {to_small_caps('daily rewards')}
━━━━━━━━━━━━━━━━━━━
🎯 /claim → {to_small_caps('get')} <b>2000 🪙</b> {to_small_caps('daily')}
🎲 /roll → {to_small_caps('gamble and win big')}

💰 {to_small_caps('more ways')}
━━━━━━━━━━━━━━━━━━━
⚔️ {to_small_caps('play games')}
🎴 {to_small_caps('collect rare slaves')}
💸 {to_small_caps('trade characters')}

⚡ {to_small_caps('start earning now')}
"""
        await query.edit_message_caption(
            caption=earn_text,
            reply_markup=query.message.reply_markup,
            parse_mode='HTML'
        )
    
    elif query.data == 'help':
        help_text = f"""
┏━━━━━━━━━━━━━━━━━━━┓
  ❔ <b>{to_small_caps('commands')}</b>
┗━━━━━━━━━━━━━━━━━━━┛

🪙 {to_small_caps('economy')}
━━━━━━━━━━━━━━━━━━━
/bal → {to_small_caps('check wallet')}
/pay → {to_small_caps('send gold')}
/claim → {to_small_caps('daily reward')}
/roll → {to_small_caps('gamble gold')}

🎴 {to_small_caps('collection')}
━━━━━━━━━━━━━━━━━━━
/slaves → {to_small_caps('all characters')}
/myslaves → {to_small_caps('your collection')}

⚔️ {to_small_caps('gameplay')}
━━━━━━━━━━━━━━━━━━━
/catch → {to_small_caps('catch slaves')}
/trade → {to_small_caps('trade slaves')}

📊 {to_small_caps('ranking')}
━━━━━━━━━━━━━━━━━━━
/xp → {to_small_caps('check rank')}
/tophunters → {to_small_caps('leaderboard')}

💡 {to_small_caps('join support for help')}
"""
        await query.edit_message_caption(
            caption=help_text,
            reply_markup=query.message.reply_markup,
            parse_mode='HTML'
        )
    
    elif query.data == 'referral':
        referral_link = f"https://t.me/{BOT_USERNAME}?start=r_{user_id}"
        referred_count = user_data.get('referred_users', 0)
        
        referral_text = f"""
┏━━━━━━━━━━━━━━━━━━━┓
  🔗 <b>{to_small_caps('invite program')}</b>
┗━━━━━━━━━━━━━━━━━━━┛

👤 {to_small_caps('your referrals')}: <b>{referred_count}</b>
🪙 {to_small_caps('earned')}: <b>{referred_count * 1000}</b> {to_small_caps('gold')}

📋 {to_small_caps('how to invite')}
━━━━━━━━━━━━━━━━━━━
1️⃣ {to_small_caps('copy link below')}
2️⃣ {to_small_caps('share with friends')}
3️⃣ {to_small_caps('they click and start bot')}
4️⃣ {to_small_caps('instant rewards')}

🎁 {to_small_caps('reward breakdown')}
━━━━━━━━━━━━━━━━━━━
✨ {to_small_caps('you get')} → <b>1000 🪙</b>
🌟 {to_small_caps('friend gets')} → <b>500 🪙</b>

🔗 {to_small_caps('your invite link')}
━━━━━━━━━━━━━━━━━━━
<code>{referral_link}</code>

💡 {to_small_caps('tap to copy link')}
"""
        await query.edit_message_caption(
            caption=referral_text,
            reply_markup=query.message.reply_markup,
            parse_mode='HTML'
        )

start_handler = CommandHandler('start', start, block=False)
application.add_handler(start_handler)

callback_handler = CallbackQueryHandler(button_callback)
application.add_handler(callback_handler)