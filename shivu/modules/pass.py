from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from html import escape

from shivu import application, user_collection, collection, user_totals_collection, LOGGER

# Owner ID for approval
OWNER_ID = 5147822244

# Pass configuration
PASS_CONFIG = {
    'free': {
        'name': 'ғʀᴇᴇ ᴘᴀss',
        'weekly_reward': 1000,
        'streak_bonus': 5000,
        'mythic_characters': 0,
        'grab_multiplier': 1.0
    },
    'premium': {
        'name': 'ᴘʀᴇᴍɪᴜᴍ ᴘᴀss',
        'weekly_reward': 5000,
        'streak_bonus': 25000,
        'mythic_characters': 3,
        'cost': 50000,
        'grab_multiplier': 1.5
    },
    'elite': {
        'name': 'ᴇʟɪᴛᴇ ᴘᴀss',
        'weekly_reward': 15000,
        'streak_bonus': 100000,
        'mythic_characters': 10,
        'cost_inr': 10,
        'upi_id': 'looktouhid@oksbi',
        'activation_bonus': 100000000,
        'grab_multiplier': 2.0
    }
}

# Task requirements
MYTHIC_TASKS = {
    'invites': {'required': 5, 'reward': 'ᴍʏᴛʜɪᴄ ᴄʜᴀʀᴀᴄᴛᴇʀ'},
    'weekly_claims': {'required': 4, 'reward': 'ʙᴏɴᴜs ʀᴇᴡᴀʀᴅ'},
    'grabs': {'required': 50, 'reward': 'ᴄᴏʟʟᴇᴄᴛᴏʀ'}
}

# Invite rewards
INVITE_REWARD = 1000


def to_small_caps(text):
    """Convert text to small caps"""
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
            'invited_users': [],
            'total_invite_earnings': 0
        }
        await user_collection.update_one(
            {'id': user_id},
            {'$set': {'pass_data': pass_data}}
        )
        return pass_data

    return user.get('pass_data', {})


async def check_and_update_tier(user_id: int) -> str:
    """Check if tier has expired and update accordingly"""
    pass_data = await get_or_create_pass_data(user_id)
    tier = pass_data.get('tier', 'free')
    
    if tier == 'elite':
        elite_expires = pass_data.get('elite_expires')
        if elite_expires and isinstance(elite_expires, datetime):
            if elite_expires < datetime.utcnow():
                await user_collection.update_one(
                    {'id': user_id},
                    {'$set': {'pass_data.tier': 'free'}}
                )
                return 'free'
    elif tier == 'premium':
        premium_expires = pass_data.get('premium_expires')
        if premium_expires and isinstance(premium_expires, datetime):
            if premium_expires < datetime.utcnow():
                await user_collection.update_one(
                    {'id': user_id},
                    {'$set': {'pass_data.tier': 'free'}}
                )
                return 'free'
    
    return tier


async def update_grab_task(user_id: int):
    """Update grab task count"""
    try:
        await user_collection.update_one(
            {'id': user_id},
            {'$inc': {'pass_data.tasks.grabs': 1}}
        )
        LOGGER.info(f"[PASS] Grab task updated for user {user_id}")
    except Exception as e:
        LOGGER.error(f"[PASS] Error updating grab task: {e}")


async def pass_command(update: Update, context: CallbackContext) -> None:
    """Show pass status and information"""
    user_id = update.effective_user.id

    try:
        tier = await check_and_update_tier(user_id)
        pass_data = await get_or_create_pass_data(user_id)
        user = await user_collection.find_one({'id': user_id})

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
                days_left = (elite_expires - datetime.utcnow()).days
                tier_status = to_small_caps("elite") + f" ({days_left} " + to_small_caps("days") + ")"
        elif tier == 'premium':
            premium_expires = pass_data.get('premium_expires')
            if premium_expires and isinstance(premium_expires, datetime):
                days_left = (premium_expires - datetime.utcnow()).days
                tier_status = to_small_caps("premium") + f" ({days_left} " + to_small_caps("days") + ")"

        mythic_status = to_small_caps("unlocked") if mythic_unlocked else to_small_caps("locked")
        grab_multiplier = PASS_CONFIG[tier]['grab_multiplier']

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
{to_small_caps('grab multiplier')}: {grab_multiplier}x

━━━━━━━━━━━━━━━━━━━
{to_small_caps('rewards')}
━━━━━━━━━━━━━━━━━━━
{to_small_caps('weekly')}: {PASS_CONFIG[tier]['weekly_reward']:,}
{to_small_caps('streak bonus')}: {PASS_CONFIG[tier]['streak_bonus']:,}
{to_small_caps('tier status')}: {tier_status}

━━━━━━━━━━━━━━━━━━━
{to_small_caps('commands')}
━━━━━━━━━━━━━━━━━━━
/pclaim - {to_small_caps('weekly reward')}
/sweekly - {to_small_caps('streak bonus')}
/tasks - {to_small_caps('view tasks')}
/upgrade - {to_small_caps('get premium')}
/invite - {to_small_caps('invite friends')}

{to_small_caps('complete tasks to unlock mythic character')}
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
        tier = await check_and_update_tier(user_id)
        pass_data = await get_or_create_pass_data(user_id)

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

        # Streak management
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
    """Claim 6-week streak bonus"""
    user_id = update.effective_user.id

    try:
        tier = await check_and_update_tier(user_id)
        pass_data = await get_or_create_pass_data(user_id)

        weekly_claims = pass_data.get('weekly_claims', 0)
        if weekly_claims < 6:
            msg = (
                f"{to_small_caps('you need 6 weekly claims')}\n"
                f"{to_small_caps('current')}: {weekly_claims}/6"
            )
            await update.message.reply_text(msg)
            return

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
            progress = min(100, int((current / required) * 100))

            if current >= required:
                status = to_small_caps("completed")
            else:
                status = to_small_caps("in progress")
                all_completed = False

            task_list.append(
                f"<b>{to_small_caps(task_key.replace('_', ' '))}:</b> {current}/{required}\n"
                f"   {'█' * (progress // 10)}{'░' * (10 - progress // 10)} {progress}%\n"
                f"   {to_small_caps('reward')}: {reward}\n"
                f"   {to_small_caps('status')}: {status}"
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
                LOGGER.info(f"[PASS] Mythic unlocked for user {user_id}")

        mythic_status = to_small_caps('completed') if mythic_unlocked else to_small_caps('locked')

        caption = f"""╔═══════════════════╗
  {to_small_caps('mythic tasks')}
╚═══════════════════╝

{chr(10).join(task_list)}

━━━━━━━━━━━━━━━━━━━
{to_small_caps('mythic unlock')}: {mythic_status}

{to_small_caps('complete all tasks to unlock a free mythic character')}
"""

        keyboard = [[
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


async def invite_command(update: Update, context: CallbackContext) -> None:
    """Show invite program"""
    user_id = update.effective_user.id

    try:
        pass_data = await get_or_create_pass_data(user_id)
        
        invited_users = pass_data.get('invited_users', [])
        total_invites = len(invited_users)
        total_earnings = pass_data.get('total_invite_earnings', 0)
        
        bot_username = context.bot.username
        invite_link = f"https://t.me/{bot_username}?start=r_{user_id}"
        
        caption = f"""╔═══════════════════╗
  {to_small_caps('invite program')}
╚═══════════════════╝

{to_small_caps('your referrals')}: {total_invites}
{to_small_caps('earned')}: {total_earnings:,} {to_small_caps('gold')}

━━━━━━━━━━━━━━━━━━━
{to_small_caps('how to invite')}
━━━━━━━━━━━━━━━━━━━
{to_small_caps('copy link below')}
{to_small_caps('share with friends')}
{to_small_caps('they click and start bot')}
{to_small_caps('instant rewards')}

━━━━━━━━━━━━━━━━━━━
{to_small_caps('rewards')}
━━━━━━━━━━━━━━━━━━━
{INVITE_REWARD:,} {to_small_caps('gold per invite')}
{to_small_caps('counts toward tasks')}

━━━━━━━━━━━━━━━━━━━
{to_small_caps('your invite link')}
━━━━━━━━━━━━━━━━━━━
<code>{invite_link}</code>

{to_small_caps('tap to copy link')}
"""

        keyboard = [
            [InlineKeyboardButton(to_small_caps("share link"), url=invite_link)],
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

        LOGGER.info(f"[PASS] Invite shown for user {user_id}")

    except Exception as e:
        LOGGER.error(f"[PASS INVITE ERROR] {e}")
        error_msg = to_small_caps('error loading invite')
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.answer(error_msg, show_alert=True)
        else:
            await update.message.reply_text(error_msg)


async def upgrade_command(update: Update, context: CallbackContext) -> None:
    """Show upgrade options"""
    user_id = update.effective_user.id

    try:
        tier = await check_and_update_tier(user_id)
        pass_data = await get_or_create_pass_data(user_id)
        user = await user_collection.find_one({'id': user_id})
        balance = user.get('balance', 0)

        caption = f"""╔═══════════════════╗
  {to_small_caps('upgrade options')}
╚═══════════════════╝

{to_small_caps('your balance')}: <code>{balance:,}</code>
{to_small_caps('current tier')}: {PASS_CONFIG[tier]['name']}

━━━━━━━━━━━━━━━━━━━
{to_small_caps('premium pass')}
━━━━━━━━━━━━━━━━━━━
{to_small_caps('cost')}: <code>50,000</code> {to_small_caps('gold')}
{to_small_caps('duration')}: 30 {to_small_caps('days')}

<b>{to_small_caps('benefits')}:</b>
{to_small_caps('weekly reward')}: 5,000
{to_small_caps('streak bonus')}: 25,000
{to_small_caps('mythic chars')}: 3 {to_small_caps('per claim')}
{to_small_caps('multiplier')}: 1.5x

━━━━━━━━━━━━━━━━━━━
{to_small_caps('elite pass')}
━━━━━━━━━━━━━━━━━━━
{to_small_caps('cost')}: 10 {to_small_caps('inr')}
{to_small_caps('payment')}: UPI
{to_small_caps('duration')}: 30 {to_small_caps('days')}

<b>{to_small_caps('benefits')}:</b>
{to_small_caps('activation bonus')}: 100,000,000 {to_small_caps('gold')}
{to_small_caps('instant mythics')}: 10 {to_small_caps('characters')}
{to_small_caps('weekly reward')}: 15,000
{to_small_caps('streak bonus')}: 100,000
{to_small_caps('mythic per claim')}: 10
{to_small_caps('multiplier')}: 2x

{to_small_caps('choose your upgrade')}
"""

        keyboard = [
            [InlineKeyboardButton(to_small_caps("premium pass"), callback_data=f"pass_buy_premium_{user_id}")