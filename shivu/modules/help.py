import os
import random
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from telegram.error import BadRequest, TimedOut, NetworkError
from shivu import application, user_collection

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

# Random tips
TIPS = [
    "💡 ᴜsᴇ /ᴄʟᴀɪᴍ ᴅᴀɪʟʏ ᴛᴏ ɢᴇᴛ ғʀᴇᴇ ɢᴏʟᴅ",
    "💡 ɪɴᴠɪᴛᴇ ғʀɪᴇɴᴅs ᴛᴏ ᴇᴀʀɴ 1000 ɢᴏʟᴅ",
    "💡 ᴘʟᴀʏ ɢᴀᴍᴇs ᴛᴏ ɪɴᴄʀᴇᴀsᴇ ʏᴏᴜʀ xᴘ",
    "💡 ᴄᴏʟʟᴇᴄᴛ ʀᴀʀᴇ sʟᴀᴠᴇs ᴛᴏ ɢᴇᴛ ʀɪᴄʜ",
    "💡 ᴜsᴇ /ʙᴀʟ ᴛᴏ ᴄʜᴇᴄᴋ ʏᴏᴜʀ ᴡᴀʟʟᴇᴛ",
    "💡 ᴛʀᴀᴅᴇ sʟᴀᴠᴇs ᴡɪᴛʜ ᴏᴛʜᴇʀs ᴛᴏ ɢʀᴏᴡ"
]

# Helper function to get user balance safely
async def get_user_balance(user_id):
    try:
        user_data = await user_collection.find_one({'id': user_id})
        return user_data.get('balance', 0) if user_data else 0
    except Exception as e:
        print(f"Error fetching user balance: {e}")
        return 0

# Generate main help keyboard
def get_main_keyboard(user_id):
    return [
        [
            InlineKeyboardButton(f"🎮 {to_small_caps('games')}", callback_data=f'help_games_{user_id}'),
            InlineKeyboardButton(f"💰 {to_small_caps('economy')}", callback_data=f'help_economy_{user_id}')
        ],
        [
            InlineKeyboardButton(f"🎴 {to_small_caps('slaves')}", callback_data=f'help_slaves_{user_id}'),
            InlineKeyboardButton(f"🐉 {to_small_caps('beasts')}", callback_data=f'help_beasts_{user_id}')
        ],
        [
            InlineKeyboardButton(f"💎 {to_small_caps('pass')}", callback_data=f'help_pass_{user_id}'),
            InlineKeyboardButton(f"📊 {to_small_caps('info')}", callback_data=f'help_info_{user_id}')
        ],
        [
            InlineKeyboardButton(f"🏆 {to_small_caps('leaderboard')}", callback_data=f'help_top_{user_id}'),
            InlineKeyboardButton(f"🎁 {to_small_caps('rewards')}", callback_data=f'help_rewards_{user_id}')
        ],
        [
            InlineKeyboardButton(f"📚 {to_small_caps('guide')}", callback_data=f'help_guide_{user_id}'),
            InlineKeyboardButton(f"🪄 {to_small_caps('tips')}", callback_data=f'help_tips_{user_id}')
        ]
    ]

# Generate main help caption
def get_main_caption(first_name, balance):
    return f"""
╔═══════════════════╗
  ✨ <b>{to_small_caps('help center')}</b> ✨
╚═══════════════════╝

👋 {to_small_caps('hey')} <b>{first_name}</b>

🎮 {to_small_caps('need help senpai')}
🌸 {to_small_caps('choose a category below')}

━━━━━━━━━━━━━━━━━━━
🪙 {to_small_caps('your balance')}: <b>{balance}</b>
━━━━━━━━━━━━━━━━━━━

💡 <i>{random.choice(TIPS)}</i>
"""

# Main help command
async def help_command(update: Update, context: CallbackContext):
    try:
        user = update.effective_user
        balance = await get_user_balance(user.id)
        first_name = user.first_name

        caption = get_main_caption(first_name, balance)
        keyboard = get_main_keyboard(user.id)
        reply_markup = InlineKeyboardMarkup(keyboard)
        photo_url = "https://te.legra.ph/file/b6661a11573417d03b4b4.png"

        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=photo_url,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    except BadRequest as e:
        print(f"Bad request error in help_command: {e}")
        await update.message.reply_text("❌ Failed to send help menu. Please try again.")
    except Exception as e:
        print(f"Error in help_command: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again later.")

# Get category caption
def get_category_caption(action):
    captions = {
        'games': f"""
╔═══════════════════╗
  🎮 <b>{to_small_caps('game zone')}</b>
╚═══════════════════╝

⚡ {to_small_caps('test your luck and skills')}

━━━━━━━━━━━━━━━━━━━
🎲 <b>{to_small_caps('gambling games')}</b>
━━━━━━━━━━━━━━━━━━━
• <code>/sbet 10000 heads</code> → {to_small_caps('coin toss')}
• <code>/roll 10000 even</code> → {to_small_caps('dice roll')}
• <code>/gamble 10000 l</code> → {to_small_caps('left or right')}

━━━━━━━━━━━━━━━━━━━
🎯 <b>{to_small_caps('skill games')}</b>
━━━━━━━━━━━━━━━━━━━
• <code>/basket 5000</code> → {to_small_caps('basketball')} 🏀
• <code>/dart 2000</code> → {to_small_caps('dart game')} 🎯

━━━━━━━━━━━━━━━━━━━
🧩 <b>{to_small_caps('special')}</b>
━━━━━━━━━━━━━━━━━━━
• <code>/riddle</code> → {to_small_caps('solve and earn')}
• <code>/stour</code> → {to_small_caps('slave contracts')}

✨ {to_small_caps('earn xp and gold while playing')}
""",
        'economy': f"""
╔═══════════════════╗
  💰 <b>{to_small_caps('economy')}</b>
╚═══════════════════╝

🪙 {to_small_caps('manage your wealth')}

━━━━━━━━━━━━━━━━━━━
📊 <b>{to_small_caps('check balance')}</b>
━━━━━━━━━━━━━━━━━━━
• <code>/bal</code> → {to_small_caps('wallet and bank')}
• <code>/sinv</code> → {to_small_caps('inventory')}

━━━━━━━━━━━━━━━━━━━
💸 <b>{to_small_caps('transactions')}</b>
━━━━━━━━━━━━━━━━━━━
• <code>/pay @user 1000</code> → {to_small_caps('send gold')}
• <code>/claim</code> → {to_small_caps('daily 2000 gold')}

━━━━━━━━━━━━━━━━━━━
🎁 <b>{to_small_caps('free rewards')}</b>
━━━━━━━━━━━━━━━━━━━
• <code>/daily</code> → {to_small_caps('daily bonus')}
• <code>/weekly</code> → {to_small_caps('weekly bonus')}

💡 {to_small_caps('max pay 70b every 20 min')}
""",
        'slaves': f"""
╔═══════════════════╗
  🎴 <b>{to_small_caps('slave collection')}</b>
╚═══════════════════╝

⚡ {to_small_caps('catch and collect anime slaves')}

━━━━━━━━━━━━━━━━━━━
🎯 <b>{to_small_caps('catching')}</b>
━━━━━━━━━━━━━━━━━━━
• <code>/slave name</code> → {to_small_caps('catch slave')}
• {to_small_caps('spawns every 100 messages')}

━━━━━━━━━━━━━━━━━━━
👤 <b>{to_small_caps('view collection')}</b>
━━━━━━━━━━━━━━━━━━━
• <code>/myslave</code> → {to_small_caps('your slaves')}
• <code>/slaves</code> → {to_small_caps('all slaves')}
• <code>/smode</code> → {to_small_caps('sort by rank')}

━━━━━━━━━━━━━━━━━━━
💱 <b>{to_small_caps('trading')}</b>
━━━━━━━━━━━━━━━━━━━
• <code>/trade</code> → {to_small_caps('trade with others')}
• <code>/sinfo id</code> → {to_small_caps('slave details')}

🌟 {to_small_caps('build your empire')}
""",
        'beasts': f"""
╔═══════════════════╗
  🐉 <b>{to_small_caps('beast system')}</b>
╚═══════════════════╝

🔥 {to_small_caps('summon powerful beasts')}

━━━━━━━━━━━━━━━━━━━
🛒 <b>{to_small_caps('shop')}</b>
━━━━━━━━━━━━━━━━━━━
• <code>/beastshop</code> → {to_small_caps('view beasts')}
• <code>/buybeast</code> → {to_small_caps('purchase beast')}

━━━━━━━━━━━━━━━━━━━
👾 <b>{to_small_caps('manage')}</b>
━━━━━━━━━━━━━━━━━━━
• <code>/beast</code> → {to_small_caps('your beasts')}
• <code>/binfo id</code> → {to_small_caps('beast info')}
• <code>/setbeast</code> → {to_small_caps('set main beast')}

━━━━━━━━━━━━━━━━━━━
⚔️ <b>{to_small_caps('battles')}</b>
━━━━━━━━━━━━━━━━━━━
• {to_small_caps('use beasts in tournaments')}
• {to_small_caps('level up through battles')}

✨ {to_small_caps('collect rare beasts')}
""",
        'pass': f"""
╔═══════════════════╗
  💎 <b>{to_small_caps('slave pass')}</b>
╚═══════════════════╝

👑 {to_small_caps('premium membership')}

━━━━━━━━━━━━━━━━━━━
🎁 <b>{to_small_caps('weekly rewards')}</b>
━━━━━━━━━━━━━━━━━━━
• <code>/claim</code> → {to_small_caps('claim weekly')}
• <code>/sweekly</code> → {to_small_caps('bonus after 6 claims')}
• <code>/pbonus</code> → {to_small_caps('complete tasks')}

━━━━━━━━━━━━━━━━━━━
✨ <b>{to_small_caps('benefits')}</b>
━━━━━━━━━━━━━━━━━━━
• {to_small_caps('exclusive slaves')}
• {to_small_caps('extra gold rewards')}
• {to_small_caps('special events access')}
• {to_small_caps('priority support')}

━━━━━━━━━━━━━━━━━━━
📋 <b>{to_small_caps('how to use')}</b>
━━━━━━━━━━━━━━━━━━━
• <code>/pass</code> → {to_small_caps('view pass status')}

🌟 {to_small_caps('upgrade to premium today')}
""",
        'info': f"""
╔═══════════════════╗
  📊 <b>{to_small_caps('information')}</b>
╚═══════════════════╝

📈 {to_small_caps('check stats and rankings')}

━━━━━━━━━━━━━━━━━━━
👤 <b>{to_small_caps('personal stats')}</b>
━━━━━━━━━━━━━━━━━━━
• <code>/sinv</code> → {to_small_caps('check tokens')}
• <code>/xp</code> → {to_small_caps('check level')}
• <code>/sinfo</code> → {to_small_caps('full profile')}

━━━━━━━━━━━━━━━━━━━
🏆 <b>{to_small_caps('leaderboards')}</b>
━━━━━━━━━━━━━━━━━━━
• <code>/tops</code> → {to_small_caps('top players')}
• <code>/topchat</code> → {to_small_caps('top chats')}
• <code>/topgroups</code> → {to_small_caps('top groups')}
• <code>/xtop</code> → {to_small_caps('xp rankings')}
• <code>/gstop</code> → {to_small_caps('gold rankings')}

💡 {to_small_caps('track your progress')}
""",
        'top': f"""
╔═══════════════════╗
  🏆 <b>{to_small_caps('leaderboards')}</b>
╚═══════════════════╝

👑 {to_small_caps('compete with top hunters')}

━━━━━━━━━━━━━━━━━━━
📊 <b>{to_small_caps('rankings')}</b>
━━━━━━━━━━━━━━━━━━━
• <code>/tops</code> → {to_small_caps('richest hunters')}
• <code>/xtop</code> → {to_small_caps('highest xp')}
• <code>/gstop</code> → {to_small_caps('most gold')}
• <code>/tophunters</code> → {to_small_caps('elite list')}

━━━━━━━━━━━━━━━━━━━
👥 <b>{to_small_caps('group stats')}</b>
━━━━━━━━━━━━━━━━━━━
• <code>/topchat</code> → {to_small_caps('active chats')}
• <code>/topgroups</code> → {to_small_caps('top groups')}

✨ {to_small_caps('climb to the top')}
""",
        'rewards': f"""
╔═══════════════════╗
  🎁 <b>{to_small_caps('daily rewards')}</b>
╚═══════════════════╝

💰 {to_small_caps('claim free rewards daily')}

━━━━━━━━━━━━━━━━━━━
⏰ <b>{to_small_caps('daily claims')}</b>
━━━━━━━━━━━━━━━━━━━
• <code>/claim</code> → {to_small_caps('2000 gold daily')}
• <code>/daily</code> → {to_small_caps('bonus gold')}
• <code>/hclaim</code> → {to_small_caps('daily slave')}

━━━━━━━━━━━━━━━━━━━
📅 <b>{to_small_caps('weekly bonuses')}</b>
━━━━━━━━━━━━━━━━━━━
• <code>/weekly</code> → {to_small_caps('big weekly reward')}
• <code>/sweekly</code> → {to_small_caps('pass bonus')}

━━━━━━━━━━━━━━━━━━━
🎊 <b>{to_small_caps('referral rewards')}</b>
━━━━━━━━━━━━━━━━━━━
• {to_small_caps('invite friends')} → <b>1000🪙</b>
• {to_small_caps('they get')} → <b>500🪙</b>

🌟 {to_small_caps('never miss your rewards')}
""",
        'guide': f"""
╔═══════════════════╗
  📚 <b>{to_small_caps('quick start guide')}</b>
╚═══════════════════╝

🎯 {to_small_caps('new to the bot')}

━━━━━━━━━━━━━━━━━━━
1️⃣ <b>{to_small_caps('get started')}</b>
━━━━━━━━━━━━━━━━━━━
• {to_small_caps('type')} <code>/start</code>
• {to_small_caps('claim daily with')} <code>/claim</code>

━━━━━━━━━━━━━━━━━━━
2️⃣ <b>{to_small_caps('catch slaves')}</b>
━━━━━━━━━━━━━━━━━━━
• {to_small_caps('wait for spawn in chat')}
• {to_small_caps('type')} <code>/slave name</code>

━━━━━━━━━━━━━━━━━━━
3️⃣ <b>{to_small_caps('earn gold')}</b>
━━━━━━━━━━━━━━━━━━━
• {to_small_caps('play games')} → <code>/roll</code>
• {to_small_caps('invite friends')}
• {to_small_caps('complete tasks')}

━━━━━━━━━━━━━━━━━━━
4️⃣ <b>{to_small_caps('level up')}</b>
━━━━━━━━━━━━━━━━━━━
• {to_small_caps('play games to gain xp')}
• {to_small_caps('check with')} <code>/xp</code>

✨ {to_small_caps('have fun and dominate')}
"""
    }
    return captions.get(action, "")

# Callback handler
async def help_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    
    try:
        await query.answer()
    except Exception as e:
        print(f"Error answering callback: {e}")
        return

    try:
        data = query.data
        parts = data.split('_')
        action = '_'.join(parts[1:-1])
        expected_user_id = int(parts[-1])

        user_id = query.from_user.id

        if user_id != expected_user_id:
            await query.answer("⚠️ ᴛʜɪs ɪsɴ'ᴛ ғᴏʀ ʏᴏᴜ", show_alert=True)
            return

        # Handle back action
        if action == 'back':
            balance = await get_user_balance(user_id)
            first_name = query.from_user.first_name
            caption = get_main_caption(first_name, balance)
            keyboard = get_main_keyboard(user_id)

            await query.edit_message_caption(
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            return

        # Handle tips action (special case with refresh button)
        if action == 'tips':
            tip = random.choice(TIPS)
            caption = f"""
╔═══════════════════╗
  🪄 <b>{to_small_caps('pro tips')}</b>
╚═══════════════════╝

💡 {to_small_caps('helpful tips for hunters')}

━━━━━━━━━━━━━━━━━━━
<b>{to_small_caps('random tip')}</b>
━━━━━━━━━━━━━━━━━━━
{tip}

━━━━━━━━━━━━━━━━━━━
<b>{to_small_caps('more tips')}</b>
━━━━━━━━━━━━━━━━━━━
• {to_small_caps('claim daily rewards')}
• {to_small_caps('play games for xp')}
• {to_small_caps('trade rare slaves')}
• {to_small_caps('join events')}
• {to_small_caps('use pass for bonuses')}
• {to_small_caps('invite friends')}

✨ {to_small_caps('tap for new tip')}
"""
            keyboard = [
                [InlineKeyboardButton(f"🔄 {to_small_caps('new tip')}", callback_data=f'help_tips_{user_id}')],
                [InlineKeyboardButton(f"⤾ {to_small_caps('back')}", callback_data=f'help_back_{user_id}')]
            ]
            await query.edit_message_caption(
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            return

        # Handle other categories
        caption = get_category_caption(action)
        if caption:
            back_button = [[InlineKeyboardButton(f"⤾ {to_small_caps('back')}", callback_data=f'help_back_{user_id}')]]
            await query.edit_message_caption(
                caption=caption,
                reply_markup=InlineKeyboardMarkup(back_button),
                parse_mode='HTML'
            )
        else:
            await query.answer("❌ Invalid category", show_alert=True)

    except BadRequest as e:
        print(f"Bad request error in callback: {e}")
        await query.answer("❌ Failed to update menu", show_alert=True)
    except TimedOut:
        print("Timeout error in callback")
    except NetworkError as e:
        print(f"Network error in callback: {e}")
    except Exception as e:
        print(f"Unexpected error in callback: {e}")
        await query.answer("❌ An error occurred", show_alert=True)

# Add handlers
help_handler = CommandHandler(['help', 'menu', 'panel'], help_command, block=False)
application.add_handler(help_handler)

callback_pattern = r'help_(games|economy|slaves|beasts|pass|info|top|rewards|guide|tips|back)_\d+$'
help_callback_handler = CallbackQueryHandler(help_callback, pattern=callback_pattern, block=False)
application.add_handler(help_callback_handler)