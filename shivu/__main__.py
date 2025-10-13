import importlib
import time
import random
import re
import asyncio
from html import escape
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, CallbackQueryHandler, filters
from telegram.error import BadRequest, Forbidden

from shivu import (
    db,
    shivuu,
    application, 
    LOGGER
)
from shivu.modules import ALL_MODULES

# Database collections
collection = db['anime_characters_lol']
user_collection = db['user_collection_lmaoooo']
user_totals_collection = db['user_totals_lmaoooo']
group_user_totals_collection = db['group_user_totalsssssss']
top_global_groups_collection = db['top_global_groups']

# Global dictionaries for tracking
locks = {}
message_counters = {}
spam_counters = {}
last_characters = {}
sent_characters = {}
first_correct_guesses = {}
message_counts = {}
last_user = {}
warned_users = {}

# Default spawn frequency
DEFAULT_MESSAGE_FREQUENCY = 70

# Import all modules
for module_name in ALL_MODULES:
    try:
        imported_module = importlib.import_module("shivu.modules." + module_name)
        LOGGER.info(f"Successfully imported module: {module_name}")
    except Exception as e:
        LOGGER.error(f"Failed to import module {module_name}: {e}")


def escape_markdown(text):
    """Escape markdown special characters"""
    escape_chars = r'\*_`\\~>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)


async def message_counter(update: Update, context: CallbackContext) -> None:
    """Count messages and spawn characters at intervals"""
    # Ignore non-group messages
    if update.effective_chat.type not in ['group', 'supergroup']:
        return
    
    # Ignore bot messages and commands
    if not update.message or not update.message.text:
        return
    
    if update.message.text.startswith('/'):
        return
    
    chat_id = str(update.effective_chat.id)
    user_id = update.effective_user.id

    # Initialize lock for this chat
    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()
    lock = locks[chat_id]

    async with lock:
        # Get message frequency from database or use default
        try:
            chat_frequency = await user_totals_collection.find_one({'chat_id': chat_id})
            if chat_frequency:
                message_frequency = chat_frequency.get('message_frequency', DEFAULT_MESSAGE_FREQUENCY)
            else:
                message_frequency = DEFAULT_MESSAGE_FREQUENCY
                # Initialize chat settings in database
                await user_totals_collection.insert_one({
                    'chat_id': chat_id,
                    'message_frequency': DEFAULT_MESSAGE_FREQUENCY
                })
        except Exception as e:
            LOGGER.error(f"Error fetching chat frequency: {e}")
            message_frequency = DEFAULT_MESSAGE_FREQUENCY

        # Anti-spam check
        if chat_id in last_user and last_user[chat_id]['user_id'] == user_id:
            last_user[chat_id]['count'] += 1
            if last_user[chat_id]['count'] >= 10:
                # Check if user was recently warned
                if user_id in warned_users and time.time() - warned_users[user_id] < 600:
                    return
                else:
                    try:
                        await update.message.reply_text(
                            f"⚠️ 𝘿𝙤𝙣'𝙩 𝙎𝙥𝙖𝙢 {escape(update.effective_user.first_name)}...\n"
                            "𝙔𝙤𝙪𝙧 𝙈𝙚𝙨𝙨𝙖𝙜𝙚𝙨 𝙒𝙞𝙡𝙡 𝙗𝙚 𝙞𝙜𝙣𝙤𝙧𝙚𝙙 𝙛𝙤𝙧 10 𝙈𝙞𝙣𝙪𝙩𝙚𝙨..."
                        )
                    except Exception as e:
                        LOGGER.error(f"Error sending spam warning: {e}")
                    warned_users[user_id] = time.time()
                    return
        else:
            last_user[chat_id] = {'user_id': user_id, 'count': 1}

        # Increment message count
        if chat_id not in message_counts:
            message_counts[chat_id] = 0
        
        message_counts[chat_id] += 1

        # Check if it's time to spawn
        if message_counts[chat_id] >= message_frequency:
            await send_image(update, context)
            message_counts[chat_id] = 0


async def send_image(update: Update, context: CallbackContext) -> None:
    """Send a random character image to the chat"""
    chat_id = update.effective_chat.id

    try:
        # Fetch all characters
        all_characters = list(await collection.find({}).to_list(length=None))
        
        if not all_characters:
            LOGGER.error("No characters found in database")
            return

        # Initialize sent characters list for this chat
        if chat_id not in sent_characters:
            sent_characters[chat_id] = []

        # Reset if all characters have been sent
        if len(sent_characters[chat_id]) >= len(all_characters):
            sent_characters[chat_id] = []

        # Filter characters that haven't been sent yet
        available_characters = [
            c for c in all_characters 
            if 'id' in c and c.get('id') not in sent_characters[chat_id]
        ]

        if not available_characters:
            available_characters = all_characters
            sent_characters[chat_id] = []

        # Select random character
        character = random.choice(available_characters)

        # Mark character as sent
        sent_characters[chat_id].append(character['id'])
        last_characters[chat_id] = character

        # Clear previous guess tracker
        if chat_id in first_correct_guesses:
            del first_correct_guesses[chat_id]

        # Get rarity emoji
        rarity = character.get('rarity', '🟢 Common')
        if isinstance(rarity, str):
            rarity_emoji = rarity.split(' ')[0] if ' ' in rarity else '🟢'
        else:
            rarity_emoji = '🟢'

        # Send character image
        caption = (
            f"***{rarity_emoji} ʟᴏᴏᴋ ᴀ ᴡᴀɪғᴜ ʜᴀꜱ ꜱᴘᴀᴡɴᴇᴅ !! "
            f"ᴍᴀᴋᴇ ʜᴇʀ ʏᴏᴜʀ'ꜱ ʙʏ ɢɪᴠɪɴɢ\n/grab 𝚆𝚊𝚒𝚏𝚞 𝚗𝚊𝚖𝚎***"
        )

        await context.bot.send_photo(
            chat_id=chat_id,
            photo=character['img_url'],
            caption=caption,
            parse_mode='Markdown'
        )
        
        LOGGER.info(f"Character spawned in chat {chat_id}: {character.get('name', 'Unknown')}")

    except Exception as e:
        LOGGER.error(f"Error sending character image: {e}")


async def guess(update: Update, context: CallbackContext) -> None:
    """Handle character guessing"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Check if there's an active character
    if chat_id not in last_characters:
        return

    # Check if already guessed
    if chat_id in first_correct_guesses:
        await update.message.reply_text(
            '🚫 𝙒ᴀɪғᴜ ᴀʟʀᴇᴀᴅʏ ɢʀᴀʙʙᴇᴅ ʙʏ 𝙨ᴏᴍᴇᴏɴᴇ ᴇʟ𝙨ᴇ ⚡, '
            '𝘽ᴇᴛᴛᴇʀ 𝙇ᴜᴄᴋ 𝙉ᴇ𝙭ᴛ 𝙏ɪᴍᴇ'
        )
        return

    # Get user's guess
    guess_text = ' '.join(context.args).lower() if context.args else ''

    # Validate guess
    if not guess_text:
        await update.message.reply_text('𝙋𝙡𝙚𝙖𝙨𝙚 𝙥𝙧𝙤𝙫𝙞𝙙𝙚 𝙖 𝙣𝙖𝙢𝙚!')
        return

    if "()" in guess_text or "&" in guess_text:
        await update.message.reply_text("𝙉𝙖𝙝𝙝 𝙔𝙤𝙪 𝘾𝙖𝙣'𝙩 𝙪𝙨𝙚 𝙏𝙝𝙞𝙨 𝙏𝙮𝙥𝙚𝙨 𝙤𝙛 𝙬𝙤𝙧𝙙𝙨 ❌️")
        return

    # Get character name parts
    character_name = last_characters[chat_id].get('name', '').lower()
    name_parts = character_name.split()

    # Check if guess matches
    is_correct = (
        sorted(name_parts) == sorted(guess_text.split()) or 
        any(part == guess_text for part in name_parts) or
        guess_text == character_name
    )

    if is_correct:
        # Mark as guessed
        first_correct_guesses[chat_id] = user_id

        try:
            # Update or create user
            user = await user_collection.find_one({'id': user_id})
            if user:
                update_fields = {}
                if hasattr(update.effective_user, 'username') and update.effective_user.username:
                    if update.effective_user.username != user.get('username'):
                        update_fields['username'] = update.effective_user.username
                if update.effective_user.first_name != user.get('first_name'):
                    update_fields['first_name'] = update.effective_user.first_name
                
                if update_fields:
                    await user_collection.update_one({'id': user_id}, {'$set': update_fields})

                await user_collection.update_one(
                    {'id': user_id}, 
                    {'$push': {'characters': last_characters[chat_id]}}
                )
            else:
                await user_collection.insert_one({
                    'id': user_id,
                    'username': getattr(update.effective_user, 'username', None),
                    'first_name': update.effective_user.first_name,
                    'characters': [last_characters[chat_id]],
                })

            # Update group user totals
            group_user_total = await group_user_totals_collection.find_one({
                'user_id': user_id, 
                'group_id': chat_id
            })
            
            if group_user_total:
                update_fields = {}
                if hasattr(update.effective_user, 'username') and update.effective_user.username:
                    if update.effective_user.username != group_user_total.get('username'):
                        update_fields['username'] = update.effective_user.username
                if update.effective_user.first_name != group_user_total.get('first_name'):
                    update_fields['first_name'] = update.effective_user.first_name
                
                if update_fields:
                    await group_user_totals_collection.update_one(
                        {'user_id': user_id, 'group_id': chat_id}, 
                        {'$set': update_fields}
                    )

                await group_user_totals_collection.update_one(
                    {'user_id': user_id, 'group_id': chat_id}, 
                    {'$inc': {'count': 1}}
                )
            else:
                await group_user_totals_collection.insert_one({
                    'user_id': user_id,
                    'group_id': chat_id,
                    'username': getattr(update.effective_user, 'username', None),
                    'first_name': update.effective_user.first_name,
                    'count': 1,
                })

            # Update group totals
            group_info = await top_global_groups_collection.find_one({'group_id': chat_id})
            if group_info:
                update_fields = {}
                if update.effective_chat.title != group_info.get('group_name'):
                    update_fields['group_name'] = update.effective_chat.title
                
                if update_fields:
                    await top_global_groups_collection.update_one(
                        {'group_id': chat_id}, 
                        {'$set': update_fields}
                    )

                await top_global_groups_collection.update_one(
                    {'group_id': chat_id}, 
                    {'$inc': {'count': 1}}
                )
            else:
                await top_global_groups_collection.insert_one({
                    'group_id': chat_id,
                    'group_name': update.effective_chat.title,
                    'count': 1,
                })

            # Send success message
            character = last_characters[chat_id]
            keyboard = [[
                InlineKeyboardButton(
                    "🪼 ʜᴀʀᴇᴍ", 
                    switch_inline_query_current_chat=f"collection.{user_id}"
                )
            ]]

            # Get rarity properly
            rarity = character.get('rarity', '🟢 Common')
            if isinstance(rarity, str):
                rarity_parts = rarity.split(' ', 1)
                rarity_emoji = rarity_parts[0] if len(rarity_parts) > 0 else '🟢'
                rarity_text = rarity_parts[1] if len(rarity_parts) > 1 else 'Common'
            else:
                rarity_emoji = '🟢'
                rarity_text = 'Common'

            success_message = (
                f'<b><a href="tg://user?id={user_id}">{escape(update.effective_user.first_name)}</a></b> '
                f'Congratulations 🎊 You grabbed a new Waifu !!✅\n\n'
                f'🎀 𝙉𝙖𝙢𝙚: <code>{character.get("name", "Unknown")}</code>\n'
                f'⚡ 𝘼𝙣𝙞𝙢𝙚: <code>{character.get("anime", "Unknown")}</code>\n'
                f'{rarity_emoji} 𝙍𝙖𝙧𝙞𝙩𝙮: <code>{rarity_text}</code>\n\n'
                f'✧⁠ Character successfully added in your harem'
            )

            await update.message.reply_text(
                success_message,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            LOGGER.error(f"Error processing correct guess: {e}")
            await update.message.reply_text('An error occurred while processing your guess.')
    else:
        await update.message.reply_text('𝙋𝙡𝙚𝙖𝙨𝙚 𝙒𝙧𝙞𝙩𝙚 𝘾𝙤𝙧𝙧𝙚𝙘𝙩 𝙉𝙖𝙢𝙚... ❌️')


async def fav(update: Update, context: CallbackContext) -> None:
    """Set a character as favorite"""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text('𝙋𝙡𝙚𝙖𝙨𝙚 𝙥𝙧𝙤𝙫𝙞𝙙𝙚 𝙒𝘼𝙄𝙁𝙐 𝙞𝙙...')
        return

    character_id = str(context.args[0])  # Convert to string

    try:
        # Find the user in the database
        user = await user_collection.find_one({'id': user_id})
        if not user:
            await update.message.reply_text('𝙔𝙤𝙪 𝙝𝙖𝙫𝙚 𝙣𝙤𝙩 𝙂𝙤𝙩 𝘼𝙣𝙮 𝙒𝘼𝙄𝙁𝙐 𝙮𝙚𝙩...')
            return

        # Find the waifu in the user's character list (compare as strings)
        character = next(
            (c for c in user.get('characters', []) if str(c.get('id')) == character_id),
            None
        )
        
        if not character:
            await update.message.reply_text('𝙏𝙝𝙞𝙨 𝙒𝘼𝙄𝙁𝙐 𝙞𝙨 𝙉𝙤𝙩 𝙄𝙣 𝙮𝙤𝙪𝙧 𝙒𝘼𝙄𝙁𝙐 𝙡𝙞𝙨𝙩')
            return

        # Create inline buttons for confirmation
        buttons = [
            [
                InlineKeyboardButton("✅ Yes", callback_data=f"fav_yes_{character_id}_{user_id}"),
                InlineKeyboardButton("❌ No", callback_data=f"fav_no_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)

        # Send message with buttons and waifu details
        await update.message.reply_photo(
            photo=character.get("img_url", ""),
            caption=(
                f"<b>💖 Do you want to make this waifu your favorite?</b>\n\n"
                f"✨ <b>Name:</b> <code>{character.get('name', 'Unknown')}</code>\n"
                f"📺 <b>Anime:</b> <code>{character.get('anime', 'Unknown')}</code>\n"
                f"🆔 <b>ID:</b> <code>{character.get('id', 'Unknown')}</code>"
            ),
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    except Exception as e:
        LOGGER.error(f"Error in fav command: {e}")
        await update.message.reply_text('An error occurred while processing your request.')


async def handle_fav_callback(update: Update, context: CallbackContext) -> None:
    """Handle favorite button callbacks"""
    query = update.callback_query
    
    try:
        await query.answer()
        
        # Parse callback data
        data_parts = query.data.split('_')
        action = data_parts[1]  # 'yes' or 'no'
        
        if action == 'yes':
            character_id = str(data_parts[2])  # Convert to string
            user_id = int(data_parts[3])
            
            # Verify the user clicking is the same user who requested
            if query.from_user.id != user_id:
                await query.answer("⚠️ This is not your request!", show_alert=True)
                return
            
            # Update the user's favorite (store as string with upsert)
            result = await user_collection.update_one(
                {'id': user_id},
                {'$set': {'favorites': character_id}},  # Store as string
                upsert=True
            )
            
            if result.modified_count > 0 or result.upserted_id:
                await query.edit_message_caption(
                    caption=(
                        f"<b>✅ Success!</b>\n\n"
                        f"💖 Waifu marked as your favorite!\n"
                        f"🆔 Character ID: <code>{character_id}</code>\n\n"
                        f"<i>Your favorite will be shown in inline queries!</i>"
                    ),
                    parse_mode='HTML'
                )
            else:
                await query.edit_message_caption(
                    caption="❌ Failed to set favorite. Please try again.",
                    parse_mode='HTML'
                )
                
        elif action == 'no':
            user_id = int(data_parts[2])
            
            # Verify the user clicking is the same user who requested
            if query.from_user.id != user_id:
                await query.answer("⚠️ This is not your request!", show_alert=True)
                return
            
            await query.edit_message_caption(
                caption="❌ Action canceled. No changes made.",
                parse_mode='HTML'
            )
            
    except Exception as e:
        LOGGER.error(f"Error in fav callback: {e}")
        try:
            await query.edit_message_caption(
                caption="❌ An error occurred. Please try again.",
                parse_mode='HTML'
            )
        except:
            await query.answer("❌ Error occurred", show_alert=True)


def main() -> None:
    """Run bot"""
    try:
        # Add command handlers
        application.add_handler(CommandHandler(["grab", "g"], guess, block=False))
        application.add_handler(CommandHandler('fav', fav, block=False))
        
        # Add callback handlers with specific patterns
        application.add_handler(CallbackQueryHandler(handle_fav_callback, pattern="^fav_", block=False))

        # Add message handler (should be last)
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            message_counter, 
            block=False
        ))

        LOGGER.info("All handlers registered successfully")
        
        # Start polling
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        
    except Exception as e:
        LOGGER.error(f"Error in main: {e}")
        raise


if __name__ == "__main__":
    try:
        # Start the client
        shivuu.start()
        LOGGER.info("Shivuu client started successfully")
        
        # Run the bot
        main()
        
    except KeyboardInterrupt:
        LOGGER.info("Bot stopped by user")
    except Exception as e:
        LOGGER.error(f"Fatal error: {e}")
        raise
    finally:
        try:
            shivuu.stop()
            LOGGER.info("Shivuu client stopped")
        except:
            pass