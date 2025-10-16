from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from html import escape
import random

from shivu import application, user_collection, collection, LOGGER

# Pass configuration
PASS_CONFIG = {
    'free': {
        'name': 'ғʀᴇᴇ ᴘᴀss',
        'weekly_reward': 1000,
        'streak_bonus': 5000,
        'mythic_unlock': True
    },
    'premium': {
        'name': 'ᴘʀᴇᴍɪᴜᴍ ᴘᴀss',
        'weekly_reward': 2500,
        'streak_bonus': 15000,
        'mythic_unlock': True,
        'extra_characters': 2,
        'cost': 50000
    }
}

# Task requirements
MYTHIC_TASKS = {
    'invites': {'required': 5, 'reward': 'ᴍʏᴛʜɪᴄ ᴄʜᴀʀᴀᴄᴛᴇʀ'},
    'weekly_claims': {'required': 4, 'reward': 'ʙᴏɴᴜs ʀᴇᴡᴀʀᴅ'},
    'battles': {'required': 10, 'reward': 'ʙᴀᴛᴛʟᴇ ᴍᴀsᴛᴇʀ'},
    'grabs': {'required': 50, 'reward': 'ᴄᴏʟʟᴇᴄᴛᴏʀ'}
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
        # Create new user
        user = {
            'id': user_id,
            'characters': [],
            'balance': 0
        }
        await user_collection.insert_one(user)
    
    # Initialize pass data if not exists
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
                'battles': 0,
                'grabs': 0
            },
            'mythic_unlocked': False,
            'premium_expires': None
        }
        await user_collection.update_one(
            {'id': user_id},
            {'$set': {'pass_data': pass_data}}
        )
        return pass_data
    
    return user.get('pass_data', {})


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
        
        # Calculate task completion
        total_tasks = len(MYTHIC_TASKS)
        completed_tasks = sum(1 for task_key, task_info in MYTHIC_TASKS.items() 
                             if tasks.get(task_key, 0) >= task_info['required'])
        
        # Check premium status
        premium_status = to_small_caps("no")
        if tier == 'premium':
            premium_expires = pass_data.get('premium_expires')
            if premium_expires and isinstance(premium_expires, datetime):
                if premium_expires > datetime.utcnow():
                    days_left = (premium_expires - datetime.utcnow()).days
                    premium_status = to_small_caps(f"active") + f" ({days_left} " + to_small_caps("days") + ")"
                else:
                    premium_status = to_small_caps("expired")
        
        mythic_status = to_small_caps("unlocked") if mythic_unlocked else to_small_caps("locked")
        
        # Build message
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
{to_small_caps('rewards')}
━━━━━━━━━━━━━━━━━━━
{to_small_caps('weekly')}: {PASS_CONFIG[tier]['weekly_reward']:,}
{to_small_caps('streak bonus')}: {PASS_CONFIG[tier]['streak_bonus']:,}
{to_small_caps('premium')}: {premium_status}

━━━━━━━━━━━━━━━━━━━
{to_small_caps('commands')}
━━━━━━━━━━━━━━━━━━━
/pclaim {to_small_caps('weekly reward')}
/sweekly {to_small_caps('streak bonus')}
/tasks {to_small_caps('view tasks')}
/upgrade {to_small_caps('get premium')}

{to_small_caps('complete tasks to unlock mythic character')}
"""
        
        # Create buttons
        keyboard = [
            [
                InlineKeyboardButton(to_small_caps("claim"), callback_data=f"pass_claim_{user_id}"),
                InlineKeyboardButton(to_small_caps("tasks"), callback_data=f"pass_tasks_{user_id}")
            ],
            [
                InlineKeyboardButton(to_small_caps("upgrade"), callback_data=f"pass_upgrade_{user_id}"),
                InlineKeyboardButton(to_small_caps("help"), callback_data=f"pass_help_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send with image
        await update.message.reply_photo(
            photo="https://telegra.ph/file/e714526fdc85b8800e1de.jpg",
            caption=caption,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        LOGGER.info(f"[PASS] Status shown for user {user_id}")
        
    except Exception as e:
        LOGGER.error(f"[PASS ERROR] {e}")
        await update.message.reply_text(to_small_caps('error loading pass data'))


async def claim_command(update: Update, context: CallbackContext) -> None:
    """Claim weekly reward"""
    user_id = update.effective_user.id
    
    try:
        pass_data = await get_or_create_pass_data(user_id)
        user = await user_collection.find_one({'id': user_id})
        
        # Check last claim
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
        
        # Update user
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
        
        # Check streak
        last_streak = pass_data.get('last_streak_claim')
        if last_streak and isinstance(last_streak, datetime):
            days_since = (datetime.utcnow() - last_streak).days
            if 6 <= days_since <= 8:
                # Maintain streak
                await user_collection.update_one(
                    {'id': user_id},
                    {
                        '$inc': {'pass_data.streak_count': 1},
                        '$set': {'pass_data.last_streak_claim': datetime.utcnow()}
                    }
                )
            elif days_since > 8:
                # Reset streak
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
        
        # Premium bonus
        premium_msg = ""
        if tier == 'premium':
            extra_chars = PASS_CONFIG['premium'].get('extra_characters', 2)
            mythic_chars = await collection.find({'rarity': '🏵 Mythic'}).limit(extra_chars).to_list(length=extra_chars)
            
            if mythic_chars:
                await user_collection.update_one(
                    {'id': user_id},
                    {'$push': {'characters': {'$each': mythic_chars}}}
                )
                premium_msg = f"\n\n{to_small_caps('premium bonus')}: 2 {to_small_caps('mythic characters')}"
        
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
        
        # Award bonus
        await user_collection.update_one(
            {'id': user_id},
            {
                '$inc': {'balance': bonus},
                '$set': {'pass_data.weekly_claims': 0}
            }
        )
        
        await update.message.reply_text(
            f"{to_small_caps('streak bonus claimed')}\n\n"
            f"{to_small_caps('bonus')}: <code>{bonus:,}</code>\n"
            f"{to_small_caps('weekly claims reset to')} 0",
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
        for task_key, task_info in MYTHIC_TASKS.items():
            current = tasks.get(task_key, 0)
            required = task_info['required']
            reward = task_info['reward']
            progress = min(100, int((current / required) * 100))
            status = to_small_caps("completed") if current >= required else to_small_caps("in progress")
            
            task_list.append(
                f"<b>{to_small_caps(task_key.replace('_', ' '))}:</b> {current}/{required}\n"
                f"   {'█' * (progress // 10)}{'░' * (10 - progress // 10)} {progress}%\n"
                f"   {to_small_caps('reward')}: {reward}\n"
                f"   {to_small_caps('status')}: {status}"
            )
        
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
        
        # Check if it's a callback query or command
        if hasattr(update, 'callback_query') and update.callback_query:
            try:
                media = InputMediaPhoto(
                    media="https://telegra.ph/file/e714526fdc85b8800e1de.jpg",
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
                photo="https://telegra.ph/file/e714526fdc85b8800e1de.jpg",
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
    """Upgrade to premium pass"""
    user_id = update.effective_user.id
    
    try:
        pass_data = await get_or_create_pass_data(user_id)
        user = await user_collection.find_one({'id': user_id})
        
        tier = pass_data.get('tier', 'free')
        if tier == 'premium':
            expires = pass_data.get('premium_expires')
            if expires and isinstance(expires, datetime) and expires > datetime.utcnow():
                days_left = (expires - datetime.utcnow()).days
                msg = (
                    f"{to_small_caps('you already have premium')}\n"
                    f"{to_small_caps('expires in')}: {days_left} {to_small_caps('days')}"
                )
                
                if hasattr(update, 'callback_query') and update.callback_query:
                    await update.callback_query.answer(msg, show_alert=True)
                else:
                    await update.message.reply_text(msg)
                return
        
        cost = PASS_CONFIG['premium']['cost']
        balance = user.get('balance', 0)
        
        if balance < cost:
            msg = (
                f"{to_small_caps('insufficient balance')}\n\n"
                f"{to_small_caps('required')}: <code>{cost:,}</code>\n"
                f"{to_small_caps('your balance')}: <code>{balance:,}</code>\n"
                f"{to_small_caps('needed')}: <code>{cost - balance:,}</code>"
            )
            
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.answer(to_small_caps('insufficient balance'), show_alert=True)
                await update.callback_query.message.reply_text(msg, parse_mode='HTML')
            else:
                await update.message.reply_text(msg, parse_mode='HTML')
            return
        
        # Show confirmation
        keyboard = [[
            InlineKeyboardButton(to_small_caps("confirm"), callback_data=f"pass_buy_{user_id}"),
            InlineKeyboardButton(to_small_caps("cancel"), callback_data=f"pass_cancel_{user_id}")
        ]]
        
        caption = (
            f"╔═══════════════════╗\n"
            f"  {to_small_caps('upgrade to premium')}\n"
            f"╚═══════════════════╝\n\n"
            f"<b>{to_small_caps('premium benefits')}:</b>\n"
            f"{to_small_caps('weekly rewards')}: 2.5x\n"
            f"{to_small_caps('streak bonus')}: 3x\n"
            f"{to_small_caps('free mythic characters')}: 2 {to_small_caps('per claim')}\n"
            f"{to_small_caps('priority support')}\n\n"
            f"{to_small_caps('cost')}: <code>{cost:,}</code>\n"
            f"{to_small_caps('duration')}: 30 {to_small_caps('days')}\n\n"
            f"{to_small_caps('confirm purchase')}"
        )
        
        # Check if it's a callback query or command
        if hasattr(update, 'callback_query') and update.callback_query:
            try:
                media = InputMediaPhoto(
                    media="https://telegra.ph/file/e714526fdc85b8800e1de.jpg",
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
                photo="https://telegra.ph/file/e714526fdc85b8800e1de.jpg",
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        
        LOGGER.info(f"[PASS] Upgrade confirmation shown for user {user_id}")
        
    except Exception as e:
        LOGGER.error(f"[PASS UPGRADE ERROR] {e}")
        error_msg = to_small_caps('error loading upgrade')
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.answer(error_msg, show_alert=True)
        else:
            await update.message.reply_text(error_msg)


async def pass_callback(update: Update, context: CallbackContext) -> None:
    """Handle pass button callbacks"""
    query = update.callback_query
    
    try:
        await query.answer()
        
        data = query.data
        if not data.startswith('pass_'):
            return
        
        parts = data.split('_')
        action = parts[1]
        user_id = int(parts[2])
        
        # Verify user
        if query.from_user.id != user_id:
            await query.answer(to_small_caps("not your request"), show_alert=True)
            return
        
        if action == 'claim':
            # Trigger claim
            update.callback_query = query
            await claim_command(update, context)
            
        elif action == 'tasks':
            # Show tasks
            update.callback_query = query
            await tasks_command(update, context)
            
        elif action == 'upgrade':
            # Show upgrade
            update.callback_query = query
            await upgrade_command(update, context)
            
        elif action == 'help':
            # Show help
            help_text = (
                f"╔═══════════════════╗\n"
                f"  {to_small_caps('pass help')}\n"
                f"╚═══════════════════╝\n\n"
                f"<b>{to_small_caps('commands')}:</b>\n"
                f"/pass {to_small_caps('view pass status')}\n"
                f"/pclaim {to_small_caps('claim weekly reward')}\n"
                f"/sweekly {to_small_caps('claim streak bonus')}\n"
                f"/tasks {to_small_caps('view task progress')}\n"
                f"/upgrade {to_small_caps('upgrade to premium')}\n\n"
                f"<b>{to_small_caps('how to unlock mythic')}:</b>\n"
                f"1. {to_small_caps('invite 5 people')}\n"
                f"2. {to_small_caps('claim 4 weekly rewards')}\n"
                f"3. {to_small_caps('win 10 battles')}\n"
                f"4. {to_small_caps('grab 50 characters')}\n\n"
                f"{to_small_caps('complete all tasks for free mythic')}"
            )
            
            keyboard = [[
                InlineKeyboardButton(to_small_caps("back"), callback_data=f"pass_back_{user_id}")
            ]]
            
            try:
                media = InputMediaPhoto(
                    media="https://telegra.ph/file/e714526fdc85b8800e1de.jpg",
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
            # Go back to main pass screen
            pass_data = await get_or_create_pass_data(user_id)
            user = await user_collection.find_one({'id': user_id})
            
            tier = pass_data.get('tier', 'free')
            tier_name = PASS_CONFIG[tier]['name']
            weekly_claims = pass_data.get('weekly_claims', 0)
            streak_count = pass_data.get('streak_count', 0)
            tasks = pass_data.get('tasks', {})
            mythic_unlocked = pass_data.get('mythic_unlocked', False)
            balance = user.get('balance', 0)
            
            # Calculate task completion
            total_tasks = len(MYTHIC_TASKS)
            completed_tasks = sum(1 for task_key, task_info in MYTHIC_TASKS.items() 
                                 if tasks.get(task_key, 0) >= task_info['required'])
            
            # Check premium status
            premium_status = to_small_caps("no")
            if tier == 'premium':
                premium_expires = pass_data.get('premium_expires')
                if premium_expires and isinstance(premium_expires, datetime):
                    if premium_expires > datetime.utcnow():
                        days_left = (premium_expires - datetime.utcnow()).days
                        premium_status = to_small_caps(f"active") + f" ({days_left} " + to_small_caps("days") + ")"
                    else:
                        premium_status = to_small_caps("expired")
            
            mythic_status = to_small_caps("unlocked") if mythic_unlocked else to_small_caps("locked")
            
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
{to_small_caps('rewards')}
━━━━━━━━━━━━━━━━━━━
{to_small_caps('weekly')}: {PASS_CONFIG[tier]['weekly_reward']:,}
{to_small_caps('streak bonus')}: {PASS_CONFIG[tier]['streak_bonus']:,}
{to_small_caps('premium')}: {premium_status}

━━━━━━━━━━━━━━━━━━━
{to_small_caps('commands')}
━━━━━━━━━━━━━━━━━━━
/pclaim {to_small_caps('weekly reward')}
/sweekly {to_small_caps('streak bonus')}
/tasks {to_small_caps('view tasks')}
/upgrade {to_small_caps('get premium')}

{to_small_caps('complete tasks to unlock mythic character')}
"""
            
            keyboard = [
                [
                    InlineKeyboardButton(to_small_caps("claim"), callback_data=f"pass_claim_{user_id}"),
                    InlineKeyboardButton(to_small_caps("tasks"), callback_data=f"pass_tasks_{user_id}")
                ],
                [
                    InlineKeyboardButton(to_small_caps("upgrade"), callback_data=f"pass_upgrade_{user_id}"),
                    InlineKeyboardButton(to_small_caps("help"), callback_data=f"pass_help_{user_id}")
                ]
            ]
            
            try:
                media = InputMediaPhoto(
                    media="https://telegra.ph/file/e714526fdc85b8800e1de.jpg",
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
            
        elif action == 'buy':
            # Process premium purchase
            user = await user_collection.find_one({'id': user_id})
            cost = PASS_CONFIG['premium']['cost']
            balance = user.get('balance', 0)
            
            if balance < cost:
                await query.answer(to_small_caps("insufficient balance"), show_alert=True)
                return
            
            # Deduct and upgrade
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
                f"  {to_small_caps('premium activated')}\n"
                f"╚═══════════════════╝\n\n"
                f"{to_small_caps('you are now a premium member')}\n"
                f"{to_small_caps('expires')}: {expires.strftime('%Y-%m-%d')}\n\n"
                f"<b>{to_small_caps('your benefits')}:</b>\n"
                f"{to_small_caps('weekly rewards')}: 2.5x\n"
                f"{to_small_caps('streak bonus')}: 3x\n"
                f"{to_small_caps('free mythic characters')}: 2 {to_small_caps('per claim')}\n\n"
                f"{to_small_caps('enjoy your benefits')}"
            )
            
            keyboard = [[
                InlineKeyboardButton(to_small_caps("back to pass"), callback_data=f"pass_back_{user_id}")
            ]]
            
            try:
                media = InputMediaPhoto(
                    media="https://telegra.ph/file/e714526fdc85b8800e1de.jpg",
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
            
            await query.answer(to_small_caps("premium activated successfully"), show_alert=False)
            LOGGER.info(f"[PASS] User {user_id} upgraded to premium")
            
        elif action == 'cancel':
            # Cancel premium purchase, go back to main screen
            await query.answer(to_small_caps("purchase cancelled"), show_alert=False)
            
            # Show main pass screen
            pass_data = await get_or_create_pass_data(user_id)
            user = await user_collection.find_one({'id': user_id})
            
            tier = pass_data.get('tier', 'free')
            tier_name = PASS_CONFIG[tier]['name']
            weekly_claims = pass_data.get('weekly_claims', 0)
            streak_count = pass_data.get('streak_count', 0)
            tasks = pass_data.get('tasks', {})
            mythic_unlocked = pass_data.get('mythic_unlocked', False)
            balance = user.get('balance', 0)
            
            # Calculate task completion
            total_tasks = len(MYTHIC_TASKS)
            completed_tasks = sum(1 for task_key, task_info in MYTHIC_TASKS.items() 
                                 if tasks.get(task_key, 0) >= task_info['required'])
            
            # Check premium status
            premium_status = to_small_caps("no")
            if tier == 'premium':
                premium_expires = pass_data.get('premium_expires')
                if premium_expires and isinstance(premium_expires, datetime):
                    if premium_expires > datetime.utcnow():
                        days_left = (premium_expires - datetime.utcnow()).days
                        premium_status = to_small_caps(f"active") + f" ({days_left} " + to_small_caps("days") + ")"
                    else:
                        premium_status = to_small_caps("expired")
            
            mythic_status = to_small_caps("unlocked") if mythic_unlocked else to_small_caps("locked")
            
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
{to_small_caps('rewards')}
━━━━━━━━━━━━━━━━━━━
{to_small_caps('weekly')}: {PASS_CONFIG[tier]['weekly_reward']:,}
{to_small_caps('streak bonus')}: {PASS_CONFIG[tier]['streak_bonus']:,}
{to_small_caps('premium')}: {premium_status}

━━━━━━━━━━━━━━━━━━━
{to_small_caps('commands')}
━━━━━━━━━━━━━━━━━━━
/claim {to_small_caps('weekly reward')}
/sweekly {to_small_caps('streak bonus')}
/tasks {to_small_caps('view tasks')}
/upgrade {to_small_caps('get premium')}

{to_small_caps('complete tasks to unlock mythic character')}
"""
            
            keyboard = [
                [
                    InlineKeyboardButton(to_small_caps("claim"), callback_data=f"pass_claim_{user_id}"),
                    InlineKeyboardButton(to_small_caps("tasks"), callback_data=f"pass_tasks_{user_id}")
                ],
                [
                    InlineKeyboardButton(to_small_caps("upgrade"), callback_data=f"pass_upgrade_{user_id}"),
                    InlineKeyboardButton(to_small_caps("help"), callback_data=f"pass_help_{user_id}")
                ]
            ]
            
            try:
                media = InputMediaPhoto(
                    media="https://telegra.ph/file/e714526fdc85b8800e1de.jpg",
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
        
    except Exception as e:
        LOGGER.error(f"[PASS CALLBACK ERROR] {e}")
        await query.answer(to_small_caps('error processing request'), show_alert=True)


# Register handlers
application.add_handler(CommandHandler("pass", pass_command, block=False))
application.add_handler(CommandHandler("pclaim", claim_command, block=False))
application.add_handler(CommandHandler("sweekly", sweekly_command, block=False))
application.add_handler(CommandHandler("tasks", tasks_command, block=False))
application.add_handler(CommandHandler("upgrade", upgrade_command, block=False))
application.add_handler(CallbackQueryHandler(pass_callback, pattern=r"^pass_", block=False))