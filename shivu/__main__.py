import importlib
import time
import random
import asyncio
import traceback
from html import escape
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram.error import BadRequest
from shivu import callback

from shivu import db, shivuu, application, LOGGER
from shivu.modules import ALL_MODULES

collection = db['anime_characters_lol']
user_collection = db['user_collection_lmaoooo']
user_totals_collection = db['user_totals_lmaoooo']
group_user_totals_collection = db['group_user_totalsssssss']
top_global_groups_collection = db['top_global_groups']

DEFAULT_MESSAGE_FREQUENCY = 70
DESPAWN_TIME = 180

locks = {}
message_counts = {}
sent_characters = {}
last_characters = {}
first_correct_guesses = {}
last_user = {}
warned_users = {}
spawn_messages = {}
spawn_message_links = {}

# Import all modules
for module_name in ALL_MODULES:
    try:
        importlib.import_module("shivu.modules." + module_name)
        LOGGER.info(f"Imported: {module_name}")
    except Exception as e:
        LOGGER.error(f"Failed to import {module_name}: {e}")

# Import spawn settings
try:
    from shivu.modules.rarity import spawn_settings_collection, group_rarity_collection, get_spawn_settings, get_group_exclusive
    LOGGER.info("✅ Rarity system loaded")
except Exception as e:
    LOGGER.error(f"Could not import rarity: {e}")
    spawn_settings_collection = None
    group_rarity_collection = None


async def is_character_allowed(character, chat_id=None):
    """Check if character can spawn - Group gets exclusive + global rarities"""
    try:
        if character.get('removed', False):
            return False

        char_rarity = character.get('rarity', '🟢 Common')
        rarity_emoji = char_rarity.split(' ')[0] if isinstance(char_rarity, str) and ' ' in char_rarity else char_rarity

        # Check group exclusivity
        if group_rarity_collection is not None and chat_id:
            try:
                # Check if current group has this as exclusive - ALWAYS ALLOW
                current_group_exclusive = await group_rarity_collection.find_one({
                    'chat_id': chat_id,
                    'rarity_emoji': rarity_emoji
                })
                
                if current_group_exclusive:
                    LOGGER.info(f"Chat {chat_id} allowing exclusive rarity {rarity_emoji}")
                    return True
                
                # Check if this rarity is exclusive to ANOTHER group - BLOCK IT
                other_group_exclusive = await group_rarity_collection.find_one({
                    'rarity_emoji': rarity_emoji,
                    'chat_id': {'$ne': chat_id}
                })
                
                if other_group_exclusive:
                    LOGGER.info(f"Chat {chat_id} blocking {rarity_emoji} (exclusive to {other_group_exclusive['chat_id']})")
                    return False
            except Exception as e:
                LOGGER.error(f"Error checking group exclusivity: {e}")

        # Check global settings for non-exclusive rarities
        if spawn_settings_collection is not None:
            try:
                settings = await get_spawn_settings()
                if settings and settings.get('rarities'):
                    rarities = settings['rarities']
                    if rarity_emoji in rarities:
                        is_enabled = rarities[rarity_emoji].get('enabled', True)
                        if not is_enabled:
                            LOGGER.info(f"Blocking {rarity_emoji} - globally disabled")
                        return is_enabled
            except Exception as e:
                LOGGER.error(f"Error checking global settings: {e}")

        return True
    except Exception as e:
        LOGGER.error(f"Error in is_character_allowed: {e}")
        return True


async def get_chat_message_frequency(chat_id):
    """Get message frequency for chat"""
    try:
        chat_frequency = await user_totals_collection.find_one({'chat_id': chat_id})
        if chat_frequency:
            return chat_frequency.get('message_frequency', DEFAULT_MESSAGE_FREQUENCY)
        await user_totals_collection.insert_one({'chat_id': chat_id, 'message_frequency': DEFAULT_MESSAGE_FREQUENCY})
        return DEFAULT_MESSAGE_FREQUENCY
    except:
        return DEFAULT_MESSAGE_FREQUENCY


async def update_grab_task(user_id: int):
    """Update grab task for user"""
    try:
        user = await user_collection.find_one({'id': user_id})
        if user and 'pass_data' in user:
            await user_collection.update_one({'id': user_id}, {'$inc': {'pass_data.tasks.grabs': 1}})
    except:
        pass


async def despawn_character(chat_id, message_id, character, context):
    """Handle character despawn after timeout"""
    try:
        await asyncio.sleep(DESPAWN_TIME)

        if chat_id in first_correct_guesses:
            last_characters.pop(chat_id, None)
            spawn_messages.pop(chat_id, None)
            spawn_message_links.pop(chat_id, None)
            return

        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except:
            pass

        rarity = character.get('rarity', '🟢 Common')
        rarity_emoji = rarity.split(' ')[0] if isinstance(rarity, str) and ' ' in rarity else '🟢'

        missed_msg = await context.bot.send_photo(
            chat_id=chat_id,
            photo=character['img_url'],
            caption=f"⏰ ᴛɪᴍᴇ's ᴜᴘ!\n{rarity_emoji} ɴᴀᴍᴇ: <b>{character.get('name', 'Unknown')}</b>\n⚡ ᴀɴɪᴍᴇ: <b>{character.get('anime', 'Unknown')}</b>\n💔 ʙᴇᴛᴛᴇʀ ʟᴜᴄᴋ ɴᴇxᴛ ᴛɪᴍᴇ!",
            parse_mode='HTML'
        )

        await asyncio.sleep(10)
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=missed_msg.message_id)
        except:
            pass

        last_characters.pop(chat_id, None)
        spawn_messages.pop(chat_id, None)
        spawn_message_links.pop(chat_id, None)

    except Exception as e:
        LOGGER.error(f"Error in despawn: {e}")


async def message_counter(update: Update, context):
    """Count messages and trigger spawns"""
    try:
        if update.effective_chat.type not in ['group', 'supergroup'] or not update.message or not update.message.text or update.message.text.startswith('/'):
            return

        chat_id = str(update.effective_chat.id)
        user_id = update.effective_user.id

        if chat_id not in locks:
            locks[chat_id] = asyncio.Lock()

        async with locks[chat_id]:
            message_frequency = await get_chat_message_frequency(chat_id)

            if chat_id in last_user and last_user[chat_id]['user_id'] == user_id:
                last_user[chat_id]['count'] += 1
                if last_user[chat_id]['count'] >= 10:
                    if user_id in warned_users and time.time() - warned_users[user_id] < 600:
                        return
                    try:
                        await update.message.reply_html(f"<b>ᴅᴏɴ'ᴛ sᴘᴀᴍ</b> {escape(update.effective_user.first_name)}...\n<b>ʏᴏᴜʀ ᴍᴇssᴀɢᴇs ᴡɪʟʟ ʙᴇ ɪɢɴᴏʀᴇᴅ ғᴏʀ 10 ᴍɪɴᴜᴛᴇs...!!</b>")
                    except:
                        pass
                    warned_users[user_id] = time.time()
                    return
            else:
                last_user[chat_id] = {'user_id': user_id, 'count': 1}

            message_counts[chat_id] = message_counts.get(chat_id, 0) + 1

            if message_counts[chat_id] >= message_frequency:
                await send_image(update, context)
                message_counts[chat_id] = 0
    except Exception as e:
        LOGGER.error(f"Error in message_counter: {e}")


async def send_image(update: Update, context):
    """Enhanced spawn - Group gets exclusive rarity + all global rarities"""
    chat_id = update.effective_chat.id
    try:
        all_characters = list(await collection.find({}).to_list(length=None))
        if not all_characters:
            LOGGER.warning("No characters in database")
            return

        if chat_id not in sent_characters:
            sent_characters[chat_id] = []

        if len(sent_characters[chat_id]) >= len(all_characters):
            sent_characters[chat_id] = []

        available = [c for c in all_characters if 'id' in c and c.get('id') not in sent_characters[chat_id]]
        if not available:
            available = all_characters
            sent_characters[chat_id] = []

        # Filter by allowed characters
        allowed = [char for char in available if await is_character_allowed(char, chat_id)]
        if not allowed:
            LOGGER.warning(f"No allowed characters for chat {chat_id}")
            return

        character = None
        selected_rarity = None

        try:
            # Get group exclusive settings
            group_setting = None
            if group_rarity_collection is not None:
                group_setting = await get_group_exclusive(chat_id)

            # Get global settings
            settings = await get_spawn_settings()
            global_rarities = settings.get('rarities', {}) if settings else {}

            # Build rarity pools
            rarity_pools = {}
            
            for char in allowed:
                char_rarity = char.get('rarity', '🟢 Common')
                emoji = char_rarity.split(' ')[0] if isinstance(char_rarity, str) and ' ' in char_rarity else char_rarity
                
                if emoji not in rarity_pools:
                    rarity_pools[emoji] = []
                rarity_pools[emoji].append(char)

            # Build weighted selection
            weighted_choices = []

            # Add exclusive rarity if group has one
            if group_setting:
                exclusive_emoji = group_setting['rarity_emoji']
                exclusive_chance = group_setting.get('chance', 10.0)
                
                if exclusive_emoji in rarity_pools and rarity_pools[exclusive_emoji]:
                    weighted_choices.append({
                        'emoji': exclusive_emoji,
                        'chars': rarity_pools[exclusive_emoji],
                        'chance': exclusive_chance,
                        'is_exclusive': True
                    })
                    LOGGER.info(f"Chat {chat_id} has exclusive {exclusive_emoji} ({exclusive_chance}%)")

            # Add all global enabled rarities (excluding exclusive if already added)
            for emoji, rarity_data in global_rarities.items():
                if not rarity_data.get('enabled', True):
                    continue
                    
                # Skip if this is the exclusive rarity (already added)
                if group_setting and emoji == group_setting['rarity_emoji']:
                    continue
                
                if emoji in rarity_pools and rarity_pools[emoji]:
                    weighted_choices.append({
                        'emoji': emoji,
                        'chars': rarity_pools[emoji],
                        'chance': rarity_data.get('chance', 5.0),
                        'is_exclusive': False
                    })

            # Select character using weighted random
            if weighted_choices:
                total_chance = sum(choice['chance'] for choice in weighted_choices)
                rand = random.uniform(0, total_chance)
                
                cumulative = 0
                for choice in weighted_choices:
                    cumulative += choice['chance']
                    if rand <= cumulative:
                        character = random.choice(choice['chars'])
                        selected_rarity = choice['emoji']
                        exclusive_tag = " [EXCLUSIVE]" if choice['is_exclusive'] else ""
                        LOGGER.info(f"Chat {chat_id} spawned {selected_rarity}{exclusive_tag} (chance: {choice['chance']:.2f}%, roll: {rand:.2f}/{total_chance:.2f})")
                        break

        except Exception as e:
            LOGGER.error(f"Error in weighted selection: {e}\n{traceback.format_exc()}")

        # Fallback to random if selection failed
        if not character:
            character = random.choice(allowed)
            LOGGER.warning(f"Chat {chat_id} used fallback random selection")

        sent_characters[chat_id].append(character['id'])
        last_characters[chat_id] = character
        first_correct_guesses.pop(chat_id, None)

        rarity = character.get('rarity', 'Common')
        rarity_emoji = rarity.split(' ')[0] if isinstance(rarity, str) and ' ' in rarity else '🟢'

        spawn_msg = await context.bot.send_photo(
            chat_id=chat_id,
            photo=character['img_url'],
            caption=f"{rarity_emoji} ʟᴏᴏᴋ ᴀ ᴡᴀɪғᴜ ʜᴀs sᴘᴀᴡɴᴇᴅ!!\nᴍᴀᴋᴇ ʜᴇʀ ʏᴏᴜʀ's ʙʏ /grab ᴡᴀɪғᴜ ɴᴀᴍᴇ\n⏰ {DESPAWN_TIME // 60} ᴍɪɴᴜᴛᴇs ᴛᴏ ɢʀᴀʙ!",
            parse_mode=None
        )

        spawn_messages[chat_id] = spawn_msg.message_id

        chat_username = update.effective_chat.username
        if chat_username:
            spawn_message_links[chat_id] = f"https://t.me/{chat_username}/{spawn_msg.message_id}"
        else:
            chat_id_str = str(chat_id).replace('-100', '')
            spawn_message_links[chat_id] = f"https://t.me/c/{chat_id_str}/{spawn_msg.message_id}"

        asyncio.create_task(despawn_character(chat_id, spawn_msg.message_id, character, context))

    except Exception as e:
        LOGGER.error(f"Error in send_image: {e}\n{traceback.format_exc()}")


async def guess(update: Update, context):
    """Handle /grab command"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    try:
        if chat_id not in last_characters:
            return

        if chat_id in first_correct_guesses:
            await update.message.reply_html('<b>🚫 ᴡᴀɪғᴜ ᴀʟʀᴇᴀᴅʏ ɢʀᴀʙʙᴇᴅ!</b>')
            return

        guess_text = ' '.join(context.args).lower() if context.args else ''

        if not guess_text:
            await update.message.reply_html('<b>ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ɴᴀᴍᴇ!</b>')
            return

        if "()" in guess_text or "&" in guess_text:
            await update.message.reply_html("<b>ɪɴᴠᴀʟɪᴅ ᴄʜᴀʀᴀᴄᴛᴇʀs!❌</b>")
            return

        character_name = last_characters[chat_id].get('name', '').lower()
        name_parts = character_name.split()

        is_correct = (sorted(name_parts) == sorted(guess_text.split()) or
                     any(part == guess_text for part in name_parts) or
                     guess_text == character_name)

        if is_correct:
            first_correct_guesses[chat_id] = user_id

            if chat_id in spawn_messages:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=spawn_messages[chat_id])
                except:
                    pass
                spawn_messages.pop(chat_id, None)

            user = await user_collection.find_one({'id': user_id})
            update_fields = {}
            if hasattr(update.effective_user, 'username') and update.effective_user.username:
                if not user or update.effective_user.username != user.get('username'):
                    update_fields['username'] = update.effective_user.username
            if not user or update.effective_user.first_name != user.get('first_name'):
                update_fields['first_name'] = update.effective_user.first_name

            if user:
                if update_fields:
                    await user_collection.update_one({'id': user_id}, {'$set': update_fields})
                await user_collection.update_one({'id': user_id}, {'$push': {'characters': last_characters[chat_id]}})
            else:
                await user_collection.insert_one({
                    'id': user_id,
                    'username': getattr(update.effective_user, 'username', None),
                    'first_name': update.effective_user.first_name,
                    'characters': [last_characters[chat_id]],
                })

            await update_grab_task(user_id)

            group_user_total = await group_user_totals_collection.find_one({'user_id': user_id, 'group_id': chat_id})
            if group_user_total:
                if update_fields:
                    await group_user_totals_collection.update_one({'user_id': user_id, 'group_id': chat_id}, {'$set': update_fields})
                await group_user_totals_collection.update_one({'user_id': user_id, 'group_id': chat_id}, {'$inc': {'count': 1}})
            else:
                await group_user_totals_collection.insert_one({
                    'user_id': user_id,
                    'group_id': chat_id,
                    'username': getattr(update.effective_user, 'username', None),
                    'first_name': update.effective_user.first_name,
                    'count': 1,
                })

            group_info = await top_global_groups_collection.find_one({'group_id': chat_id})
            if group_info:
                if update.effective_chat.title != group_info.get('group_name'):
                    await top_global_groups_collection.update_one({'group_id': chat_id}, {'$set': {'group_name': update.effective_chat.title}})
                await top_global_groups_collection.update_one({'group_id': chat_id}, {'$inc': {'count': 1}})
            else:
                await top_global_groups_collection.insert_one({'group_id': chat_id, 'group_name': update.effective_chat.title, 'count': 1})

            character = last_characters[chat_id]
            keyboard = [[InlineKeyboardButton("🪼 ʜᴀʀᴇᴍ", switch_inline_query_current_chat=f"collection.{user_id}")]]

            rarity = character.get('rarity', '🟢 Common')
            rarity_emoji = rarity.split(' ')[0] if isinstance(rarity, str) and ' ' in rarity else '🟢'
            rarity_text = rarity.split(' ', 1)[1] if isinstance(rarity, str) and ' ' in rarity else 'Common'

            await update.message.reply_text(
                f'🎊 <b><a href="tg://user?id={user_id}">{escape(update.effective_user.first_name)}</a></b> ɢʀᴀʙʙᴇᴅ ᴀ ɴᴇᴡ ᴡᴀɪғᴜ!\n'
                f'🎀 ɴᴀᴍᴇ: <code>{character.get("name", "Unknown")}</code>\n'
                f'{rarity_emoji} ʀᴀʀɪᴛʏ: <code>{rarity_text}</code>\n'
                f'⚡ ᴀɴɪᴍᴇ: <code>{character.get("anime", "Unknown")}</code>\n'
                f'✧ ᴀᴅᴅᴇᴅ ᴛᴏ ʏᴏᴜʀ ʜᴀʀᴇᴍ',
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

            spawn_message_links.pop(chat_id, None)
        else:
            keyboard = []
            if chat_id in spawn_message_links:
                keyboard.append([InlineKeyboardButton("📍 ᴠɪᴇᴡ sᴘᴀᴡɴ", url=spawn_message_links[chat_id])])

            await update.message.reply_html(
                '<b>ᴡʀᴏɴɢ ɴᴀᴍᴇ!❌</b>',
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
            )
    except Exception as e:
        LOGGER.error(f"Error in guess: {e}\n{traceback.format_exc()}")


def main():
    application.add_handler(CommandHandler(["grab", "g"], guess, block=False))
    application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))

    LOGGER.info("✅ Bot handlers registered")
    LOGGER.info("Starting bot...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    shivuu.start()
    LOGGER.info("✅ Bot started successfully")
    main()