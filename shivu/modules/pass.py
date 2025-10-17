from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from html import escape
import random

from shivu import application, user_collection, collection, user_totals_collection, LOGGER

# Owner ID for approval
OWNER_ID = 5147822244
BOT_USERNAME = "waifukunbot"

# Pass configuration
PASS_CONFIG = {
    'free': {
        'name': 'ғʀᴇᴇ ᴘᴀss',
        'weekly_reward': 1000,
        'streak_bonus': 5000,
        'mythic_characters': 0
    },
    'premium': {
        'name': 'ᴘʀᴇᴍɪᴜᴍ ᴘᴀss',
        'weekly_reward': 5000,
        'streak_bonus': 25000,
        'mythic_characters': 3,
        'cost': 50000
    },
    'elite': {
        'name': 'ᴇʟɪᴛᴇ ᴘᴀss',
        'weekly_reward': 15000,
        'streak_bonus': 100000,
        'mythic_characters': 10,
        'cost_inr': 10,
        'upi_id': 'looktouhid@oksbi',
        'activation_bonus': 100000000
    }
}

# Task requirements
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


async def handle_grab_task(user_id: int):
    """Update grab task count"""
    try:
        await user_collection.update_one(
            {'id': user_id},
            {'$inc': {'pass_data.tasks.grabs': 1}}
        )
        LOGGER.info(f"[PASS] Updated grab count for user {user_id}")
    except Exception as e:
        LOGGER.error(f"[PASS] Error updating grab task: {e}")


async def handle_referral(referrer_id: int, new_user_id: int):
    """Handle referral when new user joins"""
    try:
        existing = await user_collection.find_one({'id': new_user_id})
        if existing and existing.get('referred_by'):
            return False

        await user_collection.update_one(
            {'id': new_user_id},
            {'$set': {'referred_by': referrer_id}},
            upsert=True
        )

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


async def pass_command(update: Update, context: CallbackContext) -> None:
    """Show pass status and help"""
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
                    tier_status = to_small_caps("elite") + f" {days_left}ᴅ"
                else:
                    tier_status = to_small_caps("expired")
        elif tier == 'premium':
            premium_expires = pass_data.get('premium_expires')
            if premium_expires and isinstance(premium_expires, datetime):
                if premium_expires > datetime.utcnow():
                    days_left = (premium_expires - datetime.utcnow()).days
                    tier_status = to_small_caps("premium") + f" {days_left}ᴅ"
                else:
                    tier_status = to_small_caps("expired")

        mythic_status = to_small_caps("unlocked") if mythic_unlocked else to_small_caps("locked")

        caption = f"""{tier_name}

{to_small_caps('user')} {escape(update.effective_user.first_name)}
{to_small_caps('balance')} {balance:,}

{to_small_caps('progress')}
{to_small_caps('weekly claims')} {weekly_claims}/6
{to_small_caps('streak')} {streak_count} {to_small_caps('weeks')}
{to_small_caps('tasks')} {completed_tasks}/{total_tasks}
{to_small_caps('mythic')} {mythic_status}

{to_small_caps('rewards')}
{to_small_caps('weekly')} {PASS_CONFIG[tier]['weekly_reward']:,}
{to_small_caps('streak bonus')} {PASS_CONFIG[tier]['streak_bonus']:,}
{to_small_caps('status')} {tier_status}

{to_small_caps('commands')}
/pclaim - {to_small_caps('claim weekly reward')}
/sweekly - {to_small_caps('claim streak bonus')}
/tasks - {to_small_caps('view task progress')}
/upgrade - {to_small_caps('upgrade pass tier')}
/invite - {to_small_caps('get referral link')}
"""

        keyboard = [
            [
                InlineKeyboardButton(to_small_caps("claim"), callback_data=f"pass_claim"),
                InlineKeyboardButton(to_small_caps("tasks"), callback_data=f"pass_tasks")
            ],
            [
                InlineKeyboardButton(to_small_caps("upgrade"), callback_data=f"pass_upgrade"),
                InlineKeyboardButton(to_small_caps("invite"), callback_data=f"pass_invite")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_photo(
            photo="https://files.catbox.moe/z8fhwx.jpg",
            caption=caption,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    except Exception as e:
        LOGGER.error(f"[PASS ERROR] {e}")
        await update.message.reply_text(to_small_caps('error loading pass data'))


async def pclaim_command(update: Update, context: CallbackContext) -> None:
    """Claim weekly reward"""
    user_id = update.effective_user.id

    try:
        pass_data = await get_or_create_pass_data(user_id)

        last_claim = pass_data.get('last_weekly_claim')
        if last_claim and isinstance(last_claim, datetime):
            time_since = datetime.utcnow() - last_claim
            if time_since < timedelta(days=7):
                remaining = timedelta(days=7) - time_since
                hours = remaining.seconds // 3600
                minutes = (remaining.seconds % 3600) // 60

                msg = f"{to_small_caps('next claim in')}\n{remaining.days}ᴅ {hours}ʜ {minutes}ᴍ"
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

                premium_msg = f"\n{to_small_caps('bonus')} {len(mythic_chars)} {to_small_caps('mythic added')}"

        success_text = f"{to_small_caps('claimed')}\n{to_small_caps('reward')} {reward:,}\n{to_small_caps('claims')} {new_claims}/6{premium_msg}"
        await update.message.reply_text(success_text)

    except Exception as e:
        LOGGER.error(f"[PASS CLAIM ERROR] {e}")
        await update.message.reply_text(to_small_caps('error processing claim'))


async def sweekly_command(update: Update, context: CallbackContext) -> None:
    """Claim streak bonus"""
    user_id = update.effective_user.id

    try:
        pass_data = await get_or_create_pass_data(user_id)

        weekly_claims = pass_data.get('weekly_claims', 0)
        if weekly_claims < 6:
            msg = f"{to_small_caps('need 6 claims')}\n{to_small_caps('current')} {weekly_claims}/6"
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

        await user_collection.update_one({'id': user_id}, update_data)

        if mythic_char:
            await user_totals_collection.update_one(
                {'id': user_id},
                {'$inc': {'count': 1}},
                upsert=True
            )

        char_msg = ""
        if mythic_char:
            char_name = mythic_char.get('name', 'unknown')
            char_msg = f"\n{to_small_caps('bonus')} {char_name}"

        await update.message.reply_text(
            f"{to_small_caps('streak claimed')}\n{to_small_caps('bonus')} {bonus:,}\n{to_small_caps('claims reset')}{char_msg}"
        )

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
            display = task_info['display']

            if current >= required:
                status = "✅"
            else:
                status = "⏳"
                all_completed = False

            task_list.append(f"{status} {display} {current}/{required}")

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

        mythic_status = '✅' if mythic_unlocked else '🔒'

        caption = f"""{to_small_caps('mythic tasks')}

{chr(10).join(task_list)}

{to_small_caps('mythic unlock')} {mythic_status}
"""

        keyboard = [[
            InlineKeyboardButton(to_small_caps("refresh"), callback_data=f"pass_tasks"),
            InlineKeyboardButton(to_small_caps("back"), callback_data=f"pass_back")
        ]]

        await update.message.reply_photo(
            photo="https://files.catbox.moe/z8fhwx.jpg",
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        LOGGER.error(f"[PASS TASKS ERROR] {e}")
        await update.message.reply_text(to_small_caps('error loading tasks'))


async def upgrade_command(update: Update, context: CallbackContext) -> None:
    """Show upgrade options"""
    user_id = update.effective_user.id

    try:
        pass_data = await get_or_create_pass_data(user_id)
        user = await user_collection.find_one({'id': user_id})
        balance = user.get('balance', 0)
        tier = pass_data.get('tier', 'free')

        caption = f"""{to_small_caps('upgrade pass')}

{to_small_caps('balance')} {balance:,}
{to_small_caps('current')} {PASS_CONFIG[tier]['name']}

💎 {to_small_caps('premium pass')}
{to_small_caps('cost')} 50000 {to_small_caps('gold')}
{to_small_caps('duration')} 30 {to_small_caps('days')}

{to_small_caps('benefits')}
{to_small_caps('weekly')} 5000
{to_small_caps('streak')} 25000
{to_small_caps('mythic')} 3 {to_small_caps('per claim')}

⭐ {to_small_caps('elite pass')}
{to_small_caps('cost')} 10 {to_small_caps('inr')}
{to_small_caps('upi')} {PASS_CONFIG['elite']['upi_id']}
{to_small_caps('duration')} 30 {to_small_caps('days')}

{to_small_caps('benefits')}
{to_small_caps('instant')} 100000000 {to_small_caps('gold')}
{to_small_caps('instant')} 10 {to_small_caps('mythic')}
{to_small_caps('weekly')} 15000
{to_small_caps('streak')} 100000
{to_small_caps('mythic')} 10 {to_small_caps('per claim')}
"""

        keyboard = [
            [InlineKeyboardButton(to_small_caps("buy premium"), callback_data=f"pass_buy_premium")],
            [InlineKeyboardButton(to_small_caps("buy elite"), callback_data=f"pass_buy_elite")],
            [InlineKeyboardButton(to_small_caps("back"), callback_data=f"pass_back")]
        ]

        await update.message.reply_photo(
            photo="https://files.catbox.moe/z8fhwx.jpg",
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        LOGGER.error(f"[PASS UPGRADE ERROR] {e}")
        await update.message.reply_text(to_small_caps('error loading upgrade'))


async def invite_command(update: Update, context: CallbackContext) -> None:
    """Show invite information"""
    user_id = update.effective_user.id

    try:
        pass_data = await get_or_create_pass_data(user_id)

        referral_count = pass_data.get('referral_count', 0)
        referral_earnings = pass_data.get('referral_earnings', 0)
        invite_link = f"https://t.me/{BOT_USERNAME}?start=r_{user_id}"

        caption = f"""ɪɴᴠɪᴛᴇ ᴘʀᴏɢʀᴀᴍ

ʏᴏᴜʀ ʀᴇғᴇʀʀᴀʟs {referral_count}
ᴇᴀʀɴᴇᴅ {referral_earnings:,} ɢᴏʟᴅ

ʜᴏᴡ ᴛᴏ ɪɴᴠɪᴛᴇ
ᴄᴏᴘʏ ʟɪɴᴋ ʙᴇʟᴏᴡ
sʜᴀʀᴇ ᴡɪᴛʜ ғʀɪᴇɴᴅs
ᴛʜᴇʏ ᴄʟɪᴄᴋ ᴀɴᴅ sᴛᴀʀᴛ ʙᴏᴛ
ɪɴsᴛᴀɴᴛ ʀᴇᴡᴀʀᴅs

ʏᴏᴜʀ ɪɴᴠɪᴛᴇ ʟɪɴᴋ
<code>{invite_link}</code>

ʀᴇᴡᴀʀᴅs
1000 ɢᴏʟᴅ ᴘᴇʀ ʀᴇғᴇʀʀᴀʟ
ᴄᴏᴜɴᴛs ᴛᴏᴡᴀʀᴅs ᴘᴀss ᴛᴀsᴋs
ᴜɴʟᴏᴄᴋ ᴍʏᴛʜɪᴄ ᴀᴛ 5 ɪɴᴠɪᴛᴇs
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

    except Exception as e:
        LOGGER.error(f"[PASS INVITE ERROR] {e}")
        await update.message.reply_text(to_small_caps('error loading invite data'))


async def approve_elite_command(update: Update, context: CallbackContext) -> None:
    """Owner command to approve elite pass"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text(to_small_caps('unauthorized'))
        return

    try:
        if len(context.args) < 1:
            await update.message.reply_text(f"{to_small_caps('usage')} /approveelite userid")
            return

        target_user_id = int(context.args[0])
        target_user = await user_collection.find_one({'id': target_user_id})

        if not target_user:
            await update.message.reply_text(to_small_caps('user not found'))
            return

        pass_data = target_user.get('pass_data', {})
        if not pass_data.get('pending_elite_payment'):
            await update.message.reply_text(to_small_caps('no pending payment'))
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
            f"✅ {to_small_caps('elite activated')}\n{to_small_caps('user')} {target_user_id}\n{to_small_caps('gold')} {activation_bonus:,}\n{to_small_caps('mythic')} {len(mythic_chars)}"
        )

        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"⭐ {to_small_caps('elite activated')}\n\n{to_small_caps('gold')} {activation_bonus:,}\n{to_small_caps('mythic')} {len(mythic_chars)}"
            )
        except Exception as e:
            LOGGER.error(f"[PASS] Could not notify user: {e}")

    except ValueError:
        await update.message.reply_text(to_small_caps('invalid user id'))
    except Exception as e:
        LOGGER.error(f"[PASS APPROVE ERROR] {e}")
        await update.message.reply_text(to_small_caps('error processing'))


async def pass_callback(update: Update, context: CallbackContext) -> None:
    """Handle pass callbacks"""
    query = update.callback_query
    
    # CRITICAL: Answer immediately to prevent timeout
    try:
        await query.answer()
    except:
        pass

    try:
        data = query.data
        user_id = query.from_user.id

        if data == "pass_claim":
            pass_data = await get_or_create_pass_data(user_id)
            last_claim = pass_data.get('last_weekly_claim')
            
            if last_claim and isinstance(last_claim, datetime):
                time_since = datetime.utcnow() - last_claim
                if time_since < timedelta(days=7):
                    remaining = timedelta(days=7) - time_since
                    hours = remaining.seconds // 3600
                    minutes = (remaining.seconds % 3600) // 60
                    try:
                        await query.answer(f"{to_small_caps('next claim in')} {remaining.days}ᴅ {hours}ʜ {minutes}ᴍ", show_alert=True)
                    except:
                        pass
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
                    premium_msg = f"\n{to_small_caps('bonus')} {len(mythic_chars)} {to_small_caps('mythic added')}"
            
            success_msg = f"{to_small_caps('claimed')}\n{to_small_caps('reward')} {reward:,}\n{to_small_caps('claims')} {new_claims}/6{premium_msg}"
            try:
                await query.message.reply_text(success_msg)
            except:
                pass

        elif data == "pass_tasks":
            pass_data = await get_or_create_pass_data(user_id)
            tasks = pass_data.get('tasks', {})
            mythic_unlocked = pass_data.get('mythic_unlocked', False)

            task_list = []
            all_completed = True
            for task_key, task_info in MYTHIC_TASKS.items():
                current = tasks.get(task_key, 0)
                required = task_info['required']
                display = task_info['display']

                if current >= required:
                    status = "✅"
                else:
                    status = "⏳"
                    all_completed = False

                task_list.append(f"{status} {display} {current}/{required}")

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

            mythic_status = '✅' if mythic_unlocked else '🔒'

            caption = f"""{to_small_caps('mythic tasks')}

{chr(10).join(task_list)}

{to_small_caps('mythic unlock')} {mythic_status}
"""

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(to_small_caps("refresh"), callback_data="pass_tasks"),
                    InlineKeyboardButton(to_small_caps("back"), callback_data="pass_back")
                ]
            ])

            try:
                media = InputMediaPhoto(media="https://files.catbox.moe/z8fhwx.jpg", caption=caption)
                await query.edit_message_media(media=media, reply_markup=keyboard)
            except:
                try:
                    await query.edit_message_caption(caption=caption, reply_markup=keyboard)
                except:
                    pass

        elif data == "pass_upgrade":
            pass_data = await get_or_create_pass_data(user_id)
            user = await user_collection.find_one({'id': user_id})
            balance = user.get('balance', 0)
            tier = pass_data.get('tier', 'free')

            caption = f"""{to_small_caps('upgrade pass')}

{to_small_caps('balance')} {balance:,}
{to_small_caps('current')} {PASS_CONFIG[tier]['name']}

💎 {to_small_caps('premium pass')}
{to_small_caps('cost')} 50000 {to_small_caps('gold')}
{to_small_caps('duration')} 30 {to_small_caps('days')}

{to_small_caps('benefits')}
{to_small_caps('weekly')} 5000
{to_small_caps('streak')} 25000
{to_small_caps('mythic')} 3 {to_small_caps('per claim')}

⭐ {to_small_caps('elite pass')}
{to_small_caps('cost')} 10 {to_small_caps('inr')}
{to_small_caps('upi')} {PASS_CONFIG['elite']['upi_id']}
{to_small_caps('duration')} 30 {to_small_caps('days')}

{to_small_caps('benefits')}
{to_small_caps('instant')} 100000000 {to_small_caps('gold')}
{to_small_caps('instant')} 10 {to_small_caps('mythic')}
{to_small_caps('weekly')} 15000
{to_small_caps('streak')} 100000
{to_small_caps('mythic')} 10 {to_small_caps('per claim')}
"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(to_small_caps("buy premium"), callback_data="pass_buy_premium")],
                [InlineKeyboardButton(to_small_caps("buy elite"), callback_data="pass_buy_elite")],
                [InlineKeyboardButton(to_small_caps("back"), callback_data="pass_back")]
            ])

            try:
                media = InputMediaPhoto(media="https://files.catbox.moe/z8fhwx.jpg", caption=caption)
                await query.edit_message_media(media=media, reply_markup=keyboard)
            except:
                try:
                    await query.edit_message_caption(caption=caption, reply_markup=keyboard)
                except:
                    pass

        elif data == "pass_invite":
            pass_data = await get_or_create_pass_data(user_id)
            referral_count = pass_data.get('referral_count', 0)
            referral_earnings = pass_data.get('referral_earnings', 0)
            invite_link = f"https://t.me/{BOT_USERNAME}?start=r_{user_id}"

            caption = f"""ɪɴᴠɪᴛᴇ ᴘʀᴏɢʀᴀᴍ

ʏᴏᴜʀ ʀᴇғᴇʀʀᴀʟs {referral_count}
ᴇᴀʀɴᴇᴅ {referral_earnings:,} ɢᴏʟᴅ

ʜᴏᴡ ᴛᴏ ɪɴᴠɪᴛᴇ
ᴄᴏᴘʏ ʟɪɴᴋ ʙᴇʟᴏᴡ
sʜᴀʀᴇ ᴡɪᴛʜ ғʀɪᴇɴᴅs
ᴛʜᴇʏ ᴄʟɪᴄᴋ ᴀɴᴅ sᴛᴀʀᴛ ʙᴏᴛ

ʏᴏᴜʀ ɪɴᴠɪᴛᴇ ʟɪɴᴋ
<code>{invite_link}</code>

ʀᴇᴡᴀʀᴅs
1000 ɢᴏʟᴅ ᴘᴇʀ ʀᴇғᴇʀʀᴀʟ
ᴜɴʟᴏᴄᴋ ᴍʏᴛʜɪᴄ ᴀᴛ 5 ɪɴᴠɪᴛᴇs
"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("sʜᴀʀᴇ ʟɪɴᴋ", url=f"https://t.me/share/url?url={invite_link}")],
                [InlineKeyboardButton(to_small_caps("back"), callback_data="pass_back")]
            ])

            try:
                media = InputMediaPhoto(media="https://files.catbox.moe/z8fhwx.jpg", caption=caption, parse_mode='HTML')
                await query.edit_message_media(media=media, reply_markup=keyboard)
            except:
                try:
                    await query.edit_message_caption(caption=caption, reply_markup=keyboard, parse_mode='HTML')
                except:
                    pass

        elif data == "pass_buy_premium":
            user = await user_collection.find_one({'id': user_id})
            cost = PASS_CONFIG['premium']['cost']
            balance = user.get('balance', 0)

            if balance < cost:
                try:
                    await query.answer(f"{to_small_caps('need')} {cost - balance:,} {to_small_caps('more gold')}", show_alert=True)
                except:
                    pass
                return

            caption = f"""{to_small_caps('confirm premium')}

{to_small_caps('cost')} {cost:,}
{to_small_caps('balance')} {balance:,}

{to_small_caps('benefits')}
{to_small_caps('weekly')} 5000
{to_small_caps('streak')} 25000
{to_small_caps('mythic')} 3 {to_small_caps('per claim')}
"""

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(to_small_caps("confirm"), callback_data="pass_confirm_premium"),
                    InlineKeyboardButton(to_small_caps("cancel"), callback_data="pass_upgrade")
                ]
            ])

            try:
                media = InputMediaPhoto(media="https://files.catbox.moe/z8fhwx.jpg", caption=caption)
                await query.edit_message_media(media=media, reply_markup=keyboard)
            except:
                try:
                    await query.edit_message_caption(caption=caption, reply_markup=keyboard)
                except:
                    pass

        elif data == "pass_buy_elite":
            upi_id = PASS_CONFIG['elite']['upi_id']
            cost_inr = PASS_CONFIG['elite']['cost_inr']

            caption = f"""{to_small_caps('elite payment')}

{to_small_caps('amount')} {cost_inr} {to_small_caps('inr')}
{to_small_caps('upi')} <code>{upi_id}</code>

{to_small_caps('steps')}
1 {to_small_caps('pay to upi above')}
2 {to_small_caps('screenshot payment')}
3 {to_small_caps('click submit')}
4 {to_small_caps('wait for approval')}

{to_small_caps('instant rewards')}
{to_small_caps('gold')} 100000000
{to_small_caps('mythic')} 10 {to_small_caps('characters')}
"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(to_small_caps("submit payment"), callback_data="pass_submit_elite")],
                [InlineKeyboardButton(to_small_caps("cancel"), callback_data="pass_upgrade")]
            ])

            try:
                media = InputMediaPhoto(media="https://files.catbox.moe/z8fhwx.jpg", caption=caption, parse_mode='HTML')
                await query.edit_message_media(media=media, reply_markup=keyboard)
            except:
                try:
                    await query.edit_message_caption(caption=caption, reply_markup=keyboard, parse_mode='HTML')
                except:
                    pass

        elif data == "pass_confirm_premium":
            user = await user_collection.find_one({'id': user_id})
            cost = PASS_CONFIG['premium']['cost']
            balance = user.get('balance', 0)

            if balance < cost:
                try:
                    await query.answer(to_small_caps("insufficient balance"), show_alert=True)
                except:
                    pass
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

            caption = f"""✅ {to_small_caps('premium active')}

{to_small_caps('activated successfully')}
{to_small_caps('expires')} {expires.strftime('%Y-%m-%d')}

{to_small_caps('benefits')}
{to_small_caps('weekly')} 5000
{to_small_caps('streak')} 25000
{to_small_caps('mythic')} 3 {to_small_caps('per claim')}
"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(to_small_caps("back"), callback_data="pass_back")]
            ])

            try:
                media = InputMediaPhoto(media="https://files.catbox.moe/z8fhwx.jpg", caption=caption)
                await query.edit_message_media(media=media, reply_markup=keyboard)
            except:
                try:
                    await query.edit_message_caption(caption=caption, reply_markup=keyboard)
                except:
                    pass

            LOGGER.info(f"[PASS] User {user_id} upgraded to premium")

        elif data == "pass_submit_elite":
            await user_collection.update_one(
                {'id': user_id},
                {'$set': {'pass_data.pending_elite_payment': datetime.utcnow()}}
            )

            try:
                await context.bot.send_message(
                    chat_id=OWNER_ID,
                    text=f"""⭐ {to_small_caps('new elite payment')}

{to_small_caps('user')} {user_id}
{to_small_caps('username')} @{query.from_user.username or 'none'}
{to_small_caps('name')} {query.from_user.first_name}
{to_small_caps('amount')} 10 {to_small_caps('inr')}

{to_small_caps('to approve')}
/approveelite {user_id}"""
                )
            except Exception as e:
                LOGGER.error(f"[PASS] Could not notify owner: {e}")

            caption = f"""📤 {to_small_caps('payment submitted')}

✅ {to_small_caps('request received')}

{to_small_caps('owner will verify')}
{to_small_caps('activation within 24h')}

{to_small_caps('rewards')}
{to_small_caps('gold')} 100000000
{to_small_caps('mythic')} 10
"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(to_small_caps("back"), callback_data="pass_back")]
            ])

            try:
                media = InputMediaPhoto(media="https://files.catbox.moe/z8fhwx.jpg", caption=caption)
                await query.edit_message_media(media=media, reply_markup=keyboard)
            except:
                try:
                    await query.edit_message_caption(caption=caption, reply_markup=keyboard)
                except:
                    pass

            LOGGER.info(f"[PASS] User {user_id} submitted elite payment")

        elif data == "pass_back":
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
                        tier_status = to_small_caps("elite") + f" {days_left}ᴅ"
            elif tier == 'premium':
                premium_expires = pass_data.get('premium_expires')
                if premium_expires and isinstance(premium_expires, datetime):
                    if premium_expires > datetime.utcnow():
                        days_left = (premium_expires - datetime.utcnow()).days
                        tier_status = to_small_caps("premium") + f" {days_left}ᴅ"

            mythic_status = to_small_caps("unlocked") if mythic_unlocked else to_small_caps("locked")

            caption = f"""{tier_name}

{to_small_caps('user')} {escape(query.from_user.first_name)}
{to_small_caps('balance')} {balance:,}

{to_small_caps('progress')}
{to_small_caps('weekly claims')} {weekly_claims}/6
{to_small_caps('streak')} {streak_count} {to_small_caps('weeks')}
{to_small_caps('tasks')} {completed_tasks}/{total_tasks}
{to_small_caps('mythic')} {mythic_status}

{to_small_caps('rewards')}
{to_small_caps('weekly')} {PASS_CONFIG[tier]['weekly_reward']:,}
{to_small_caps('streak bonus')} {PASS_CONFIG[tier]['streak_bonus']:,}
{to_small_caps('status')} {tier_status}

{to_small_caps('commands')}
/pclaim - {to_small_caps('claim weekly reward')}
/sweekly - {to_small_caps('claim streak bonus')}
/tasks - {to_small_caps('view task progress')}
/upgrade - {to_small_caps('upgrade pass tier')}
/invite - {to_small_caps('get referral link')}
"""

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(to_small_caps("claim"), callback_data="pass_claim"),
                    InlineKeyboardButton(to_small_caps("tasks"), callback_data="pass_tasks")
                ],
                [
                    InlineKeyboardButton(to_small_caps("upgrade"), callback_data="pass_upgrade"),
                    InlineKeyboardButton(to_small_caps("invite"), callback_data="pass_invite")
                ]
            ])

            try:
                media = InputMediaPhoto(media="https://files.catbox.moe/z8fhwx.jpg", caption=caption, parse_mode='HTML')
                await query.edit_message_media(media=media, reply_markup=keyboard)
            except:
                try:
                    await query.edit_message_caption(caption=caption, reply_markup=keyboard, parse_mode='HTML')
                except:
                    pass

    except Exception as e:
        LOGGER.error(f"[PASS CALLBACK ERROR] {e}")
        try:
            await query.answer(to_small_caps('error'), show_alert=True)
        except:
            pass
            pass_data = await get_or_create_pass_data(user_id)
            last_claim = pass_data.get('last_weekly_claim')
            
            if last_claim and isinstance(last_claim, datetime):
                time_since = datetime.utcnow() - last_claim
                if time_since < timedelta(days=7):
                    remaining = timedelta(days=7) - time_since
                    hours = remaining.seconds // 3600
                    minutes = (remaining.seconds % 3600) // 60
                    await query.answer(f"{to_small_caps('next claim in')} {remaining.days}ᴅ {hours}ʜ {minutes}ᴍ", show_alert=True)
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
                    premium_msg = f"\n{to_small_caps('bonus')} {len(mythic_chars)} {to_small_caps('mythic added')}"
            
            await query.answer(to_small_caps("claimed successfully"), show_alert=False)
            await query.message.reply_text(f"{to_small_caps('claimed')}\n{to_small_caps('reward')} {reward:,}\n{to_small_caps('claims')} {new_claims}/6{premium_msg}")

        elif data == "pass_tasks":
            pass_data = await get_or_create_pass_data(user_id)
            tasks = pass_data.get('tasks', {})
            mythic_unlocked = pass_data.get('mythic_unlocked', False)

            task_list = []
            all_completed = True
            for task_key, task_info in MYTHIC_TASKS.items():
                current = tasks.get(task_key, 0)
                required = task_info['required']
                display = task_info['display']

                if current >= required:
                    status = "✅"
                else:
                    status = "⏳"
                    all_completed = False

                task_list.append(f"{status} {display} {current}/{required}")

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

            mythic_status = '✅' if mythic_unlocked else '🔒'

            caption = f"""{to_small_caps('mythic tasks')}

{chr(10).join(task_list)}

{to_small_caps('mythic unlock')} {mythic_status}
"""

            keyboard = [[
                InlineKeyboardButton(to_small_caps("refresh"), callback_data="pass_tasks"),
                InlineKeyboardButton(to_small_caps("back"), callback_data="pass_back")
            ]]

            try:
                media = InputMediaPhoto(media="https://files.catbox.moe/z8fhwx.jpg", caption=caption)
                await query.edit_message_media(media=media, reply_markup=InlineKeyboardMarkup(keyboard))
            except:
                await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))

       elif data == "pass_upgrade":
            pass_data = await get_or_create_pass_data(user_id)
            user = await user_collection.find_one({'id': user_id})
            balance = user.get('balance', 0)
            tier = pass_data.get('tier', 'free')

            caption = f"""{to_small_caps('upgrade pass')}

{to_small_caps('balance')} {balance:,}
{to_small_caps('current')} {PASS_CONFIG[tier]['name']}

💎 {to_small_caps('premium pass')}
{to_small_caps('cost')} 50000 {to_small_caps('gold')}
{to_small_caps('duration')} 30 {to_small_caps('days')}

{to_small_caps('benefits')}
{to_small_caps('weekly')} 5000
{to_small_caps('streak')} 25000
{to_small_caps('mythic')} 3 {to_small_caps('per claim')}

⭐ {to_small_caps('elite pass')}
{to_small_caps('cost')} 10 {to_small_caps('inr')}
{to_small_caps('upi')} {PASS_CONFIG['elite']['upi_id']}
{to_small_caps('duration')} 30 {to_small_caps('days')}

{to_small_caps('benefits')}
{to_small_caps('instant')} 100000000 {to_small_caps('gold')}
{to_small_caps('instant')} 10 {to_small_caps('mythic')}
{to_small_caps('weekly')} 15000
{to_small_caps('streak')} 100000
{to_small_caps('mythic')} 10 {to_small_caps('per claim')}
"""

            keyboard = [
                [InlineKeyboardButton(to_small_caps("buy premium"), callback_data="pass_buy_premium")],
                [InlineKeyboardButton(to_small_caps("buy elite"), callback_data="pass_buy_elite")],
                [InlineKeyboardButton(to_small_caps("back"), callback_data="pass_back")]
            ]

            try:
                media = InputMediaPhoto(media="https://files.catbox.moe/z8fhwx.jpg", caption=caption)
                await query.edit_message_media(media=media, reply_markup=InlineKeyboardMarkup(keyboard))
            except:
                await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "pass_invite":
            pass_data = await get_or_create_pass_data(user_id)
            referral_count = pass_data.get('referral_count', 0)
            referral_earnings = pass_data.get('referral_earnings', 0)
            invite_link = f"https://t.me/{BOT_USERNAME}?start=r_{user_id}"

            caption = f"""ɪɴᴠɪᴛᴇ ᴘʀᴏɢʀᴀᴍ

ʏᴏᴜʀ ʀᴇғᴇʀʀᴀʟs {referral_count}
ᴇᴀʀɴᴇᴅ {referral_earnings:,} ɢᴏʟᴅ

ʜᴏᴡ ᴛᴏ ɪɴᴠɪᴛᴇ
ᴄᴏᴘʏ ʟɪɴᴋ ʙᴇʟᴏᴡ
sʜᴀʀᴇ ᴡɪᴛʜ ғʀɪᴇɴᴅs
ᴛʜᴇʏ ᴄʟɪᴄᴋ ᴀɴᴅ sᴛᴀʀᴛ ʙᴏᴛ

ʏᴏᴜʀ ɪɴᴠɪᴛᴇ ʟɪɴᴋ
<code>{invite_link}</code>

ʀᴇᴡᴀʀᴅs
1000 ɢᴏʟᴅ ᴘᴇʀ ʀᴇғᴇʀʀᴀʟ
ᴜɴʟᴏᴄᴋ ᴍʏᴛʜɪᴄ ᴀᴛ 5 ɪɴᴠɪᴛᴇs
"""

            keyboard = [
                [InlineKeyboardButton("sʜᴀʀᴇ ʟɪɴᴋ", url=f"https://t.me/share/url?url={invite_link}")],
                [InlineKeyboardButton(to_small_caps("back"), callback_data="pass_back")]
            ]

            try:
                media = InputMediaPhoto(media="https://files.catbox.moe/z8fhwx.jpg", caption=caption, parse_mode='HTML')
                await query.edit_message_media(media=media, reply_markup=InlineKeyboardMarkup(keyboard))
            except:
                await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

        elif data == "pass_buy_premium":
            user = await user_collection.find_one({'id': user_id})
            cost = PASS_CONFIG['premium']['cost']
            balance = user.get('balance', 0)

            if balance < cost:
                await query.answer(f"{to_small_caps('need')} {cost - balance:,} {to_small_caps('more gold')}", show_alert=True)
                return

            caption = f"""{to_small_caps('confirm premium')}

{to_small_caps('cost')} {cost:,}
{to_small_caps('balance')} {balance:,}

{to_small_caps('benefits')}
{to_small_caps('weekly')} 5000
{to_small_caps('streak')} 25000
{to_small_caps('mythic')} 3 {to_small_caps('per claim')}
"""

            keyboard = [
                [
                    InlineKeyboardButton(to_small_caps("confirm"), callback_data="pass_confirm_premium"),
                    InlineKeyboardButton(to_small_caps("cancel"), callback_data="pass_upgrade")
                ]
            ]

            try:
                media = InputMediaPhoto(media="https://files.catbox.moe/z8fhwx.jpg", caption=caption)
                await query.edit_message_media(media=media, reply_markup=InlineKeyboardMarkup(keyboard))
            except:
                await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "pass_buy_elite":
            upi_id = PASS_CONFIG['elite']['upi_id']
            cost_inr = PASS_CONFIG['elite']['cost_inr']

            caption = f"""{to_small_caps('elite payment')}

{to_small_caps('amount')} {cost_inr} {to_small_caps('inr')}
{to_small_caps('upi')} <code>{upi_id}</code>

{to_small_caps('steps')}
1 {to_small_caps('pay to upi above')}
2 {to_small_caps('screenshot payment')}
3 {to_small_caps('click submit')}
4 {to_small_caps('wait for approval')}

{to_small_caps('instant rewards')}
{to_small_caps('gold')} 100000000
{to_small_caps('mythic')} 10 {to_small_caps('characters')}
"""

            keyboard = [
                [InlineKeyboardButton(to_small_caps("submit payment"), callback_data="pass_submit_elite")],
                [InlineKeyboardButton(to_small_caps("cancel"), callback_data="pass_upgrade")]
            ]

            try:
                media = InputMediaPhoto(media="https://files.catbox.moe/z8fhwx.jpg", caption=caption, parse_mode='HTML')
                await query.edit_message_media(media=media, reply_markup=InlineKeyboardMarkup(keyboard))
            except:
                await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

        elif data == "pass_confirm_premium":
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

            caption = f"""✅ {to_small_caps('premium active')}

{to_small_caps('activated successfully')}
{to_small_caps('expires')} {expires.strftime('%Y-%m-%d')}

{to_small_caps('benefits')}
{to_small_caps('weekly')} 5000
{to_small_caps('streak')} 25000
{to_small_caps('mythic')} 3 {to_small_caps('per claim')}
"""

            keyboard = [[InlineKeyboardButton(to_small_caps("back"), callback_data="pass_back")]]

            try:
                media = InputMediaPhoto(media="https://files.catbox.moe/z8fhwx.jpg", caption=caption)
                await query.edit_message_media(media=media, reply_markup=InlineKeyboardMarkup(keyboard))
            except:
                await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))

            await query.answer(to_small_caps("premium activated"), show_alert=False)
            LOGGER.info(f"[PASS] User {user_id} upgraded to premium")

        elif data == "pass_submit_elite":
            await user_collection.update_one(
                {'id': user_id},
                {'$set': {'pass_data.pending_elite_payment': datetime.utcnow()}}
            )

            try:
                await context.bot.send_message(
                    chat_id=OWNER_ID,
                    text=f"""⭐ {to_small_caps('new elite payment')}

{to_small_caps('user')} {user_id}
{to_small_caps('username')} @{query.from_user.username or 'none'}
{to_small_caps('name')} {query.from_user.first_name}
{to_small_caps('amount')} 10 {to_small_caps('inr')}

{to_small_caps('to approve')}
/approveelite {user_id}"""
                )
            except Exception as e:
                LOGGER.error(f"[PASS] Could not notify owner: {e}")

            caption = f"""📤 {to_small_caps('payment submitted')}

✅ {to_small_caps('request received')}

{to_small_caps('owner will verify')}
{to_small_caps('activation within 24h')}

{to_small_caps('rewards')}
{to_small_caps('gold')} 100000000
{to_small_caps('mythic')} 10
"""

            keyboard = [[InlineKeyboardButton(to_small_caps("back"), callback_data="pass_back")]]

            try:
                media = InputMediaPhoto(media="https://files.catbox.moe/z8fhwx.jpg", caption=caption)
                await query.edit_message_media(media=media, reply_markup=InlineKeyboardMarkup(keyboard))
            except:
                await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))

            await query.answer(to_small_caps("payment submitted"), show_alert=False)
            LOGGER.info(f"[PASS] User {user_id} submitted elite payment")

        elif data == "pass_back":
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
                        tier_status = to_small_caps("elite") + f" {days_left}ᴅ"
            elif tier == 'premium':
                premium_expires = pass_data.get('premium_expires')
                if premium_expires and isinstance(premium_expires, datetime):
                    if premium_expires > datetime.utcnow():
                        days_left = (premium_expires - datetime.utcnow()).days
                        tier_status = to_small_caps("premium") + f" {days_left}ᴅ"

            mythic_status = to_small_caps("unlocked") if mythic_unlocked else to_small_caps("locked")

            caption = f"""{tier_name}

{to_small_caps('user')} {escape(query.from_user.first_name)}
{to_small_caps('balance')} {balance:,}

{to_small_caps('progress')}
{to_small_caps('weekly claims')} {weekly_claims}/6
{to_small_caps('streak')} {streak_count} {to_small_caps('weeks')}
{to_small_caps('tasks')} {completed_tasks}/{total_tasks}
{to_small_caps('mythic')} {mythic_status}

{to_small_caps('rewards')}
{to_small_caps('weekly')} {PASS_CONFIG[tier]['weekly_reward']:,}
{to_small_caps('streak bonus')} {PASS_CONFIG[tier]['streak_bonus']:,}
{to_small_caps('status')} {tier_status}

{to_small_caps('commands')}
/pclaim - {to_small_caps('claim weekly reward')}
/sweekly - {to_small_caps('claim streak bonus')}
/tasks - {to_small_caps('view task progress')}
/upgrade - {to_small_caps('upgrade pass tier')}
/invite - {to_small_caps('get referral link')}
"""

            keyboard = [
                [
                    InlineKeyboardButton(to_small_caps("claim"), callback_data="pass_claim"),
                    InlineKeyboardButton(to_small_caps("tasks"), callback_data="pass_tasks")
                ],
                [
                    InlineKeyboardButton(to_small_caps("upgrade"), callback_data="pass_upgrade"),
                    InlineKeyboardButton(to_small_caps("invite"), callback_data="pass_invite")
                ]
            ]

            try:
                media = InputMediaPhoto(media="https://files.catbox.moe/z8fhwx.jpg", caption=caption, parse_mode='HTML')
                await query.edit_message_media(media=media, reply_markup=InlineKeyboardMarkup(keyboard))
            except:
                await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    except Exception as e:
        LOGGER.error(f"[PASS CALLBACK ERROR] {e}")
        await query.answer(to_small_caps('error'), show_alert=True)


def register_pass_handlers():
    """Register all pass handlers - MUST be called before other callback handlers"""
    application.add_handler(CommandHandler("pass", pass_command, block=False))
    application.add_handler(CommandHandler("pclaim", pclaim_command, block=False))
    application.add_handler(CommandHandler("sweekly", sweekly_command, block=False))
    application.add_handler(CommandHandler("tasks", tasks_command, block=False))
    application.add_handler(CommandHandler("upgrade", upgrade_command, block=False))
    application.add_handler(CommandHandler("invite", invite_command, block=False))
    application.add_handler(CommandHandler("approveelite", approve_elite_command, block=False))
    application.add_handler(CallbackQueryHandler(pass_callback, pattern=r"^pass_", block=False), group=-1)
    LOGGER.info("✅ Pass system handlers registered with priority")


__all__ = ['register_pass_handlers', 'handle_grab_task', 'handle_referral']