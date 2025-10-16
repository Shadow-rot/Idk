from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from html import escape

from shivu import application, user_collection, collection, user_totals_collection, LOGGER

# Owner ID
OWNER_ID = 5147822244

# Pass configuration
PASS_CONFIG = {
    'free': {
        'name': 'FREE PASS',
        'weekly_reward': 1000,
        'streak_bonus': 5000,
        'mythic_characters': 0
    },
    'premium': {
        'name': 'PREMIUM PASS',
        'weekly_reward': 5000,
        'streak_bonus': 25000,
        'mythic_characters': 3,
        'cost': 50000
    },
    'elite': {
        'name': 'ELITE PASS',
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
    'invites': {'required': 5, 'reward': 'MYTHIC CHARACTER'},
    'weekly_claims': {'required': 4, 'reward': 'BONUS REWARD'}
}

# Invite reward
INVITE_REWARD = 1000


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
            'tasks': {
                'invites': 0,
                'weekly_claims': 0
            },
            'mythic_unlocked': False,
            'premium_expires': None,
            'elite_expires': None,
            'pending_elite_payment': None,
            'invited_by': None,
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


async def handle_referral(user_id: int, referrer_id: int, context: CallbackContext):
    """Handle referral when user joins"""
    try:
        if referrer_id == user_id:
            return
        
        pass_data = await get_or_create_pass_data(user_id)
        
        if pass_data.get('invited_by'):
            return
        
        await user_collection.update_one(
            {'id': referrer_id},
            {
                '$push': {'pass_data.invited_users': user_id},
                '$inc': {
                    'balance': INVITE_REWARD,
                    'pass_data.tasks.invites': 1,
                    'pass_data.total_invite_earnings': INVITE_REWARD
                }
            }
        )
        
        await user_collection.update_one(
            {'id': user_id},
            {'$set': {'pass_data.invited_by': referrer_id}}
        )
        
        try:
            await context.bot.send_message(
                chat_id=referrer_id,
                text=f"NEW REFERRAL!\n\nYou earned: {INVITE_REWARD:,} gold\nTotal invites: +1",
                parse_mode='HTML'
            )
        except:
            pass
        
        LOGGER.info(f"[PASS] User {user_id} referred by {referrer_id}")
        
    except Exception as e:
        LOGGER.error(f"[PASS REFERRAL ERROR] {e}")


async def pass_command(update: Update, context: CallbackContext) -> None:
    """Show pass status"""
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
                tier_status = f"ELITE ({days_left} days)"
        elif tier == 'premium':
            premium_expires = pass_data.get('premium_expires')
            if premium_expires and isinstance(premium_expires, datetime):
                days_left = (premium_expires - datetime.utcnow()).days
                tier_status = f"PREMIUM ({days_left} days)"

        mythic_status = "UNLOCKED" if mythic_unlocked else "LOCKED"

        caption = f"""<b>{tier_name}</b>

USER: {escape(update.effective_user.first_name)}
ID: <code>{user_id}</code>
BALANCE: <code>{balance:,}</code>

<b>PROGRESS</b>
Weekly Claims: {weekly_claims}/6
Streak: {streak_count} weeks
Tasks: {completed_tasks}/{total_tasks}
Mythic: {mythic_status}

<b>REWARDS</b>
Weekly: {PASS_CONFIG[tier]['weekly_reward']:,}
Streak Bonus: {PASS_CONFIG[tier]['streak_bonus']:,}
Status: {tier_status}

<b>COMMANDS</b>
/pclaim - Claim weekly reward
/sweekly - Claim streak bonus
/tasks - View tasks
/upgrade - Upgrade pass
/invite - Invite friends
"""

        keyboard = [
            [
                InlineKeyboardButton("CLAIM", callback_data=f"pass_claim"),
                InlineKeyboardButton("TASKS", callback_data=f"pass_tasks")
            ],
            [
                InlineKeyboardButton("UPGRADE", callback_data=f"pass_upgrade"),
                InlineKeyboardButton("INVITE", callback_data=f"pass_invite")
            ]
        ]

        await update.message.reply_photo(
            photo="https://files.catbox.moe/z8fhwx.jpg",
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

        LOGGER.info(f"[PASS] Status shown for user {user_id}")

    except Exception as e:
        LOGGER.error(f"[PASS ERROR] {e}")
        await update.message.reply_text("Error loading pass data")


async def pclaim_command(update: Update, context: CallbackContext) -> None:
    """Claim weekly reward"""
    user_id = update.effective_user.id
    is_callback = hasattr(update, 'callback_query') and update.callback_query

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
                msg = f"Next claim in: {remaining.days}d {hours}h {minutes}m"

                if is_callback:
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
                    {'$inc': {'pass_data.streak_count': 1}}
                )
            elif days_since > 8:
                await user_collection.update_one(
                    {'id': user_id},
                    {'$set': {'pass_data.streak_count': 0}}
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

                premium_msg = f"\n\nBONUS: {len(mythic_chars)} Mythic characters added"

        success_text = f"CLAIMED!\n\nReward: <code>{reward:,}</code>\nTotal Claims: {new_claims}/6{premium_msg}"

        if is_callback:
            await update.callback_query.answer("Claimed!", show_alert=False)
            await update.callback_query.message.reply_text(success_text, parse_mode='HTML')
        else:
            await update.message.reply_text(success_text, parse_mode='HTML')

        LOGGER.info(f"[PASS] User {user_id} claimed weekly reward")

    except Exception as e:
        LOGGER.error(f"[PASS CLAIM ERROR] {e}")
        error_msg = "Error processing claim"
        if is_callback:
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
            await update.message.reply_text(f"You need 6 weekly claims\nCurrent: {weekly_claims}/6")
            return

        bonus = PASS_CONFIG[tier]['streak_bonus']
        mythic_char = await collection.find_one({'rarity': '🏵 Mythic'})

        update_data = {
            '$inc': {'balance': bonus},
            '$set': {'pass_data.weekly_claims': 0, 'pass_data.last_streak_claim': datetime.utcnow()}
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
            char_name = mythic_char.get('name', 'Unknown')
            char_anime = mythic_char.get('anime', 'Unknown')
            char_msg = f"\n\nBONUS CHARACTER:\nName: {char_name}\nAnime: {char_anime}"

        await update.message.reply_text(
            f"STREAK BONUS CLAIMED!\n\nBonus Gold: <code>{bonus:,}</code>\nWeekly claims reset to 0{char_msg}",
            parse_mode='HTML'
        )

        LOGGER.info(f"[PASS] User {user_id} claimed streak bonus")

    except Exception as e:
        LOGGER.error(f"[PASS SWEEKLY ERROR] {e}")
        await update.message.reply_text("Error processing bonus")


async def tasks_command(update: Update, context: CallbackContext) -> None:
    """Show task progress"""
    user_id = update.effective_user.id
    is_callback = hasattr(update, 'callback_query') and update.callback_query

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
                f"Progress: {progress}%\n"
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

        mythic_status = "COMPLETED" if mythic_unlocked else "LOCKED"

        caption = f"""<b>MYTHIC TASKS</b>

{chr(10).join(task_list)}

<b>MYTHIC UNLOCK:</b> {mythic_status}

Complete all tasks to unlock a free mythic character
"""

        keyboard = [[InlineKeyboardButton("BACK", callback_data="pass_back")]]

        if is_callback:
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
        error_msg = "Error loading tasks"
        if is_callback:
            await update.callback_query.answer(error_msg, show_alert=True)
        else:
            await update.message.reply_text(error_msg)


async def invite_command(update: Update, context: CallbackContext) -> None:
    """Show invite program"""
    user_id = update.effective_user.id
    is_callback = hasattr(update, 'callback_query') and update.callback_query

    try:
        pass_data = await get_or_create_pass_data(user_id)
        
        invited_users = pass_data.get('invited_users', [])
        total_invites = len(invited_users)
        total_earnings = pass_data.get('total_invite_earnings', 0)
        
        bot_username = context.bot.username
        invite_link = f"https://t.me/{bot_username}?start=r_{user_id}"
        
        caption = f"""<b>INVITE PROGRAM</b>

Your Referrals: {total_invites}
Total Earned: {total_earnings:,} gold

<b>HOW TO INVITE</b>
1. Copy your invite link
2. Share with friends
3. They click and start bot
4. Instant rewards

<b>REWARDS</b>
{INVITE_REWARD:,} gold per invite
Counts toward tasks

<b>YOUR INVITE LINK</b>
<code>{invite_link}</code>

Tap to copy link
"""

        keyboard = [
            [InlineKeyboardButton("COPY LINK", url=invite_link)],
            [InlineKeyboardButton("BACK", callback_data="pass_back")]
        ]

        if is_callback:
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
        error_msg = "Error loading invite"
        if is_callback:
            await update.callback_query.answer(error_msg, show_alert=True)
        else:
            await update.message.reply_text(error_msg)


async def upgrade_command(update: Update, context: CallbackContext) -> None:
    """Show upgrade options"""
    user_id = update.effective_user.id
    is_callback = hasattr(update, 'callback_query') and update.callback_query

    try:
        tier = await check_and_update_tier(user_id)
        user = await user_collection.find_one({'id': user_id})
        balance = user.get('balance', 0)

        caption = f"""<b>UPGRADE OPTIONS</b>

Your Balance: <code>{balance:,}</code>
Current Tier: {PASS_CONFIG[tier]['name']}

<b>PREMIUM PASS</b>
Cost: <code>50,000</code> gold
Duration: 30 days

BENEFITS:
• Weekly Reward: 5,000
• Streak Bonus: 25,000
• Mythic Chars: 3 per claim

<b>ELITE PASS</b>
Cost: 10 INR
Payment: UPI
Duration: 30 days

BENEFITS:
• Activation Bonus: 100,000,000 gold
• Instant Mythics: 10 characters
• Weekly Reward: 15,000
• Streak Bonus: 100,000
• Mythic per Claim: 10
"""

        keyboard = [
            [InlineKeyboardButton("PREMIUM PASS", callback_data="pass_buy_premium")],
            [InlineKeyboardButton("ELITE PASS", callback_data="pass_buy_elite")],
            [InlineKeyboardButton("BACK", callback_data="pass_back")]
        ]

        if is_callback:
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
        error_msg = "Error loading upgrade"
        if is_callback:
            await update.callback_query.answer(error_msg, show_alert=True)
        else:
            await update.message.reply_text(error_msg)


async def approve_elite_command(update: Update, context: CallbackContext) -> None:
    """Owner command to approve elite pass payment"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Unauthorized")
        return

    try:
        if len(context.args) < 1:
            await update.message.reply_text("Usage: /approveelite <user_id>")
            return

        target_user_id = int(context.args[0])

        target_user = await user_collection.find_one({'id': target_user_id})
        if not target_user:
            await update.message.reply_text("User not found")
            return

        pass_data = target_user.get('pass_data', {})
        pending = pass_data.get('pending_elite_payment')

        if not pending:
            await update.message.reply_text("No pending payment for this user")
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
            f"ELITE PASS ACTIVATED\n\n"
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
                    f"Your elite pass has been activated!\n\n"
                    f"<b>RECEIVED:</b>\n"
                    f"Gold Coins: <code>{activation_bonus:,}</code>\n"
                    f"Mythic Characters: {len(mythic_chars)}\n"
                    f"Expires: {expires.strftime('%Y-%m-%d')}\n\n"
                    f"Enjoy your benefits!"
                ),
                parse_mode='HTML'
            )
        except Exception as e:
            LOGGER.error(f"[PASS] Could not notify user {target_user_id}: {e}")

        LOGGER.info(f"[PASS] Elite pass approved for user {target_user_id}")

    except ValueError:
        await update.message.reply_text("Invalid user ID")
    except Exception as e:
        LOGGER.error(f"[PASS APPROVE ERROR] {e}")
        await update.message.reply_text("Error processing approval")


async def pass_callback(update: Update, context: CallbackContext) -> None:
    """Handle pass button callbacks"""
    query = update.callback_query
    user_id = query.from_user.id

    try:
        data = query.data
        
        if data == "pass_claim":
            update.callback_query = query
            await pclaim_command(update, context)
            
        elif data == "pass_tasks":
            update.callback_query = query
            await tasks_command(update, context)
            
        elif data == "pass_upgrade":
            update.callback_query = query
            await upgrade_command(update, context)
            
        elif data == "pass_invite":
            update.callback_query = query
            await invite_command(update, context)
            
        elif data == "pass_back":
            await query.answer()
            
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
                    tier_status = f"ELITE ({days_left} days)"
            elif tier == 'premium':
                premium_expires = pass_data.get('premium_expires')
                if premium_expires and isinstance(premium_expires, datetime):
                    days_left = (premium_expires - datetime.utcnow()).days
                    tier_status = f"PREMIUM ({days_left} days)"

            mythic_status = "UNLOCKED" if mythic_unlocked else "LOCKED"

            caption = f"""<b>{tier_name}</b>

USER: {escape(query.from_user.first_name)}
ID: <code>{user_id}</code>
BALANCE: <code>{balance:,}</code>

<b>PROGRESS</b>
Weekly Claims: {weekly_claims}/6
Streak: {streak_count} weeks
Tasks: {completed_tasks}/{total_tasks}
Mythic: {mythic_status}

<b>REWARDS</b>
Weekly: {PASS_CONFIG[tier]['weekly_reward']:,}
Streak Bonus: {PASS_CONFIG[tier]['streak_bonus']:,}
Status: {tier_status}

<b>COMMANDS</b>
/pclaim - Claim weekly reward
/sweekly - Claim streak bonus
/tasks - View tasks
/upgrade - Upgrade pass
/invite - Invite friends
"""

            keyboard = [
                [
                    InlineKeyboardButton("CLAIM", callback_data="pass_claim"),
                    InlineKeyboardButton("TASKS", callback_data="pass_tasks")
                ],
                [
                    InlineKeyboardButton("UPGRADE", callback_data="pass_upgrade"),
                    InlineKeyboardButton("INVITE", callback_data="pass_invite")
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
            
        elif data == "pass_buy_premium":
            await query.answer()
            
            user = await user_collection.find_one({'id': user_id})
            cost = PASS_CONFIG['premium']['cost']
            balance = user.get('balance', 0)

            if balance < cost:
                await query.answer("Insufficient balance", show_alert=True)
                return

            caption = f"""<b>CONFIRM PREMIUM PURCHASE</b>

Cost: <code>{cost:,}</code> gold
Your Balance: <code>{balance:,}</code>

<b>BENEFITS:</b>
• Weekly Reward: 5,000
• Streak Bonus: 25,000
• Mythic Chars: 3 per claim

Confirm purchase?
"""

            keyboard = [
                [
                    InlineKeyboardButton("CONFIRM", callback_data="pass_confirm_premium"),
                    InlineKeyboardButton("CANCEL", callback_data="pass_cancel")
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
                
        elif data == "pass_buy_elite":
            await query.answer()
            
            upi_id = PASS_CONFIG['elite']['upi_id']
            cost_inr = PASS_CONFIG['elite']['cost_inr']

            caption = f"""<b>ELITE PASS PAYMENT</b>

<b>PAYMENT DETAILS:</b>
Amount: ₹{cost_inr}
UPI ID: <code>{upi_id}</code>

<b>INSTRUCTIONS:</b>
1. Send ₹{cost_inr} to the UPI ID above
2. Take a screenshot of payment
3. Click Submit Payment below
4. Owner will verify and activate

<b>BENEFITS:</b>
Activation Bonus: 100,000,000 gold
Instant Mythics: 10 characters
• Weekly Reward: 15,000
• Streak Bonus: 100,000
• Mythic per Claim: 10
"""

            keyboard = [
                [InlineKeyboardButton("SUBMIT PAYMENT", callback_data="pass_submit_elite")],
                [InlineKeyboardButton("CANCEL", callback_data="pass_cancel")]
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
                
        elif data == "pass_confirm_premium":
            await query.answer()
            
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

Premium pass activated successfully!
Expires: {expires.strftime('%Y-%m-%d')}

<b>YOUR BENEFITS:</b>
• Weekly Reward: 5,000
• Streak Bonus: 25,000
• Mythic Chars: 3 per claim

Enjoy your benefits!
"""

            keyboard = [[InlineKeyboardButton("BACK TO PASS", callback_data="pass_back")]]

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

            LOGGER.info(f"[PASS] User {user_id} upgraded to premium")
            
        elif data == "pass_submit_elite":
            await query.answer()
            
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
                        f"Amount: ₹10\n\n"
                        f"Verify payment and use:\n"
                        f"<code>/approveelite {user_id}</code>"
                    ),
                    parse_mode='HTML'
                )
            except Exception as e:
                LOGGER.error(f"[PASS] Could not notify owner: {e}")

            caption = f"""<b>PAYMENT SUBMITTED</b>

Your payment request has been submitted!

Owner will verify and activate your elite pass within 24 hours.

You will receive a notification once activated.

<b>YOU WILL RECEIVE:</b>
• 100,000,000 gold
• 10 mythic characters
"""

            keyboard = [[InlineKeyboardButton("BACK TO PASS", callback_data="pass_back")]]

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

            LOGGER.info(f"[PASS] User {user_id} submitted elite payment")
            
        elif data == "pass_cancel":
            await query.answer("Cancelled", show_alert=False)
            update.callback_query = query
            await upgrade_command(update, context)

    except Exception as e:
        LOGGER.error(f"[PASS CALLBACK ERROR] {e}")
        await query.answer("Error processing request", show_alert=True)


# Register handlers
application.add_handler(CommandHandler("pass", pass_command, block=False))
application.add_handler(CommandHandler("pclaim", pclaim_command, block=False))
application.add_handler(CommandHandler("sweekly", sweekly_command, block=False))
application.add_handler(CommandHandler("tasks", tasks_command, block=False))
application.add_handler(CommandHandler("upgrade", upgrade_command, block=False))
application.add_handler(CommandHandler("invite", invite_command, block=False))
application.add_handler(CommandHandler("approveelite", approve_elite_command, block=False))
application.add_handler(CallbackQueryHandler(pass_callback, pattern=r"^pass_", block=False))

LOGGER.info("[PASS] Module loaded successfully")tasks")
                ],
                [
                    InlineKeyboardButton("UPGRADE", callback_data="pass_