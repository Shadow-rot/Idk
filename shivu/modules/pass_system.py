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
        'name': 'FREE PASS',
        'weekly_reward': 1000,
        'streak_bonus': 5000,
        'mythic_characters': 0,
        'grab_multiplier': 1.0
    },
    'premium': {
        'name': 'PREMIUM PASS',
        'weekly_reward': 5000,
        'streak_bonus': 25000,
        'mythic_characters': 3,
        'cost': 50000,
        'grab_multiplier': 1.5
    },
    'elite': {
        'name': 'ELITE PASS',
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
    'invites': {'required': 5, 'reward': 'MYTHIC CHARACTER'},
    'weekly_claims': {'required': 4, 'reward': 'BONUS REWARD'},
    'grabs': {'required': 50, 'reward': 'COLLECTOR'}
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
    """Update grab task count - Call this from your grab handler"""
    try:
        await user_collection.update_one(
            {'id': user_id},
            {'$inc': {'pass_data.tasks.grabs': 1}}
        )
        LOGGER.info(f"[PASS] Grab task updated for user {user_id}")
    except Exception as e:
        LOGGER.error(f"[PASS] Error updating grab task: {e}")


async def pass_command(update: Update, context: CallbackContext) -> None:
    """Show pass status and information - /pass"""
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

        tier_status = "FREE"
        if tier == 'elite':
            elite_expires = pass_data.get('elite_expires')
            if elite_expires and isinstance(elite_expires, datetime):
                days_left = (elite_expires - datetime.utcnow()).days
                tier_status = f"ELITE ({days_left} DAYS)"
        elif tier == 'premium':
            premium_expires = pass_data.get('premium_expires')
            if premium_expires and isinstance(premium_expires, datetime):
                days_left = (premium_expires - datetime.utcnow()).days
                tier_status = f"PREMIUM ({days_left} DAYS)"

        mythic_status = "UNLOCKED" if mythic_unlocked else "LOCKED"
        grab_multiplier = PASS_CONFIG[tier]['grab_multiplier']

        caption = f"""<b>{tier_name}</b>

<b>USER:</b> {escape(update.effective_user.first_name)}
<b>ID:</b> <code>{user_id}</code>
<b>BALANCE:</b> <code>{balance:,}</code>

<b>PROGRESS</b>
Weekly Claims: {weekly_claims}/6
Streak: {streak_count} weeks
Tasks Completed: {completed_tasks}/{total_tasks}
Mythic Unlock: {mythic_status}
Grab Multiplier: {grab_multiplier}x

<b>REWARDS</b>
Weekly: {PASS_CONFIG[tier]['weekly_reward']:,}
Streak Bonus: {PASS_CONFIG[tier]['streak_bonus']:,}
Tier Status: {tier_status}

<b>COMMANDS</b>
/pclaim - Weekly reward
/sweekly - Streak bonus
/tasks - View tasks
/upgrade - Get premium
/invite - Invite friends

Complete tasks to unlock mythic character
"""

        keyboard = [
            [
                InlineKeyboardButton("CLAIM", callback_data=f"pass_claim_{user_id}"),
                InlineKeyboardButton("TASKS", callback_data=f"pass_tasks_{user_id}")
            ],
            [
                InlineKeyboardButton("UPGRADE", callback_data=f"pass_upgrade_{user_id}"),
                InlineKeyboardButton("INVITE", callback_data=f"pass_invite_{user_id}")
            ],
            [
                InlineKeyboardButton("HELP", callback_data=f"pass_help_{user_id}")
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
        await update.message.reply_text('Error loading pass data')


async def pclaim_command(update: Update, context: CallbackContext) -> None:
    """Claim weekly reward - /pclaim"""
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

                msg = f"Next claim in\n\n{remaining.days} days {hours} hours {minutes} minutes"

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

                premium_msg = f"\n\nBONUS: {len(mythic_chars)} mythic characters added"

        success_text = (
            f"<b>CLAIMED SUCCESSFULLY</b>\n\n"
            f"Reward: <code>{reward:,}</code>\n"
            f"Total Claims: {new_claims}/6{premium_msg}"
        )

        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.answer("Claimed successfully", show_alert=False)
            await update.callback_query.message.reply_text(success_text, parse_mode='HTML')
        else:
            await update.message.reply_text(success_text, parse_mode='HTML')

        LOGGER.info(f"[PASS] User {user_id} claimed weekly reward")

    except Exception as e:
        LOGGER.error(f"[PASS CLAIM ERROR] {e}")
        error_msg = 'Error processing claim'
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.answer(error_msg, show_alert=True)
        else:
            await update.message.reply_text(error_msg)


async def sweekly_command(update: Update, context: CallbackContext) -> None:
    """Claim 6-week streak bonus - /sweekly"""
    user_id = update.effective_user.id

    try:
        tier = await check_and_update_tier(user_id)
        pass_data = await get_or_create_pass_data(user_id)

        weekly_claims = pass_data.get('weekly_claims', 0)
        if weekly_claims < 6:
            msg = f"You need 6 weekly claims\nCurrent: {weekly_claims}/6"
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
            char_msg = f"\n\nBONUS CHARACTER:\nName: {char_name}\nAnime: {char_anime}"

        await update.message.reply_text(
            f"<b>STREAK BONUS CLAIMED</b>\n\n"
            f"Bonus Gold: <code>{bonus:,}</code>\n"
            f"Weekly claims reset to 0{char_msg}",
            parse_mode='HTML'
        )

        LOGGER.info(f"[PASS] User {user_id} claimed streak bonus")

    except Exception as e:
        LOGGER.error(f"[PASS SWEEKLY ERROR] {e}")
        await update.message.reply_text('Error processing bonus')


async def tasks_command(update: Update, context: CallbackContext) -> None:
    """Show task progress - /tasks"""
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
                status = "COMPLETED"
            else:
                status = "IN PROGRESS"
                all_completed = False

            task_name = task_key.replace('_', ' ').upper()
            task_list.append(
                f"<b>{task_name}:</b> {current}/{required}\n"
                f"{'█' * (progress // 10)}{'░' * (10 - progress // 10)} {progress}%\n"
                f"Reward: {reward}\n"
                f"Status: {status}"
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

        mythic_status = 'COMPLETED' if mythic_unlocked else 'LOCKED'

        caption = f"""<b>MYTHIC TASKS</b>

{chr(10).join(task_list)}

MYTHIC UNLOCK: {mythic_status}

Complete all tasks to unlock a free mythic character
"""

        keyboard = [[
            InlineKeyboardButton("BACK", callback_data=f"pass_back_{user_id}")
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
        error_msg = 'Error loading tasks'
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.answer(error_msg, show_alert=True)
        else:
            await update.message.reply_text(error_msg)


async def invite_command(update: Update, context: CallbackContext) -> None:
    """Show invite program - /invite"""
    user_id = update.effective_user.id

    try:
        pass_data = await get_or_create_pass_data(user_id)

        invited_users = pass_data.get('invited_users', [])
        total_invites = pass_data.get('tasks', {}).get('invites', 0)
        total_earnings = pass_data.get('total_invite_earnings', 0)

        bot_username = context.bot.username
        invite_link = f"https://t.me/{bot_username}?start=r_{user_id}"

        caption = f"""<b>INVITE PROGRAM</b>

Your Referrals: {total_invites}
Earned: {total_earnings:,} GOLD

<b>HOW TO INVITE</b>
Copy link below
Share with friends
They click and start bot
Instant rewards

<b>REWARDS</b>
{INVITE_REWARD:,} gold per invite
Counts toward tasks

<b>YOUR INVITE LINK</b>
<code>{invite_link}</code>

Tap to copy link

Use /addinvite command to manually add invites
"""

        keyboard = [
            [InlineKeyboardButton("SHARE LINK", url=invite_link)],
            [InlineKeyboardButton("BACK", callback_data=f"pass_back_{user_id}")]
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
        error_msg = 'Error loading invite'
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.answer(error_msg, show_alert=True)
        else:
            await update.message.reply_text(error_msg)


async def upgrade_command(update: Update, context: CallbackContext) -> None:
    """Show upgrade options - /upgrade"""
    user_id = update.effective_user.id

    try:
        tier = await check_and_update_tier(user_id)
        pass_data = await get_or_create_pass_data(user_id)
        user = await user_collection.find_one({'id': user_id})
        balance = user.get('balance', 0)

        caption = f"""<b>UPGRADE OPTIONS</b>

Your Balance: <code>{balance:,}</code>
Current Tier: {PASS_CONFIG[tier]['name']}

<b>PREMIUM PASS</b>
Cost: <code>50,000</code> GOLD
Duration: 30 DAYS

<b>BENEFITS:</b>
Weekly Reward: 5,000
Streak Bonus: 25,000
Mythic Chars: 3 per claim
Multiplier: 1.5x

<b>ELITE PASS</b>
Cost: 10 INR
Payment: UPI
Duration: 30 DAYS

<b>BENEFITS:</b>
Activation Bonus: 100,000,000 GOLD
Instant Mythics: 10 characters
Weekly Reward: 15,000
Streak Bonus: 100,000
Mythic per claim: 10
Multiplier: 2x

Choose your upgrade
"""

        keyboard = [
            [InlineKeyboardButton("PREMIUM PASS", callback_data=f"pass_buy_premium_{user_id}")],
            [InlineKeyboardButton("ELITE PASS", callback_data=f"pass_buy_elite_{user_id}")],
            [InlineKeyboardButton("BACK", callback_data=f"pass_back_{user_id}")]
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
        error_msg = 'Error loading upgrade'
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.answer(error_msg, show_alert=True)
        else:
            await update.message.reply_text(error_msg)


async def addinvite_command(update: Update, context: CallbackContext) -> None:
    """Add invite count for a user - Owner only - /addinvite <user_id> <count>"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text('Unauthorized')
        return

    try:
        if len(context.args) < 2:
            await update.message.reply_text(
                f"<b>USAGE:</b> /addinvite user_id count\n\n"
                f"<b>EXAMPLE:</b> /addinvite 123456789 5",
                parse_mode='HTML'
            )
            return

        target_user_id = int(context.args[0])
        invite_count = int(context.args[1])

        if invite_count <= 0:
            await update.message.reply_text('Count must be positive')
            return

        await get_or_create_pass_data(target_user_id)

        gold_reward = invite_count * INVITE_REWARD

        await user_collection.update_one(
            {'id': target_user_id},
            {
                '$inc': {
                    'pass_data.tasks.invites': invite_count,
                    'pass_data.total_invite_earnings': gold_reward,
                    'balance': gold_reward
                }
            }
        )

        await update.message.reply_text(
            f"<b>INVITE ADDED</b>\n\n"
            f"User ID: <code>{target_user_id}</code>\n"
            f"Invites Added: {invite_count}\n"
            f"Gold Awarded: <code>{gold_reward:,}</code>",
            parse_mode='HTML'
        )

        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=(
                    f"<b>INVITE REWARD</b>\n\n"
                    f"You received {invite_count} invite credits\n"
                    f"Gold Earned: <code>{gold_reward:,}</code>"
                ),
                parse_mode='HTML'
            )
        except:
            pass

        LOGGER.info(f"[PASS] Added {invite_count} invites to user {target_user_id}")

    except ValueError:
        await update.message.reply_text('Invalid user ID or count')
    except Exception as e:
        LOGGER.error(f"[PASS ADDINVITE ERROR] {e}")
        await update.message.reply_text('Error adding invite')


async def addgrab_command(update: Update, context: CallbackContext) -> None:
    """Add grab count for a user - Owner only - /addgrab <user_id> <count>"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text('Unauthorized')
        return

    try:
        if len(context.args) < 2:
            await update.message.reply_text(
                f"<b>USAGE:</b> /addgrab user_id count\n\n"
                f"<b>EXAMPLE:</b> /addgrab 123456789 10",
                parse_mode='HTML'
            )
            return

        target_user_id = int(context.args[0])
        grab_count = int(context.args[1])

        if grab_count <= 0:
            await update.message.reply_text('Count must be positive')
            return

        await get_or_create_pass_data(target_user_id)

        await user_collection.update_one(
            {'id': target_user_id},
            {'$inc': {'pass_data.tasks.grabs': grab_count}}
        )

        await update.message.reply_text(
            f"<b>GRABS ADDED</b>\n\n"
            f"User ID: <code>{target_user_id}</code>\n"
            f"Grabs Added: {grab_count}",
            parse_mode='HTML'
        )

        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=(
                    f"<b>GRAB CREDITS ADDED</b>\n\n"
                    f"You received {grab_count} grab credits"
                ),
                parse_mode='HTML'
            )
        except:
            pass

        LOGGER.info(f"[PASS] Added {grab_count} grabs to user {target_user_id}")

    except ValueError:
        await update.message.reply_text('Invalid user ID or count')
    except Exception as e:
        LOGGER.error(f"[PASS ADDGRAB ERROR] {e}")
        await update.message.reply_text('Error adding grabs')


async def approve_elite_command(update: Update, context: CallbackContext) -> None:
    """Owner command to approve elite pass payment - /approveelite <user_id>"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text('Unauthorized')
        return

    try:
        if len(context.args) < 1:
            await update.message.reply_text(
                f"<b>USAGE:</b> /approveelite user_id\n\n"
                f"<b>EXAMPLE:</b> /approveelite 123456789",
                parse_mode='HTML'
            )
            return

        target_user_id = int(context.args[0])

        target_user = await user_collection.find_one({'id': target_user_id})
        if not target_user:
            await update.message.reply_text('User not found')
            return

        pass_data = target_user.get('pass_data', {})
        pending = pass_data.get('pending_elite_payment')

        if not pending:
            await update.message.reply_text('No pending payment for this user')
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
            f"<b>ELITE PASS ACTIVATED</b>\n\n"
            f"User ID: <code>{target_user_id}</code>\n"
            f"Gold Bonus: <code>{activation_bonus:,}</code>\n"
            f"Mythic Characters: {len(mythic_chars)}\n"
            f"Expires: {expires.strftime('%Y-%m-%d')}",
            parse_mode='HTML'
        )

        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=(
                    f"<b>ELITE PASS ACTIVATED</b>\n\n"
                    f"Your elite pass has been activated\n\n"
                    f"<b>RECEIVED:</b>\n"
                    f"Gold Coins: <code>{activation_bonus:,}</code>\n"
                    f"Mythic Characters: {len(mythic_chars)}\n"
                    f"Expires: {expires.strftime('%Y-%m-%d')}\n\n"
                    f"Enjoy your benefits\n"
                    f"Multiplier: 2x"
                ),
                parse_mode='HTML'
            )
        except Exception as e:
            LOGGER.error(f"[PASS] Could not notify user {target_user_id}: {e}")

        LOGGER.info(f"[PASS] Elite pass approved for user {target_user_id}")

    except ValueError:
        await update.message.reply_text('Invalid user ID')
    except Exception as e:
        LOGGER.error(f"[PASS APPROVE ERROR] {e}")
        await update.message.reply_text('Error processing approval')


async def passhelp_command(update: Update, context: CallbackContext) -> None:
    """Show all pass commands - /passhelp"""
    help_text = f"""<b>PASS SYSTEM COMMANDS</b>

<b>USER COMMANDS:</b>
/pass - View pass status
/pclaim - Claim weekly reward
/sweekly - Claim 6 week streak bonus
/tasks - View task progress
/upgrade - Upgrade to premium or elite
/invite - Get invite link
/passhelp - Show this help

<b>OWNER COMMANDS:</b>
/addinvite user_id count - Add invites
/addgrab user_id count - Add grabs
/approveelite user_id - Approve elite payment

<b>PASS TIERS:</b>
FREE: 1,000 weekly | 5,000 streak
PREMIUM: 5,000 weekly | 25,000 streak | 3 mythic per claim
ELITE: 15,000 weekly | 100,000 streak | 10 mythic per claim

<b>TASKS FOR MYTHIC UNLOCK:</b>
5 invites
4 weekly claims
50 grabs
"""

    await update.message.reply_text(help_text, parse_mode='HTML')


async def pass_callback(update: Update, context: CallbackContext) -> None:
    """Handle all pass button callbacks"""
    query = update.callback_query

    try:
        await query.answer()

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
            await query.answer("Not your request", show_alert=True)
            return

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
            update.callback_query = query
            await invite_command(update, context)

        elif action == 'help':
            help_text = f"""<b>PASS HELP</b>

<b>COMMANDS:</b>
/pass - View pass status
/pclaim - Claim weekly reward
/sweekly - Claim streak bonus
/tasks - View task progress
/upgrade - Upgrade options
/invite - Invite friends
/passhelp - Full command list

<b>HOW TO UNLOCK MYTHIC:</b>
Invite 5 people
Claim 4 weekly rewards
Grab 50 characters

<b>PASS TIERS:</b>
FREE: Basic rewards
PREMIUM: 50k gold for 30 days
ELITE: 10 INR for 30 days

Complete all tasks for free mythic
"""

            keyboard = [[
                InlineKeyboardButton("BACK", callback_data=f"pass_back_{user_id}")
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

            tier_status = "FREE"
            if tier == 'elite':
                elite_expires = pass_data.get('elite_expires')
                if elite_expires and isinstance(elite_expires, datetime):
                    days_left = (elite_expires - datetime.utcnow()).days
                    tier_status = f"ELITE ({days_left} DAYS)"
            elif tier == 'premium':
                premium_expires = pass_data.get('premium_expires')
                if premium_expires and isinstance(premium_expires, datetime):
                    days_left = (premium_expires - datetime.utcnow()).days
                    tier_status = f"PREMIUM ({days_left} DAYS)"

            mythic_status = "UNLOCKED" if mythic_unlocked else "LOCKED"
            grab_multiplier = PASS_CONFIG[tier]['grab_multiplier']

            caption = f"""<b>{tier_name}</b>

<b>USER:</b> {escape(query.from_user.first_name)}
<b>ID:</b> <code>{user_id}</code>
<b>BALANCE:</b> <code>{balance:,}</code>

<b>PROGRESS</b>
Weekly Claims: {weekly_claims}/6
Streak: {streak_count} weeks
Tasks Completed: {completed_tasks}/{total_tasks}
Mythic Unlock: {mythic_status}
Grab Multiplier: {grab_multiplier}x

<b>REWARDS</b>
Weekly: {PASS_CONFIG[tier]['weekly_reward']:,}
Streak Bonus: {PASS_CONFIG[tier]['streak_bonus']:,}
Tier Status: {tier_status}

<b>COMMANDS</b>
/pclaim - Weekly reward
/sweekly - Streak bonus
/tasks - View tasks
/upgrade - Get premium
/invite - Invite friends

Complete tasks to unlock mythic character
"""

            keyboard = [
                [
                    InlineKeyboardButton("CLAIM", callback_data=f"pass_claim_{user_id}"),
                    InlineKeyboardButton("TASKS", callback_data=f"pass_tasks_{user_id}")
                ],
                [
                    InlineKeyboardButton("UPGRADE", callback_data=f"pass_upgrade_{user_id}"),
                    InlineKeyboardButton("INVITE", callback_data=f"pass_invite_{user_id}")
                ],
                [
                    InlineKeyboardButton("HELP", callback_data=f"pass_help_{user_id}")
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
                    await query.answer("Insufficient balance", show_alert=True)
                    return

                caption = f"""<b>CONFIRM PREMIUM PURCHASE</b>

Cost: <code>{cost:,}</code> GOLD
Your Balance: <code>{balance:,}</code>

<b>BENEFITS:</b>
Weekly Reward: 5,000
Streak Bonus: 25,000
Mythic Chars: 3 per claim
Multiplier: 1.5x

Confirm purchase?
"""

                keyboard = [
                    [
                        InlineKeyboardButton("CONFIRM", callback_data=f"pass_confirm_premium_{user_id}"),
                        InlineKeyboardButton("CANCEL", callback_data=f"pass_cancel_{user_id}")
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

                caption = f"""<b>ELITE PASS PAYMENT</b>

<b>PAYMENT DETAILS:</b>
Amount: {cost_inr} INR
UPI ID: <code>{upi_id}</code>

<b>INSTRUCTIONS:</b>
Send {cost_inr} INR to the UPI ID above
Take a screenshot of payment
Click submit payment below
Owner will verify and activate

<b>BENEFITS:</b>
Activation Bonus: 100,000,000 GOLD
Instant Mythics: 10 characters
Weekly Reward: 15,000
Streak Bonus: 100,000
Mythic per claim: 10
Multiplier: 2x
"""

                keyboard = [
                    [InlineKeyboardButton("SUBMIT PAYMENT", callback_data=f"pass_submit_elite_{user_id}")],
                    [InlineKeyboardButton("CANCEL", callback_data=f"pass_cancel_{user_id}")]
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
                    await query.answer("Insufficient balance", show_alert=True)
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

                caption = f"""<b>PREMIUM ACTIVATED</b>

Premium pass activated successfully
Expires: {expires.strftime('%Y-%m-%d')}

<b>YOUR BENEFITS:</b>
Weekly Reward: 5,000
Streak Bonus: 25,000
Mythic Chars: 3 per claim
Multiplier: 1.5x

Enjoy your benefits
"""

                keyboard = [[
                    InlineKeyboardButton("BACK TO PASS", callback_data=f"pass_back_{user_id}")
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

                await query.answer("Premium activated", show_alert=False)
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
                            f"<b>ELITE PASS PAYMENT</b>\n\n"
                            f"User ID: <code>{user_id}</code>\n"
                            f"Username: @{query.from_user.username or 'none'}\n"
                            f"Name: {query.from_user.first_name}\n"
                            f"Amount: 10 INR\n\n"
                            f"Verify payment and use:\n"
                            f"<code>/approveelite {user_id}</code>"
                        ),
                        parse_mode='HTML'
                    )
                except Exception as e:
                    LOGGER.error(f"[PASS] Could not notify owner: {e}")

                caption = f"""<b>PAYMENT SUBMITTED</b>

Your payment request has been submitted

Owner will verify and activate your elite pass within 24 hours

You will receive a notification once activated

You will receive:
100,000,000 GOLD
10 mythic characters
"""

                keyboard = [[
                    InlineKeyboardButton("BACK TO PASS", callback_data=f"pass_back_{user_id}")
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

                await query.answer("Payment submitted for verification", show_alert=False)
                LOGGER.info(f"[PASS] User {user_id} submitted elite payment")

        elif action == 'cancel':
            await query.answer("Cancelled", show_alert=False)
            update.callback_query = query
            await upgrade_command(update, context)

    except Exception as e:
        LOGGER.error(f"[PASS CALLBACK ERROR] {e}")
        await query.answer('Error processing request', show_alert=True)


# ========================================
# REGISTER ALL HANDLERS
# ========================================

# User commands
application.add_handler(CommandHandler("pass", pass_command, block=False))
application.add_handler(CommandHandler("pclaim", pclaim_command, block=False))
application.add_handler(CommandHandler("sweekly", sweekly_command, block=False))
application.add_handler(CommandHandler("tasks", tasks_command, block=False))
application.add_handler(CommandHandler("upgrade", upgrade_command, block=False))
application.add_handler(CommandHandler("invite", invite_command, block=False))
application.add_handler(CommandHandler("passhelp", passhelp_command, block=False))

# Owner commands
application.add_handler(CommandHandler("addinvite", addinvite_command, block=False))
application.add_handler(CommandHandler("addgrab", addgrab_command, block=False))
application.add_handler(CommandHandler("approveelite", approve_elite_command, block=False))

# Callback handler for all buttons
application.add_handler(CallbackQueryHandler(pass_callback, pattern=r"^pass_", block=False))

LOGGER.info("[PASS] All handlers registered successfully")


# ========================================
# INTEGRATION GUIDE
# ========================================
"""
TO INTEGRATE WITH YOUR EXISTING GRAB/GACHA SYSTEM:

1. Import the function at the top of your grab handler file:
   from your_pass_module import update_grab_task

2. Add this line AFTER a successful character grab:
   await update_grab_task(user_id)

Example:
   
async def your_grab_handler(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    # Your existing grab logic here...
    # Character successfully grabbed
    
    # Update pass grab task
    await update_grab_task(user_id)
    
    # Rest of your code...
"""