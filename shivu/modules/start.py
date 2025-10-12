import random
from html import escape 

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler

from shivu import application, PHOTO_URL, SUPPORT_CHAT, UPDATE_CHAT, BOT_USERNAME, db, GROUP_ID
from shivu import user_collection, refeer_collection

async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username
    args = context.args
    referring_user_id = None

    if args and args[0].startswith('r_'):
        referring_user_id = int(args[0][2:])

    user_data = await user_collection.find_one({"id": user_id})

    # Get total users count
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
                referrer_message = f"🎉 <b>Referral Bonus!</b>\n\n✨ {escape(first_name)} joined using your link!\n💰 You earned <b>1000 tokens</b>!"
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
            text=f"✨ <b>NEW USER JOINED</b>\n\n👤 User: <a href='tg://user?id={user_id}'>{escape(first_name)}</a>\n🆔 ID: <code>{user_id}</code>\n👥 Total Users: <b>{total_users}</b>", 
            parse_mode='HTML'
        )
        user_data = new_user
    else:
        if user_data['first_name'] != first_name or user_data['username'] != username:
            await user_collection.update_one(
                {"id": user_id}, 
                {"$set": {"first_name": first_name, "username": username}}
            )

    # Get user stats
    user_tokens = user_data.get('tokens', 0)
    user_chars = len(user_data.get('characters', []))
    referred_count = user_data.get('referred_users', 0)

    if update.effective_chat.type == "private":
        # Generate referral link
        referral_link = f"https://t.me/{BOT_USERNAME}?start=r_{user_id}"
        
        caption = f"""
╔═══════════════════╗
   🌸 <b>WELCOME TO ANIME CATCHER</b> 🌸
╚═══════════════════╝

👋 Hey <a href='tg://user?id={user_id}'>{escape(first_name)}</a>!

🎮 <b>Catch, Collect & Trade anime characters!</b>
✨ Battle with friends and build your dream collection!

━━━━━━━━━━━━━━━━━━━━
📊 <b>YOUR STATS</b>
━━━━━━━━━━━━━━━━━━━━
💰 Tokens: <b>{user_tokens}</b>
🃏 Characters: <b>{user_chars}</b>
👥 Referrals: <b>{referred_count}</b>
🌐 Total Players: <b>{total_users:,}</b>

━━━━━━━━━━━━━━━━━━━━
🎁 <b>EARN REWARDS</b>
━━━━━━━━━━━━━━━━━━━━
Invite friends → Get <b>1000 tokens</b> per referral!
Your friend gets <b>500 tokens</b> to start!

👇 <i>Tap buttons below to get started!</i>
"""

        keyboard = [
            [
                InlineKeyboardButton("🎮 Play Now", url=f'https://t.me/{BOT_USERNAME}?startgroup=new'),
                InlineKeyboardButton("📊 Profile", callback_data='profile')
            ],
            [
                InlineKeyboardButton("💰 Earn Tokens", callback_data='earn'),
                InlineKeyboardButton("⚙️ Help", callback_data='help')
            ],
            [
                InlineKeyboardButton("🔗 Share Referral Link", url=referral_link)
            ],
            [
                InlineKeyboardButton("💬 Support", url=f'https://t.me/PICK_X_SUPPORT'),
                InlineKeyboardButton("📢 Updates", url=f'https://t.me/PICK_X_UPDATE')
            ],
            [
                InlineKeyboardButton("👨‍💻 Contact Dev", url=f'https://t.me/ll_Thorfinn_ll'),
                InlineKeyboardButton("💻 Source", url=f'https://www.youtube.com/watch?v=l1hPRV0_cwc')
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
        # Group message - shorter and simpler
        caption = f"""
✨ <b>Hey {escape(first_name)}!</b>

🎮 I'm alive and ready to play!
🌸 Catch anime characters in this group!

💡 <i>Click below to start in private chat</i>
"""
        keyboard = [
            [InlineKeyboardButton("🚀 Start Bot", url=f'https://t.me/{BOT_USERNAME}?start=true')],
            [InlineKeyboardButton("➕ Add to Your Group", url=f'https://t.me/{BOT_USERNAME}?startgroup=new')]
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

# Callback query handler for inline buttons
async def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = await user_collection.find_one({"id": user_id})
    
    if query.data == 'profile':
        user_tokens = user_data.get('tokens', 0)
        user_chars = len(user_data.get('characters', []))
        referred_count = user_data.get('referred_users', 0)
        
        profile_text = f"""
╔═══════════════════╗
   👤 <b>YOUR PROFILE</b>
╚═══════════════════╝

🎭 Name: {escape(user_data.get('first_name', 'Unknown'))}
🆔 ID: <code>{user_id}</code>
💰 Tokens: <b>{user_tokens}</b>
🃏 Characters: <b>{user_chars}</b>
👥 Referrals: <b>{referred_count}</b>

<i>Keep playing to unlock more!</i>
"""
        await query.edit_message_caption(
            caption=profile_text,
            reply_markup=query.message.reply_markup,
            parse_mode='HTML'
        )
    
    elif query.data == 'earn':
        referral_link = f"https://t.me/{BOT_USERNAME}?start=r_{user_id}"
        earn_text = f"""
╔═══════════════════╗
   💰 <b>EARN TOKENS</b>
╚═══════════════════╝

<b>Referral Rewards:</b>
• You get: <b>1000 tokens</b>
• Your friend gets: <b>500 tokens</b>

<b>How to earn:</b>
1️⃣ Share your referral link
2️⃣ Friends join using your link
3️⃣ Get instant rewards!

🔗 <b>Your Link:</b>
<code>{referral_link}</code>

<i>Tap 'Share Referral Link' to invite!</i>
"""
        await query.edit_message_caption(
            caption=earn_text,
            reply_markup=query.message.reply_markup,
            parse_mode='HTML'
        )
    
    elif query.data == 'help':
        help_text = f"""
╔═══════════════════╗
   ⚙️ <b>HELP & COMMANDS</b>
╚═══════════════════╝

<b>Available Commands:</b>
/start - Start the bot
/help - Show this help message
/profile - View your profile
/collection - View your characters
/trade - Trade with others

<b>How to Play:</b>
🎮 Add bot to your group
🌸 Characters appear randomly
⚡ Type /catch to collect them!
💫 Build your collection & trade!

<i>Need more help? Join support group!</i>
"""
        await query.edit_message_caption(
            caption=help_text,
            reply_markup=query.message.reply_markup,
            parse_mode='HTML'
        )

start_handler = CommandHandler('start', start, block=False)
application.add_handler(start_handler)

# Add callback query handler
callback_handler = CallbackQueryHandler(button_callback)
application.add_handler(callback_handler)