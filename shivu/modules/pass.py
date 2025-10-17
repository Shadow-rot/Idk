from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from html import escape
import random

from shivu import application, user_collection, collection, user_totals_collection, LOGGER

# Owner ID for approval
OWNER_ID = 5147822244
BOT_USERNAME = "waifukunbot"  # Replace with your actual bot username

# Pass configuration
PASS_CONFIG = {
    'free': {
        'name': 'ғʀᴇᴇ ᴘᴀss',
        'weekly_reward': 1000,
        'streak_bonus': 5000,
        'mythic_characters': 0,
        'grab_multiplier': 1.0,
        'grab_bonus_gold': 0
    },
    'premium': {
        'name': 'ᴘʀᴇᴍɪᴜᴍ ᴘᴀss',
        'weekly_reward': 5000,
        'streak_bonus': 25000,
        'mythic_characters': 3,
        'cost': 50000,
        'grab_multiplier': 1.5,
        'grab_bonus_gold': 5000
    },
    'elite': {
        'name': 'ᴇʟɪᴛᴇ ᴘᴀss',
        'weekly_reward': 15000,
        'streak_bonus': 100000,
        'mythic_characters': 10,
        'cost_inr': 10,
        'upi_id': 'looktouhid@oksbi',
        'activation_bonus': 100000000,
        'grab_multiplier': 2.0,
        'grab_bonus_gold': 10000
    }
}

# Task requirements (removed battles)
MYTHIC_TASKS = {
    'invites': {'required': 5, 'reward': 'ᴍʏᴛʜɪᴄ ᴄʜᴀʀᴀᴄᴛᴇʀ', 'display': 'ɪɴᴠɪᴛᴇs'},
    'weekly_claims': {'required': 4, 'reward': 'ʙᴏɴᴜs ʀᴇᴡᴀʀᴅ', 'display': 'ᴡᴇᴇᴋʟʏ ᴄʟᴀɪᴍs'},
    'grabs': {'required': 50, 'reward': 'ᴄᴏʟʟᴇᴄᴛᴏʀ', 'display': 'ɢʀᴀʙs'}
}

# Small caps function
def to_small_caps(text):
    small_caps_map = {
        'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ',
        'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ',
        's': 's', 't': 'ᴛ', 'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
        'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ғ', 'G': 'ɢ', 'H': 'ʜ', 'I': 'ɪ',
        'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ', 'O': 'ᴏ', 'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ',
        'S': 's', 'T': 'ᴛ', 'U': 'ᴜ', 'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x', 'Y': 'ʏ', 'Z': 'ᴢ',
        '0': '0', '1': '1', '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9'
    }
    return ''.join(small_caps_map.get(c, c) for c in text)


async def get_or_create_pass_data(user_id: int) -> dict:
    """Get or create user pass data"""
    user = await user_collection.find_one({'id': user_id})
    
    if not user:
        user = {
            'id': user_id,
            'characters': [],
            'balance': 0
        }
        await user_collection.insert_one(user)
    
    if 'pass_data' not in user:
        pass_data = {
            'tier': 'free',
            'weekly_claims': 0,
            'last_weekly_claim': None,
            'streak_count': 0,
            'last_streak_claim': None,
            'tasks': {
                'invites': 0,
                'weekly_claims': 0,
                'grabs': 0
            },
            'mythic_unlocked': False,
            'premium_expires': None,
            'elite_expires': None,
            'pending_elite_payment': None,
            'referral_count': 0,
            'referral_earnings': 0
        }
        await user_collection.update_one(
            {'id': user_id},
            {'$set': {'pass_data': pass_data}}
        )
        return pass_data
    
    return user.get('pass_data', {})


async def handle_grab_bonus(user_id: int):
    """Give bonus gold when user grabs a character (call this from your grab handler)"""
    try:
        user = await user_collection.find_one({'id': user_id})
        if not user:
            return
        
        pass_data = user.get('pass_data', {})
        tier = pass_data.get('tier', 'free')
        bonus_gold = PASS_CONFIG[tier]['grab_bonus_gold']
        
        if bonus_gold > 0:
            # Add random bonus between 0 and bonus_gold
            actual_bonus = random.randint(int(bonus_gold * 0.5), bonus_gold)
            
            await user_collection.update_one(
                {'id': user_id},
                {
                    '$inc': {
                        'balance': actual_bonus,
                        'pass_data.tasks.grabs': 1
                    }
                }
            )
            return actual_bonus
        else:
            # Just increment grab count for free tier
            await user_collection.update_one(
                {'id': user_id},
                {'$inc': {'pass_data.tasks.grabs': 1}}
            )
            return 0
            
    except Exception as e:
        LOGGER.error(f"[PASS] Error handling grab bonus: {e}")
        return 0


async def handle_referral(referrer_id: int, new_user_id: int):
    """Handle referral when new user joins (call this from /start with referral)"""
    try:
        # Check if new user already exists
        existing = await user_collection.find_one({'id': new_user_id})
        if existing and existing.get('referred_by'):
            return False  # Already referred
        
        # Mark new user as referred
        await user_collection.update_one(
            {'id': new_user_id},
            {'$set': {'referred_by': referrer_id}},
            upsert=True
        )
        
        # Update referrer's count and earnings
        reward = 1000
        await user_collection.update_one(
            {'id': referrer_id},
            {
                '$inc': {
                    'pass_data.tasks.invites': 1,
                    'pass_data.referral_count': 1,
                    'pass_data.referral_earnings': reward,
                    'balance': reward
                }
            }
        )
        
        LOGGER.info(f"[PASS] User {referrer_id} referred {new_user_id}")
        return True
        
    except Exception as e:
        LOGGER.error(f"[PASS] Error handling referral: {e}")
        return False


async def invite_command(update: Update, context: CallbackContext) -> None:
    """Show invite/referral information"""
    user_id = update.effective_user.id
    
    try:
        pass_data = await get_or_create_pass_data(user_id)
        
        referral_count = pass_data.get('referral_count', 0)
        referral_earnings = pass_data.get('referral_earnings', 0)
        invite_link = f"https://t.me/{BOT_USERNAME}?start=r_{user_id}"
        
        caption = f"""╔═══════════════════╗
  ɪɴᴠɪᴛᴇ ᴘʀᴏɢʀᴀᴍ
╚═══════════════════╝

ʏᴏᴜʀ ʀᴇғᴇʀʀᴀʟs: {referral_count}
ᴇᴀʀɴᴇᴅ: {referral_earnings:,} ɢᴏʟᴅ

━━━━━━━━━━━━━━━━━━━
ʜᴏᴡ ᴛᴏ ɪɴᴠɪᴛᴇ
━━━━━━━━━━━━━━━━━━━
• ᴄᴏᴘʏ ʟɪɴᴋ ʙᴇʟᴏᴡ
• sʜᴀʀᴇ ᴡɪᴛʜ ғʀɪᴇɴᴅs
• ᴛʜᴇʏ ᴄʟɪᴄᴋ ᴀɴᴅ sᴛᴀʀᴛ ʙᴏᴛ
• ɪɴsᴛᴀɴᴛ ʀᴇᴡᴀʀᴅs

━━━━━━━━━━━━━━━━━━━
ʏᴏᴜʀ ɪɴᴠɪᴛᴇ ʟɪɴᴋ
━━━━━━━━━━━━━━━━━━━
<code>{invite_link}</code>

ᴛᴀᴘ ᴛᴏ ᴄᴏᴘʏ ʟɪɴᴋ

━━━━━━━━━━━━━━━━━━━
ʀᴇᴡᴀʀᴅs
━━━━━━━━━━━━━━━━━━━
• 1,000 ɢᴏʟᴅ ᴘᴇʀ ʀᴇғᴇʀʀᴀʟ
• ᴄᴏᴜɴᴛs ᴛᴏᴡᴀʀᴅs ᴘᴀss ᴛᴀsᴋs
• ᴜɴʟᴏᴄᴋ ᴍʏᴛʜɪᴄ ᴀᴛ 5 ɪɴᴠɪᴛᴇs
"""
        
        keyboard = [[
            InlineKeyboardButton("sʜᴀʀᴇ ʟɪɴᴋ", url=f"https://t.me/share/url?url={invite_link}")
        ]]
        
        await update.message.reply_photo(
            photo="https://files.catbox.moe/z8fhwx.jpg",
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
        LOGGER.info(f"[PASS] Invite info shown for user {user_id}")
        
    except Exception as e:
        LOGGER.error(f"[PASS INVITE ERROR] {e}")
        await update.message.reply_text(to_small_caps('error loading invite data'))


async def pass_command(update: Update, context: CallbackContext) -> None:
    """Show pass status and information"""
    user_id = update.effective_user.id
    
    try:
        pass_data = await get_or_create_pass_data(user_id)
        user = await user_collection.find_one({'id': user_id})
        
        tier = pass_data.get('tier', 'free')
        tier_name = PASS_CONFIG[tier]['name']
        weekly_claims = pass_data.get('weekly_claims', 0)
        streak_count = pass_data.get('streak_count', 0)
        tasks = pass_data.get('tasks', {})
        mythic_unlocked = pass_data.get('mythic_unlocked', False)
        balance = user.get('balance', 0)
        
        total_tasks = len(MYTHIC_TASKS)
        completed_tasks = sum(1 for task_key, task_info in MYTHIC_TASKS.items() 
                             if tasks.get(task_key, 0) >= task_info['required'])
        
        tier_status = to_small_caps("free")
        if tier == 'elite':
            elite_expires = pass_data.get('elite_expires')
            if elite_expires and isinstance(elite_expires, datetime):
                if elite_expires > datetime.utcnow():
                    days_left = (elite_expires - datetime.utcnow()).days
                    tier_status = to_small_caps("elite") + f" ({days_left} " + to_small_caps("days") + ")"
                else:
                    tier_status = to_small_caps("expired")
        elif tier == 'premium':
            premium_expires = pass_data.get('premium_expires')
            if premium_expires and isinstance(premium_expires, datetime):
                if premium_expires > datetime.utcnow():
                    days_left = (premium_expires - datetime.utcnow()).days
                    tier_status = to_small_caps("premium") + f" ({days_left} " + to_small_caps("days") + ")"
                else:
                    tier_status = to_small_caps("expired")
        
        mythic_status = to_small_caps("unlocked") if mythic_unlocked else to_small_caps("locked")
        grab_multiplier = PASS_CONFIG[tier]['grab_multiplier']
        grab_bonus = PASS_CONFIG[tier]['grab_bonus_gold']
        
        caption = f"""╔═══════════════════╗
  {tier_name}
╚═══════════════════╝

{to_small_caps('user')}: {escape(update.effective_user.first_name)}
{to_small_caps('id')}: <code>{user_id}</code>
{to_small_caps('balance')}: <code>{balance:,}</code>

━━━━━━━━━━━━━━━━━━━
{to_small_caps('progress')}
━━━━━━━━━━━━━━━━━━━
{to_small_caps('weekly claims')}: {weekly_claims}/6
{to_small_caps('streak')}: {streak_count} {to_small_caps('weeks')}
{to_small_caps('tasks completed')}: {completed_tasks}/{total_tasks}
{to_small_caps('mythic unlock')}: {mythic_status}

━━━━━━━━━━━━━━━━━━━
{to_small_caps('multipliers')}
━━━━━━━━━━━━━━━━━━━
{to_small_caps('grab bonus')}: {grab_multiplier}x
{to_small_caps('grab gold')}: {grab_bonus:,} {to_small_caps('per grab')}

━━━━━━━━━━━━━━━━━━━
{to_small_caps('rewards')}
━━━━━━━━━━━━━━━━━━━
{to_small_caps('weekly')}: {PASS_CONFIG[tier]['weekly_reward']:,}
{to_small_caps('streak bonus')}: {PASS_CONFIG[tier]['streak_bonus']:,}
{to_small_caps('tier status')}: {tier_status}

━━━━━━━━━━━━━━━━━━━
{to_small_caps('commands')}
━━━━━━━━━━━━━━━━━━━
/pclaim {to_small_caps('weekly reward')}
/sweekly {to_small_caps('streak bonus')}
/tasks {to_small_caps('view tasks')}
/upgrade {to_small_caps('upgrade pass')}
/invite {to_small_caps('referral program')}
"""
        
        keyboard = [
            [
                InlineKeyboardButton(to_small_caps("claim"), callback_data=f"pass_claim_{user_id}"),
                InlineKeyboardButton(to_small_caps("tasks"), callback_data=f"pass_tasks_{user_id}")
            ],
            [
                InlineKeyboardButton(to_small_caps("upgrade"), callback_data=f"pass_upgrade_{user_id}"),
                InlineKeyboardButton(to_small_caps("invite"), callback_data=f"pass_invite_{user_id}")
            ],
            [
                InlineKeyboardButton(to_small_caps("help"), callback_data=f"pass_help_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_photo(
            photo="https://files.catbox.moe/z8fhwx.jpg",
            caption=caption,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        LOGGER.info(f"[PASS] Status shown for user {user_id}")
        
    except Exception as e:
        LOGGER.error(f"[PASS ERROR] {e}")
        await update.message.reply_text(to_small_caps('error loading pass data'))


async def pclaim_command(update: Update, context: CallbackContext) -> None:
    """Claim weekly reward"""
    user_id = update.effective_user.id
    
    try:
        pass_data = await get_or_create_pass_data(user_id)
        user = await user_collection.find_one({'id': user_id})
        
        last_claim = pass_data.get('last_weekly_claim')
        if last_claim and isinstance(last_claim, datetime):
            time_since = datetime.utcnow() - last_claim
            if time_since < timedelta(days=7):
                remaining = timedelta(days=7) - time_since
                hours = remaining.seconds // 3600
                minutes = (remaining.seconds % 3600) // 60
                
                msg = (
                    f"{to_small_caps('next claim in')}\n\n"
                    f"{remaining.days} {to_small_caps('days')} {hours} {to_small_caps('hours')} {minutes} {to_small_caps('minutes')}"
                )
                
                if hasattr(update, 'callback_query') and update.callback_query:
                    await update.callback_query.answer(msg, show_alert=True)
                else:
                    await update.message.reply_text(msg)
                return
        
        tier = pass_data.get('tier', 'free')
        reward = PASS_CONFIG[tier]['weekly_reward']
        mythic_chars_count = PASS_CONFIG[tier]['mythic_characters']
        
        new_claims = pass_data.get('weekly_claims', 0) + 1
        await user_collection.update_one(
            {'id': user_id},
            {
                '$set': {
                    'pass_data.last_weekly_claim': datetime.utcnow(),
                    'pass_data.weekly_claims': new_claims,
                    'pass_data.tasks.weekly_claims': new_claims
                },
                '$inc': {'balance': reward}
            }
        )
        
        last_streak = pass_data.get('last_streak_claim')
        if last_streak and isinstance(last_streak, datetime):
            days_since = (datetime.utcnow() - last_streak).days
            if 6 <= days_since <= 8:
                await user_collection.update_one(
                    {'id': user_id},
                    {
                        '$inc': {'pass_data.streak_count': 1},
                        '$set': {'pass_data.last_streak_claim': datetime.utcnow()}
                    }
                )
            elif days_since > 8:
                await user_collection.update_one(
                    {'id': user_id},
                    {'$set': {'pass_data.streak_count': 0}}
                )
        else:
            await user_collection.update_one(
                {'id': user_id},
                {
                    '$set': {
                        'pass_data.streak_count': 1,
                        'pass_data.last_streak_claim': datetime.utcnow()
                    }
                }
            )
        
        premium_msg = ""
        if mythic_chars_count > 0:
            mythic_chars = await collection.find({'rarity': '🏵 Mythic'}).limit(mythic_chars_count).to_list(length=mythic_chars_count)
            
            if mythic_chars:
                await user_collection.update_one(
                    {'id': user_id},
                    {'$push': {'characters': {'$each': mythic_chars}}}
                )
                
                await user_totals_collection.update_one(
                    {'id': user_id},
                    {'$inc': {'count': len(mythic_chars)}},
                    upsert=True
                )
                
                premium_msg = f"\n\n{to_small_caps('bonus')}: {len(mythic_chars)} {to_small_caps('mythic characters added')}"
        
        success_text = (
            f"{to_small_caps('claimed successfully')}\n\n"
            f"{to_small_caps('reward')}: <code>{reward:,}</code>\n"
            f"{to_small_caps('total claims')}: {new_claims}/6{premium_msg}"
        )
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.answer(to_small_caps("claimed successfully"), show_alert=False)
            await update.callback_query.message.reply_text(success_text, parse_mode='HTML')
        else:
            await update.message.reply_text(success_text, parse_mode='HTML')
        
        LOGGER.info(f"[PASS] User {user_id} claimed weekly reward")
        
    except Exception as e:
        LOGGER.error(f"[PASS CLAIM ERROR] {e}")
        error_msg = to_small_caps('error processing claim')
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.answer(error_msg, show_alert=True)
        else:
            await update.message.reply_text(error_msg)


async def sweekly_command(update: Update, context: CallbackContext) -> None:
    """Claim 6-week streak bonus with real mythic character"""
    user_id = update.effective_user.id
    
    try:
        pass_data = await get_or_create_pass_data(user_id)
        
        weekly_claims = pass_data.get('weekly_claims', 0)
        if weekly_claims < 6:
            msg = (
                f"{to_small_caps('you need 6 weekly claims')}\n"
                f"{to_small_caps('current')}: {weekly_claims}/6"
            )
            await update.message.reply_text(msg)
            return
        
        tier = pass_data.get('tier', 'free')
        bonus = PASS_CONFIG[tier]['streak_bonus']
        
        mythic_char = await collection.find_one({'rarity': '🏵 Mythic'})
        
        update_data = {
            '$inc': {'balance': bonus},
            '$set': {'pass_data.weekly_claims': 0}
        }
        
        if mythic_char:
            update_data['$push'] = {'characters': mythic_char}
        
        await user_collection.update_one(
            {'id': user_id},
            update_data
        )
        
        if mythic_char:
            await user_totals_collection.update_one(
                {'id': user_id},
                {'$inc': {'count': 1}},
                upsert=True
            )
        
        char_msg = ""
        if mythic_char:
            char_name = mythic_char.get('name', 'unknown')
            char_anime = mythic_char.get('anime', 'unknown')
            char_msg = f"\n\n{to_small_caps('bonus character')}:\n{to_small_caps('name')}: {char_name}\n{to_small_caps('anime')}: {char_anime}"
        
        await update.message.reply_text(
            f"{to_small_caps('streak bonus claimed')}\n\n"
            f"{to_small_caps('bonus gold')}: <code>{bonus:,}</code>\n"
            f"{to_small_caps('weekly claims reset to')} 0{char_msg}",
            parse_mode='HTML'
        )
        
        LOGGER.info(f"[PASS] User {user_id} claimed streak bonus")
        
    except Exception as e:
        LOGGER.error(f"[PASS SWEEKLY ERROR] {e}")
        await update.message.reply_text(to_small_caps('error processing bonus'))


async def tasks_command(update: Update, context: CallbackContext) -> None:
    """Show task progress"""
    user_id = update.effective_user.id
    
    try:
        pass_data = await get_or_create_pass_data(user_id)
        tasks = pass_data.get('tasks', {})
        mythic_unlocked = pass_data.get('mythic_unlocked', False)
        
        task_list = []
        all_completed = True
        for task_key, task_info in MYTHIC_TASKS.items():
            current = tasks.get(task_key, 0)
            required = task_info['required']
            reward = task_info['reward']
            display = task_info['display']
            progress = min(100, int((current / required) * 100))
            
            if current >= required:
                status = "✅"
            else:
                status = "⏳"
                all_completed = False
            
            bar_filled = '█' * (progress // 10)
            bar_empty = '░' * (10 - progress // 10)
            
            task_list.append(
                f"{status} <b>{display}</b>\n"
                f"   {current}/{required} | {bar_filled}{bar_empty} {progress}%\n"
                f"   {to_small_caps('reward')}: {reward}"
            )
        
        if all_completed and not mythic_unlocked:
            mythic_char = await collection.find_one({'rarity': '🏵 Mythic'})
            if mythic_char:
                await user_collection.update_one(
                    {'id': user_id},
                    {
                        '$push': {'characters': mythic_char},
                        '$set': {'pass_data.mythic_unlocked': True}
                    }
                )
                
                await user_totals_collection.update_one(
                    {'id': user_id},
                    {'$inc': {'count': 1}},
                    upsert=True
                )
                
                mythic_unlocked = True
        
        mythic_status = '✅ ' + to_small_caps('unlocked') if mythic_unlocked else '🔒 ' + to_small_caps('locked')
        
        caption = f"""╔═══════════════════╗
  {to_small_caps('mythic tasks')}
╚═══════════════════╝

{chr(10).join(task_list)}

━━━━━━━━━━━━━━━━━━━
{to_small_caps('mythic unlock')}: {mythic_status}

{to_small_caps('complete all tasks to unlock mythic')}
"""
        
        keyboard = [[
            InlineKeyboardButton(to_small_caps("refresh"), callback_data=f"pass_tasks_{user_id}"),
            InlineKeyboardButton(to_small_caps("back"), callback_data=f"pass_back_{user_id}")
        ]]
        
        if hasattr(update, 'callback_query') and update.callback_query:
            try:
                media = InputMediaPhoto(
                    media="https://files.catbox.moe/z8fhwx.jpg",
                    caption=caption,
                    parse_mode='HTML'
                )
                await update.callback_query.edit_message_media(
                    media=media,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except:
                await update.callback_query.edit_message_caption(
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
        else:
            await update.message.reply_photo(
                photo="https://files.catbox.moe/z8fhwx.jpg",
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        
        LOGGER.info(f"[PASS] Tasks shown for user {user_id}")
        
    except Exception as e:
        LOGGER.error(f"[PASS TASKS ERROR] {e}")
        error_msg = to_small_caps('error loading tasks')
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.answer(error_msg, show_alert=True)
        else:
            await update.message.reply_text(error_msg)


async def upgrade_command(update: Update, context: CallbackContext) -> None:
    """Show upgrade options"""
    user_id = update.effective_user.id
    
    try:
        pass_data = await get_or_create_pass_data(user_id)
        user = await user_collection.find_one({'id': user_id})
        balance = user.get('balance', 0)
        
        tier = pass_data.get('tier', 'free')
        
        caption = f"""╔═══════════════════╗
  {to_small_caps('upgrade pass')}
╚═══════════════════╝

{to_small_caps('your balance')}: <code>{balance:,}</code>
{to_small_caps('current tier')}: {PASS_CONFIG[tier]['name']}

━━━━━━━━━━━━━━━━━━━
💎 {to_small_caps('premium pass')}
━━━━━━━━━━━━━━━━━━━
{to_small_caps('cost')}: <code>50,000</code> {to_small_caps('gold')}
{to_small_caps('duration')}: 30 {to_small_caps('days')}

<b>{to_small_caps('benefits')}:</b>
• {to_small_caps('weekly')}: 5,000 {to_small_caps('gold')}
• {to_small_caps('streak')}: 25,000 {to_small_caps('gold')}
• {to_small_caps('mythic chars')}: 3 {to_small_caps('per claim')}
• {to_small_caps('grab bonus')}: 1.5x
• {to_small_caps('grab gold')}: 5,000 {to_small_caps('per grab')}

━━━━━━━━━━━━━━━━━━━
⭐ {to_small_caps('elite pass')}
━━━━━━━━━━━━━━━━━━━
{to_small_caps('cost')}: 10 {to_small_caps('inr')}
{to_small_caps('payment')}: {PASS_CONFIG['elite']['upi_id']}
{to_small_caps('duration')}: 30 {to_small_caps('days')}

<b>{to_small_caps('benefits')}:</b>
• {to_small_caps('instant')}: 100,000,000 {to_small_caps('gold')}
• {to_small_caps('instant')}: 10 {to_small_caps('mythic characters')}
• {to_small_caps('weekly')}: 15,000 {to_small_caps('gold')}
• {to_small_caps('streak')}: 100,000 {to_small_caps('gold')}
• {to_small_caps('mythic chars')}: 10 {to_small_caps('per claim')}
• {to_small_caps('grab bonus')}: 2x
• {to_small_caps('grab gold')}: 10,000 {to_small_caps('per grab')}
"""
        
        keyboard = [
            [InlineKeyboardButton(to_small_caps("buy premium"), callback_data=f"pass_buy_premium_{user_id}")],
            [InlineKeyboardButton(to_small_caps("buy elite"), callback_data=f"pass_buy_elite_{user_id}")],
            [InlineKeyboardButton(to_small_caps("back"), callback_data=f"pass_back_{user_id}")]
        ]
        
        if hasattr(update, 'callback_query') and update.callback_query:
            try:
                media = InputMediaPhoto(
                    media="https://files.catbox.moe/z8fhwx.jpg",
                    caption=caption,
                    parse_mode='HTML'
                )
                await update.callback_query.edit_message_media(
                    media=media,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except:
                await update.callback_query.edit_message_caption(
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
        else:
            await update.message.reply_photo(
                photo="https://files.catbox.moe/z8fhwx.jpg",
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        
        LOGGER.info(f"[PASS] Upgrade options shown for user {user_id}")
        
    except Exception as e:
        LOGGER.error(f"[PASS UPGRADE ERROR] {e}")
        error_msg = to_small_caps('error loading upgrade')
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.answer(error_msg, show_alert=True)
        else:
            await update.message.reply_text(error_msg)


async def approve_elite_command(update: Update, context: CallbackContext) -> None:
    """Owner command to approve elite pass payment"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text(to_small_caps('unauthorized'))
        return
    
    try:
        if len(context.args) < 1:
            await update.message.reply_text(
                f"{to_small_caps('usage')}: /approveelite <{to_small_caps('user id')}>"
            )
            return
        
        target_user_id = int(context.args[0])
        
        target_user = await user_collection.find_one({'id': target_user_id})
        if not target_user:
            await update.message.reply_text(to_small_caps('user not found'))
            return
        
        pass_data = target_user.get('pass_data', {})
        pending = pass_data.get('pending_elite_payment')
        
        if not pending:
            await update.message.reply_text(to_small_caps('no pending payment for this user'))
            return
        
        expires = datetime.utcnow() + timedelta(days=30)
        activation_bonus = PASS_CONFIG['elite']['activation_bonus']
        
        mythic_chars = await collection.find({'rarity': '🏵 Mythic'}).limit(10).to_list(length=10)
        
        await user_collection.update_one(
            {'id': target_user_id},
            {
                '$set': {
                    'pass_data.tier': 'elite',
                    'pass_data.elite_expires': expires,
                    'pass_data.pending_elite_payment': None
                },
                '$inc': {'balance': activation_bonus},
                '$push': {'characters': {'$each': mythic_chars}}
            }
        )
        
        await user_totals_collection.update_one(
            {'id': target_user_id},
            {'$inc': {'count': len(mythic_chars)}},
            upsert=True
        )
        
        await update.message.reply_text(
            f"✅ {to_small_caps('elite pass activated')}\n\n"
            f"{to_small_caps('user id')}: <code>{target_user_id}</code>\n"
            f"{to_small_caps('gold bonus')}: <code>{activation_bonus:,}</code>\n"
            f"{to_small_caps('mythic characters')}: {len(mythic_chars)}\n"
            f"{to_small_caps('expires')}: {expires.strftime('%Y-%m-%d')}",
            parse_mode='HTML'
        )
        
        try:
            char_names = '\n'.join([f"• {c.get('name', 'unknown')}" for c in mythic_chars[:5]])
            if len(mythic_chars) > 5:
                char_names += f"\n{to_small_caps('and')} {len(mythic_chars) - 5} {to_small_caps('more')}"
            
            await context.bot.send_message(
                chat_id=target_user_id,
                text=(
                    f"╔═══════════════════╗\n"
                    f"  ⭐ {to_small_caps('elite pass activated')}\n"
                    f"╚═══════════════════╝\n\n"
                    f"🎉 {to_small_caps('congratulations')}\n\n"
                    f"<b>{to_small_caps('received')}:</b>\n"
                    f"💰 {to_small_caps('gold')}: <code>{activation_bonus:,}</code>\n"
                    f"🏵 {to_small_caps('mythic characters')}: {len(mythic_chars)}\n\n"
                    f"<b>{to_small_caps('characters')}:</b>\n{char_names}\n\n"
                    f"⏰ {to_small_caps('expires')}: {expires.strftime('%Y-%m-%d')}\n\n"
                    f"{to_small_caps('enjoy your elite benefits')}"
                ),
                parse_mode='HTML'
            )
        except Exception as e:
            LOGGER.error(f"[PASS] Could not notify user {target_user_id}: {e}")
        
        LOGGER.info(f"[PASS] Elite pass approved for user {target_user_id}")
        
    except ValueError:
        await update.message.reply_text(to_small_caps('invalid user id'))
    except Exception as e:
        LOGGER.error(f"[PASS APPROVE ERROR] {e}")
        await update.message.reply_text(to_small_caps('error processing approval'))


async def pass_callback(update: Update, context: CallbackContext) -> None:
    """Handle pass button callbacks"""
    query = update.callback_query
    
    try:
        data = query.data
        if not data.startswith('pass_'):
            return
        
        parts = data.split('_')
        action = parts[1]
        
        if len(parts) >= 3:
            try:
                user_id = int(parts[-1])
            except:
                user_id = query.from_user.id
        else:
            user_id = query.from_user.id
        
        if query.from_user.id != user_id:
            await query.answer(to_small_caps("not your request"), show_alert=True)
            return
        
        await query.answer()
        
        if action == 'claim':
            update.callback_query = query
            await pclaim_command(update, context)
            
        elif action == 'tasks':
            update.callback_query = query
            await tasks_command(update, context)
            
        elif action == 'upgrade':
            update.callback_query = query
            await upgrade_command(update, context)
            
        elif action == 'invite':
            pass_data = await get_or_create_pass_data(user_id)
            referral_count = pass_data.get('referral_count', 0)
            referral_earnings = pass_data.get('referral_earnings', 0)
            invite_link = f"https://t.me/{BOT_USERNAME}?start=r_{user_id}"
            
            caption = f"""╔═══════════════════╗
  ɪɴᴠɪᴛᴇ ᴘʀᴏɢʀᴀᴍ
╚═══════════════════╝

ʏᴏᴜʀ ʀᴇғᴇʀʀᴀʟs: {referral_count}
ᴇᴀʀɴᴇᴅ: {referral_earnings:,} ɢᴏʟᴅ

━━━━━━━━━━━━━━━━━━━
ʜᴏᴡ ᴛᴏ ɪɴᴠɪᴛᴇ
━━━━━━━━━━━━━━━━━━━
• ᴄᴏᴘʏ ʟɪɴᴋ ʙᴇʟᴏᴡ
• sʜᴀʀᴇ ᴡɪᴛʜ ғʀɪᴇɴᴅs
• ᴛʜᴇʏ ᴄʟɪᴄᴋ ᴀɴᴅ sᴛᴀʀᴛ ʙᴏᴛ
• ɪɴsᴛᴀɴᴛ ʀᴇᴡᴀʀᴅs

━━━━━━━━━━━━━━━━━━━
ʏᴏᴜʀ ɪɴᴠɪᴛᴇ ʟɪɴᴋ
━━━━━━━━━━━━━━━━━━━
<code>{invite_link}</code>

ᴛᴀᴘ ᴛᴏ ᴄᴏᴘʏ ʟɪɴᴋ

━━━━━━━━━━━━━━━━━━━
ʀᴇᴡᴀʀᴅs
━━━━━━━━━━━━━━━━━━━
• 1,000 ɢᴏʟᴅ ᴘᴇʀ ʀᴇғᴇʀʀᴀʟ
• ᴄᴏᴜɴᴛs ᴛᴏᴡᴀʀᴅs ᴘᴀss ᴛᴀsᴋs
• ᴜɴʟᴏᴄᴋ ᴍʏᴛʜɪᴄ ᴀᴛ 5 ɪɴᴠɪᴛᴇs
"""
            
            keyboard = [
                [InlineKeyboardButton("sʜᴀʀᴇ ʟɪɴᴋ", url=f"https://t.me/share/url?url={invite_link}")],
                [InlineKeyboardButton(to_small_caps("back"), callback_data=f"pass_back_{user_id}")]
            ]
            
            try:
                media = InputMediaPhoto(
                    media="https://files.catbox.moe/z8fhwx.jpg",
                    caption=caption,
                    parse_mode='HTML'
                )
                await query.edit_message_media(
                    media=media,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except:
                await query.edit_message_caption(
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
            
        elif action == 'help':
            help_text = (
                f"╔═══════════════════╗\n"
                f"  {to_small_caps('pass help')}\n"
                f"╚═══════════════════╝\n\n"
                f"<b>{to_small_caps('commands')}:</b>\n"
                f"/pass - {to_small_caps('view pass status')}\n"
                f"/pclaim - {to_small_caps('claim weekly reward')}\n"
                f"/sweekly - {to_small_caps('claim streak bonus')}\n"
                f"/tasks - {to_small_caps('view task progress')}\n"
                f"/upgrade - {to_small_caps('upgrade options')}\n"
                f"/invite - {to_small_caps('referral program')}\n\n"
                f"<b>{to_small_caps('how to unlock mythic')}:</b>\n"
                f"1. {to_small_caps('invite 5 people')}\n"
                f"2. {to_small_caps('claim 4 weekly rewards')}\n"
                f"3. {to_small_caps('grab 50 characters')}\n\n"
                f"<b>{to_small_caps('pass tiers')}:</b>\n"
                f"• {to_small_caps('free')}: {to_small_caps('basic rewards')}\n"
                f"• {to_small_caps('premium')}: 50k {to_small_caps('gold')}\n"
                f"• {to_small_caps('elite')}: 10 {to_small_caps('inr')}\n\n"
                f"<b>{to_small_caps('grab bonuses')}:</b>\n"
                f"• {to_small_caps('premium')}: 5k {to_small_caps('gold per grab')}\n"
                f"• {to_small_caps('elite')}: 10k {to_small_caps('gold per grab')}"
            )
            
            keyboard = [[
                InlineKeyboardButton(to_small_caps("back"), callback_data=f"pass_back_{user_id}")
            ]]
            
            try:
                media = InputMediaPhoto(
                    media="https://files.catbox.moe/z8fhwx.jpg",
                    caption=help_text,
                    parse_mode='HTML'
                )
                await query.edit_message_media(
                    media=media,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except:
                await query.edit_message_caption(
                    caption=help_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
            
        elif action == 'back':
            pass_data = await get_or_create_pass_data(user_id)
            user = await user_collection.find_one({'id': user_id})
            
            tier = pass_data.get('tier', 'free')
            tier_name = PASS_CONFIG[tier]['name']
            weekly_claims = pass_data.get('weekly_claims', 0)
            streak_count = pass_data.get('streak_count', 0)
            tasks = pass_data.get('tasks', {})
            mythic_unlocked = pass_data.get('mythic_unlocked', False)
            balance = user.get('balance', 0)
            
            total_tasks = len(MYTHIC_TASKS)
            completed_tasks = sum(1 for task_key, task_info in MYTHIC_TASKS.items() 
                                 if tasks.get(task_key, 0) >= task_info['required'])
            
            tier_status = to_small_caps("free")
            if tier == 'elite':
                elite_expires = pass_data.get('elite_expires')
                if elite_expires and isinstance(elite_expires, datetime):
                    if elite_expires > datetime.utcnow():
                        days_left = (elite_expires - datetime.utcnow()).days
                        tier_status = to_small_caps("elite") + f" ({days_left} " + to_small_caps("days") + ")"
                    else:
                        tier_status = to_small_caps("expired")
            elif tier == 'premium':
                premium_expires = pass_data.get('premium_expires')
                if premium_expires and isinstance(premium_expires, datetime):
                    if premium_expires > datetime.utcnow():
                        days_left = (premium_expires - datetime.utcnow()).days
                        tier_status = to_small_caps("premium") + f" ({days_left} " + to_small_caps("days") + ")"
                    else:
                        tier_status = to_small_caps("expired")
            
            mythic_status = to_small_caps("unlocked") if mythic_unlocked else to_small_caps("locked")
            grab_multiplier = PASS_CONFIG[tier]['grab_multiplier']
            grab_bonus = PASS_CONFIG[tier]['grab_bonus_gold']
            
            caption = f"""╔═══════════════════╗
  {tier_name}
╚═══════════════════╝

{to_small_caps('user')}: {escape(query.from_user.first_name)}
{to_small_caps('id')}: <code>{user_id}</code>
{to_small_caps('balance')}: <code>{balance:,}</code>

━━━━━━━━━━━━━━━━━━━
{to_small_caps('progress')}
━━━━━━━━━━━━━━━━━━━
{to_small_caps('weekly claims')}: {weekly_claims}/6
{to_small_caps('streak')}: {streak_count} {to_small_caps('weeks')}
{to_small_caps('tasks completed')}: {completed_tasks}/{total_tasks}
{to_small_caps('mythic unlock')}: {mythic_status}

━━━━━━━━━━━━━━━━━━━
{to_small_caps('multipliers')}
━━━━━━━━━━━━━━━━━━━
{to_small_caps('grab bonus')}: {grab_multiplier}x
{to_small_caps('grab gold')}: {grab_bonus:,} {to_small_caps('per grab')}

━━━━━━━━━━━━━━━━━━━
{to_small_caps('rewards')}
━━━━━━━━━━━━━━━━━━━
{to_small_caps('weekly')}: {PASS_CONFIG[tier]['weekly_reward']:,}
{to_small_caps('streak bonus')}: {PASS_CONFIG[tier]['streak_bonus']:,}
{to_small_caps('tier status')}: {tier_status}

━━━━━━━━━━━━━━━━━━━
{to_small_caps('commands')}
━━━━━━━━━━━━━━━━━━━
/pclaim {to_small_caps('weekly reward')}
/sweekly {to_small_caps('streak bonus')}
/tasks {to_small_caps('view tasks')}
/upgrade {to_small_caps('upgrade pass')}
/invite {to_small_caps('referral program')}
"""
            
            keyboard = [
                [
                    InlineKeyboardButton(to_small_caps("claim"), callback_data=f"pass_claim_{user_id}"),
                    InlineKeyboardButton(to_small_caps("tasks"), callback_data=f"pass_tasks_{user_id}")
                ],
                [
                    InlineKeyboardButton(to_small_caps("upgrade"), callback_data=f"pass_upgrade_{user_id}"),
                    InlineKeyboardButton(to_small_caps("invite"), callback_data=f"pass_invite_{user_id}")
                ],
                [
                    InlineKeyboardButton(to_small_caps("help"), callback_data=f"pass_help_{user_id}")
                ]
            ]
            
            try:
                media = InputMediaPhoto(
                    media="https://files.catbox.moe/z8fhwx.jpg",
                    caption=caption,
                    parse_mode='HTML'
                )
                await query.edit_message_media(
                    media=media,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except:
                await query.edit_message_caption(
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
            
        elif action == 'buy' and len(parts) >= 3:
            tier_type = parts[2]
            
            if tier_type == 'premium':
                user = await user_collection.find_one({'id': user_id})
                cost = PASS_CONFIG['premium']['cost']
                balance = user.get('balance', 0)
                
                if balance < cost:
                    await query.answer(
                        f"{to_small_caps('insufficient balance')}\n{to_small_caps('need')}: {cost - balance:,}",
                        show_alert=True
                    )
                    return
                
                caption = (
                    f"╔═══════════════════╗\n"
                    f"  {to_small_caps('confirm premium')}\n"
                    f"╚═══════════════════╝\n\n"
                    f"{to_small_caps('cost')}: <code>{cost:,}</code>\n"
                    f"{to_small_caps('balance')}: <code>{balance:,}</code>\n\n"
                    f"<b>{to_small_caps('benefits')}:</b>\n"
                    f"• 5,000 {to_small_caps('weekly')}\n"
                    f"• 25,000 {to_small_caps('streak')}\n"
                    f"• 3 {to_small_caps('mythic per claim')}\n"
                    f"• 1.5x {to_small_caps('grab bonus')}\n"
                    f"• 5,000 {to_small_caps('gold per grab')}"
                )
                
                keyboard = [
                    [
                        InlineKeyboardButton(to_small_caps("confirm"), callback_data=f"pass_confirm_premium_{user_id}"),
                        InlineKeyboardButton(to_small_caps("cancel"), callback_data=f"pass_upgrade_{user_id}")
                    ]
                ]
                
                try:
                    media = InputMediaPhoto(
                        media="https://files.catbox.moe/z8fhwx.jpg",
                        caption=caption,
                        parse_mode='HTML'
                    )
                    await query.edit_message_media(
                        media=media,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                except:
                    await query.edit_message_caption(
                        caption=caption,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='HTML'
                    )
                
            elif tier_type == 'elite':
                upi_id = PASS_CONFIG['elite']['upi_id']
                cost_inr = PASS_CONFIG['elite']['cost_inr']
                
                caption = (
                    f"╔═══════════════════╗\n"
                    f"  {to_small_caps('elite payment')}\n"
                    f"╚═══════════════════╝\n\n"
                    f"<b>{to_small_caps('payment')}:</b>\n"
                    f"{to_small_caps('amount')}: {cost_inr} {to_small_caps('inr')}\n"
                    f"{to_small_caps('upi')}: <code>{upi_id}</code>\n\n"
                    f"<b>{to_small_caps('steps')}:</b>\n"
                    f"1. {to_small_caps('pay to upi above')}\n"
                    f"2. {to_small_caps('screenshot payment')}\n"
                    f"3. {to_small_caps('click submit')}\n"
                    f"4. {to_small_caps('wait for approval')}\n\n"
                    f"<b>{to_small_caps('instant rewards')}:</b>\n"
                    f"• 100,000,000 {to_small_caps('gold')}\n"
                    f"• 10 {to_small_caps('mythic characters')}\n"
                    f"• 2x {to_small_caps('grab bonus')}\n"
                    f"• 10,000 {to_small_caps('gold per grab')}"
                )
                
                keyboard = [
                    [InlineKeyboardButton(to_small_caps("submit payment"), callback_data=f"pass_submit_elite_{user_id}")],
                    [InlineKeyboardButton(to_small_caps("cancel"), callback_data=f"pass_upgrade_{user_id}")]
                ]
                
                try:
                    media = InputMediaPhoto(
                        media="https://files.catbox.moe/z8fhwx.jpg",
                        caption=caption,
                        parse_mode='HTML'
                    )
                    await query.edit_message_media(
                        media=media,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                except:
                    await query.edit_message_caption(
                        caption=caption,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='HTML'
                    )
        
        elif action == 'confirm' and len(parts) >= 3:
            if parts[2] == 'premium':
                user = await user_collection.find_one({'id': user_id})
                cost = PASS_CONFIG['premium']['cost']
                balance = user.get('balance', 0)
                
                if balance < cost:
                    await query.answer(to_small_caps("insufficient balance"), show_alert=True)
                    return
                
                expires = datetime.utcnow() + timedelta(days=30)
                
                await user_collection.update_one(
                    {'id': user_id},
                    {
                        '$inc': {'balance': -cost},
                        '$set': {
                            'pass_data.tier': 'premium',
                            'pass_data.premium_expires': expires
                        }
                    }
                )
                
                caption = (
                    f"╔═══════════════════╗\n"
                    f"  ✅ {to_small_caps('premium active')}\n"
                    f"╚═══════════════════╝\n\n"
                    f"🎉 {to_small_caps('congratulations')}\n\n"
                    f"{to_small_caps('activated successfully')}\n"
                    f"{to_small_caps('expires')}: {expires.strftime('%Y-%m-%d')}\n\n"
                    f"<b>{to_small_caps('your benefits')}:</b>\n"
                    f"• 5,000 {to_small_caps('weekly reward')}\n"
                    f"• 25,000 {to_small_caps('streak bonus')}\n"
                    f"• 3 {to_small_caps('mythic per claim')}\n"
                    f"• 1.5x {to_small_caps('grab multiplier')}\n"
                    f"• 5,000 {to_small_caps('gold per grab')}\n\n"
                    f"{to_small_caps('enjoy your benefits')}"
                )
                
                keyboard = [[
                    InlineKeyboardButton(to_small_caps("back to pass"), callback_data=f"pass_back_{user_id}")
                ]]
                
                try:
                    media = InputMediaPhoto(
                        media="https://files.catbox.moe/z8fhwx.jpg",
                        caption=caption,
                        parse_mode='HTML'
                    )
                    await query.edit_message_media(
                        media=media,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                except:
                    await query.edit_message_caption(
                        caption=caption,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='HTML'
                    )
                
                await query.answer(to_small_caps("premium activated"), show_alert=False)
                LOGGER.info(f"[PASS] User {user_id} upgraded to premium")
        
        elif action == 'submit' and len(parts) >= 3:
            if parts[2] == 'elite':
                await user_collection.update_one(
                    {'id': user_id},
                    {'$set': {'pass_data.pending_elite_payment': datetime.utcnow()}}
                )
                
                try:
                    await context.bot.send_message(
                        chat_id=OWNER_ID,
                        text=(
                            f"╔═══════════════════╗\n"
                            f"  ⭐ {to_small_caps('new elite payment')}\n"
                            f"╚═══════════════════╝\n\n"
                            f"<b>{to_small_caps('user details')}:</b>\n"
                            f"{to_small_caps('id')}: <code>{user_id}</code>\n"
                            f"{to_small_caps('username')}: @{query.from_user.username or 'none'}\n"
                            f"{to_small_caps('name')}: {query.from_user.first_name}\n"
                            f"{to_small_caps('amount')}: 10 {to_small_caps('inr')}\n"
                            f"{to_small_caps('time')}: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}\n\n"
                            f"<b>{to_small_caps('to approve')}:</b>\n"
                            f"/approveelite {user_id}"
                        ),
                        parse_mode='HTML'
                    )
                except Exception as e:
                    LOGGER.error(f"[PASS] Could not notify owner: {e}")
                
                caption = (
                    f"╔═══════════════════╗\n"
                    f"  📤 {to_small_caps('payment submitted')}\n"
                    f"╚═══════════════════╝\n\n"
                    f"✅ {to_small_caps('request received')}\n\n"
                    f"{to_small_caps('owner will verify payment')}\n"
                    f"{to_small_caps('activation within 24 hours')}\n\n"
                    f"<b>{to_small_caps('you will receive')}:</b>\n"
                    f"• 100,000,000 {to_small_caps('gold')}\n"
                    f"• 10 {to_small_caps('mythic characters')}\n"
                    f"• {to_small_caps('elite benefits')}\n\n"
                    f"{to_small_caps('notification on activation')}"
                )
                
                keyboard = [[
                    InlineKeyboardButton(to_small_caps("back to pass"), callback_data=f"pass_back_{user_id}")
                ]]
                
                try:
                    media = InputMediaPhoto(
                        media="https://files.catbox.moe/z8fhwx.jpg",
                        caption=caption,
                        parse_mode='HTML'
                    )
                    await query.edit_message_media(
                        media=media,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                except:
                    await query.edit_message_caption(
                        caption=caption,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='HTML'
                    )
                
                await query.answer(to_small_caps("payment submitted"), show_alert=False)
                LOGGER.info(f"[PASS] User {user_id} submitted elite payment")
        
    except Exception as e:
        LOGGER.error(f"[PASS CALLBACK ERROR] {e}")
        try:
            await query.answer(to_small_caps('error processing request'), show_alert=True)
        except:
            pass


# Register handlers
application.add_handler(CommandHandler("pass", pass_command, block=False))
application.add_handler(CommandHandler("pclaim", pclaim_command, block=False))
application.add_handler(CommandHandler("sweekly", sweekly_command, block=False))
application.add_handler(CommandHandler("tasks", tasks_command, block=False))
application.add_handler(CommandHandler("upgrade", upgrade_command, block=False))
application.add_handler(CommandHandler("invite", invite_command, block=False))
application.add_handler(CommandHandler("approveelite", approve_elite_command, block=False))
application.add_handler(CallbackQueryHandler(pass_callback, pattern=r"^pass_", block=False))


# Export functions for use in other modules
__all__ = ['handle_grab_bonus', 'handle_referral']