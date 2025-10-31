import random
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, user_collection

TIPS = [
    "Use /claim daily to get free gold",
    "Invite friends to earn 1000 gold",
    "Play games to increase your xp",
    "Collect rare slaves to get rich",
    "Use /bal to check your wallet",
    "Trade slaves with others to grow"
]

async def get_balance(user_id):
    try:
        user = await user_collection.find_one({'id': user_id})
        return user.get('balance', 0) if user else 0
    except:
        return 0

def main_keyboard(uid):
    return [
        [InlineKeyboardButton("Games", callback_data=f'hlp_gm_{uid}'),
         InlineKeyboardButton("Economy", callback_data=f'hlp_ec_{uid}')],
        [InlineKeyboardButton("Slaves", callback_data=f'hlp_sl_{uid}'),
         InlineKeyboardButton("Beasts", callback_data=f'hlp_bs_{uid}')],
        [InlineKeyboardButton("Pass", callback_data=f'hlp_ps_{uid}'),
         InlineKeyboardButton("Info", callback_data=f'hlp_if_{uid}')],
        [InlineKeyboardButton("Leaderboard", callback_data=f'hlp_lb_{uid}'),
         InlineKeyboardButton("Rewards", callback_data=f'hlp_rw_{uid}')],
        [InlineKeyboardButton("Guide", callback_data=f'hlp_gd_{uid}'),
         InlineKeyboardButton("Tips", callback_data=f'hlp_tp_{uid}')]
    ]

def main_caption(name, bal):
    return f"""<blockquote>Help Center

Hey {name}

Need help? Choose a category below

Your balance: {bal}

{random.choice(TIPS)}</blockquote>"""

CATEGORIES = {
    'gm': """<blockquote>Game Zone

Test your luck and skills

Gambling Games:
/sbet 10000 heads - coin toss
/roll 10000 even - dice roll
/gamble 10000 l - left or right

Skill Games:
/basket 5000 - basketball
/dart 2000 - dart game

Special:
/riddle - solve and earn
/stour - slave contracts

Earn xp and gold while playing</blockquote>""",
    
    'ec': """<blockquote>Economy

Manage your wealth

Check Balance:
/bal - wallet and bank
/sinv - inventory

Transactions:
/pay @user 1000 - send gold
/claim - daily 2000 gold

Free Rewards:
/daily - daily bonus
/weekly - weekly bonus

Max pay 70b every 20 min</blockquote>""",
    
    'sl': """<blockquote>Slave Collection

Catch and collect anime slaves

Catching:
/grab name - catch slave
Spawns every 100 messages

View Collection:
/harem - your slaves
/slaves - all slaves
/smode - sort by rank

Trading:
/trade - trade with others
/sinfo id - slave details

Build your empire</blockquote>""",
    
    'bs': """<blockquote>Beast System

Summon powerful beasts

Shop:
/beastshop - view beasts
/buybeast - purchase beast

Manage:
/beast - your beasts
/binfo id - beast info
/setbeast - set main beast

Battles:
Use beasts in tournaments
Level up through battles

Collect rare beasts</blockquote>""",
    
    'ps': """<blockquote>Slave Pass

Premium membership

Weekly Rewards:
/claim - claim weekly
/sweekly - bonus after 6 claims
/pbonus - complete tasks

Benefits:
Exclusive slaves
Extra gold rewards
Special events access
Priority support

How to Use:
/pass - view pass status

Upgrade to premium today</blockquote>""",
    
    'if': """<blockquote>Information

Check stats and rankings

Personal Stats:
/sinv - check tokens
/xp - check level
/sinfo - full profile

Leaderboards:
/tops - top players
/topchat - top chats
/topgroups - top groups
/xtop - xp rankings
/gstop - gold rankings

Track your progress</blockquote>""",
    
    'lb': """<blockquote>Leaderboards

Compete with top hunters

Rankings:
/tops - richest hunters
/xtop - highest xp
/gstop - most gold
/tophunters - elite list

Group Stats:
/topchat - active chats
/topgroups - top groups

Climb to the top</blockquote>""",
    
    'rw': """<blockquote>Daily Rewards

Claim free rewards daily

Daily Claims:
/claim - 2000 gold daily
/daily - bonus gold
/hclaim - daily slave

Weekly Bonuses:
/weekly - big weekly reward
/sweekly - pass bonus

Referral Rewards:
Invite friends - 1000 gold
They get - 500 gold

Never miss your rewards</blockquote>""",
    
    'gd': """<blockquote>Quick Start Guide

New to the bot?

1. Get Started:
Type /start
Claim daily with /claim

2. Catch Slaves:
Wait for spawn in chat
Type /slave name

3. Earn Gold:
Play games - /roll
Invite friends
Complete tasks

4. Level Up:
Play games to gain xp
Check with /xp

Have fun and dominate</blockquote>"""
}

async def help_command(update: Update, context: CallbackContext):
    try:
        user = update.effective_user
        bal = await get_balance(user.id)
        caption = main_caption(user.first_name, bal)
        keyboard = main_keyboard(user.id)
        
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo="https://te.legra.ph/file/b6661a11573417d03b4b4.png",
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Help error: {e}")
        await update.message.reply_text("Failed to send help menu")

async def help_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    
    try:
        await query.answer()
        data = query.data.split('_')
        action = data[1]
        uid = int(data[2])
        
        if query.from_user.id != uid:
            await query.answer("This isn't for you", show_alert=True)
            return
        
        if action == 'bk':
            bal = await get_balance(uid)
            caption = main_caption(query.from_user.first_name, bal)
            keyboard = main_keyboard(uid)
        elif action == 'tp':
            caption = f"""<blockquote>Pro Tips

Helpful tips for hunters

Random Tip:
{random.choice(TIPS)}

More Tips:
Claim daily rewards
Play games for xp
Trade rare slaves
Join events
Use pass for bonuses
Invite friends

Tap for new tip</blockquote>"""
            keyboard = [
                [InlineKeyboardButton("New Tip", callback_data=f'hlp_tp_{uid}')],
                [InlineKeyboardButton("Back", callback_data=f'hlp_bk_{uid}')]
            ]
        else:
            caption = CATEGORIES.get(action, "")
            keyboard = [[InlineKeyboardButton("Back", callback_data=f'hlp_bk_{uid}')]]
        
        await query.edit_message_caption(
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    except Exception as e:
        print(f"Callback error: {e}")
        await query.answer("An error occurred", show_alert=True)

application.add_handler(CommandHandler(['help', 'menu', 'panel'], help_command, block=False))
application.add_handler(CallbackQueryHandler(help_callback, pattern=r'^hlp_[a-z]{2}_\d+$', block=False))