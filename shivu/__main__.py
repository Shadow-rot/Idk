import importlib
import time
import random
import re
import asyncio
from html import escape
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, MessageHandler, filters

from shivu import db, shivuu, application, LOGGER
from shivu.modules import ALL_MODULES

collection = db['anime_characters_lol']
user_collection = db['user_collection_lmaoooo']
user_totals_collection = db['user_totals_lmaoooo']
group_user_totals_collection = db['group_user_totalsssssss']
top_global_groups_collection = db['top_global_groups']

DEFAULT_MESSAGE_FREQUENCY = 70

locks = {}
message_counts = {}
sent_characters = {}
last_characters = {}
first_correct_guesses = {}
last_user = {}
warned_users = {}
spawn_settings_collection = None

# Import all modules
for module_name in ALL_MODULES:
    try:
        importlib.import_module("shivu.modules." + module_name)
        LOGGER.info(f"✅ Imported: {module_name}")
    except Exception as e:
        LOGGER.error(f"❌ Failed to import {module_name}: {e}")

# Register plugin manager handlers
try:
    from shivu.modules.plugins_manager import register_handlers
    register_handlers(application)
    LOGGER.info("✅ Plugin manager handlers registered")
except Exception as e:
    LOGGER.error(f"❌ Failed to register plugin manager: {e}")

# Import spawn settings
try:
    from shivu.modules.rarity import spawn_settings_collection as ssc
    spawn_settings_collection = ssc
except:
    pass


async def is_character_allowed(character):
    try:
        if character.get('removed', False):
            return False

        if spawn_settings_collection:
            settings = await spawn_settings_collection.find_one({'type': 'rarity_control'})
            if settings:
                char_rarity = character.get('rarity', '🟢 Common')
                rarity_emoji = char_rarity.split(' ')[0] if isinstance(char_rarity, str) and ' ' in char_rarity else char_rarity
                rarities = settings.get('rarities', {})
                if rarity_emoji in rarities and not rarities[rarity_emoji].get('enabled', True):
                    return False

            old_settings = await spawn_settings_collection.find_one({'type': 'global'})
            if old_settings:
                disabled_rarities = old_settings.get('disabled_rarities', [])
                char_rarity = character.get('rarity', 'Common')
                rarity_emoji = char_rarity.split(' ')[0] if isinstance(char_rarity, str) and ' ' in char_rarity else char_rarity
                if rarity_emoji in disabled_rarities:
                    return False
                disabled_animes = old_settings.get('disabled_animes', [])
                char_anime = character.get('anime', '').lower()
                if char_anime in [anime.lower() for anime in disabled_animes]:
                    return False
        return True
    except:
        return True


async def get_chat_message_frequency(chat_id):
    try:
        chat_frequency = await user_totals_collection.find_one({'chat_id': chat_id})
        if chat_frequency:
            return chat_frequency.get('message_frequency', DEFAULT_MESSAGE_FREQUENCY)
        await user_totals_collection.insert_one({'chat_id': chat_id, 'message_frequency': DEFAULT_MESSAGE_FREQUENCY})
        return DEFAULT_MESSAGE_FREQUENCY
    except:
        return DEFAULT_MESSAGE_FREQUENCY


async def update_grab_task(user_id: int):
    try:
        user = await user_collection.find_one({'id': user_id})
        if user and 'pass_data' in user:
            await user_collection.update_one({'id': user_id}, {'$inc': {'pass_data.tasks.grabs': 1}})
    except:
        pass


async def message_counter(update: Update, context):
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
    chat_id = update.effective_chat.id
    try:
        all_characters = list(await collection.find({}).to_list(length=None))
        if not all_characters:
            return

        if chat_id not in sent_characters:
            sent_characters[chat_id] = []

        if len(sent_characters[chat_id]) >= len(all_characters):
            sent_characters[chat_id] = []

        available_characters = [c for c in all_characters if 'id' in c and c.get('id') not in sent_characters[chat_id]]
        if not available_characters:
            available_characters = all_characters
            sent_characters[chat_id] = []

        allowed_characters = [char for char in available_characters if await is_character_allowed(char)]
        if not allowed_characters:
            return

        character = None
        try:
            if spawn_settings_collection:
                settings = await spawn_settings_collection.find_one({'type': 'rarity_control'})
                if settings and settings.get('rarities'):
                    rarities = settings['rarities']
                    rarity_groups = {}
                    for char in allowed_characters:
                        char_rarity = char.get('rarity', '🟢 Common')
                        rarity_emoji = char_rarity.split(' ')[0] if isinstance(char_rarity, str) and ' ' in char_rarity else char_rarity
                        if rarity_emoji not in rarity_groups:
                            rarity_groups[rarity_emoji] = []
                        rarity_groups[rarity_emoji].append(char)

                    weighted_chars = []
                    for emoji, chars in rarity_groups.items():
                        if emoji in rarities and rarities[emoji].get('enabled', True):
                            chance = rarities[emoji].get('chance', 0)
                            weight = max(1, int(chance * 10))
                            weighted_chars.extend(chars * weight)

                    if weighted_chars:
                        character = random.choice(weighted_chars)
        except:
            pass

        if not character:
            character = random.choice(allowed_characters)

        sent_characters[chat_id].append(character['id'])
        last_characters[chat_id] = character
        first_correct_guesses.pop(chat_id, None)

        rarity = character.get('rarity', 'Common')
        rarity_emoji = rarity.split(' ')[0] if isinstance(rarity, str) and ' ' in rarity else ''

        await context.bot.send_photo(
            chat_id=chat_id,
            photo=character['img_url'],
            caption=f"***{rarity_emoji} ʟᴏᴏᴋ ᴀ ᴡᴀɪғᴜ ʜᴀs sᴘᴀᴡɴᴇᴅ !! ᴍᴀᴋᴇ ʜᴇʀ ʏᴏᴜʀ's ʙʏ ɢɪᴠɪɴɢ\n/grab 𝚆𝚊𝚒𝚏𝚞 𝚗𝚊𝚖𝚎***",
            parse_mode='Markdown'
        )
    except Exception as e:
        LOGGER.error(f"Error in send_image: {e}")


async def guess(update: Update, context):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    try:
        if chat_id not in last_characters:
            return

        if chat_id in first_correct_guesses:
            await update.message.reply_html('<b>🚫 ᴡᴀɪғᴜ ᴀʟʀᴇᴀᴅʏ ɢʀᴀʙʙᴇᴅ ʙʏ sᴏᴍᴇᴏɴᴇ ᴇʟsᴇ ⚡. ʙᴇᴛᴛᴇʀ ʟᴜᴄᴋ ɴᴇxᴛ ᴛɪᴍᴇ..!!</b>')
            return

        guess_text = ' '.join(context.args).lower() if context.args else ''

        if not guess_text:
            await update.message.reply_html('<b>ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ɴᴀᴍᴇ!</b>')
            return

        if "()" in guess_text or "&" in guess_text:
            await update.message.reply_html("<b>ɴᴀʜʜ ʏᴏᴜ ᴄᴀɴ'ᴛ ᴜsᴇ ᴛʜɪs ᴛʏᴘᴇs ᴏғ ᴡᴏʀᴅs...❌</b>")
            return

        character_name = last_characters[chat_id].get('name', '').lower()
        name_parts = character_name.split()

        is_correct = (sorted(name_parts) == sorted(guess_text.split()) or 
                     any(part == guess_text for part in name_parts) or 
                     guess_text == character_name)

        if is_correct:
            first_correct_guesses[chat_id] = user_id

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
            group_update_fields = {}
            if group_info and update.effective_chat.title != group_info.get('group_name'):
                group_update_fields['group_name'] = update.effective_chat.title

            if group_info:
                if group_update_fields:
                    await top_global_groups_collection.update_one({'group_id': chat_id}, {'$set': group_update_fields})
                await top_global_groups_collection.update_one({'group_id': chat_id}, {'$inc': {'count': 1}})
            else:
                await top_global_groups_collection.insert_one({'group_id': chat_id, 'group_name': update.effective_chat.title, 'count': 1})

            character = last_characters[chat_id]
            keyboard = [[InlineKeyboardButton("🪼 ʜᴀʀᴇᴍ", switch_inline_query_current_chat=f"collection.{user_id}")]]

            rarity = character.get('rarity', '🟢 Common')
            if isinstance(rarity, str) and ' ' in rarity:
                rarity_parts = rarity.split(' ', 1)
                rarity_emoji = rarity_parts[0]
                rarity_text = rarity_parts[1] if len(rarity_parts) > 1 else 'Common'
            else:
                rarity_emoji = '🟢'
                rarity_text = rarity

            await update.message.reply_text(
                f'Congratulations 🎊\n<b><a href="tg://user?id={user_id}">{escape(update.effective_user.first_name)}</a></b> You grabbed a new waifu!! ✅️\n\n'
                f'🎀 𝙉𝙖𝙢𝙚: <code>{character.get("name", "Unknown")}</code>\n'
                f'{rarity_emoji} 𝙍𝙖𝙧𝙞𝙩𝙮: <code>{rarity_text}</code>\n'
                f'⚡ 𝘼𝙣𝙞𝙢𝙚: <code>{character.get("anime", "Unknown")}</code>\n\n'
                f'✧⁠ Character successfully added in your harem',
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_html('<b>ᴘʟᴇᴀsᴇ ᴡʀɪᴛᴇ ᴀ ᴄᴏʀʀᴇᴄᴛ ɴᴀᴍᴇ..❌</b>')
    except Exception as e:
        LOGGER.error(f"Error in guess: {e}")


def main():
    application.add_handler(CommandHandler(["grab", "g"], guess, block=False))
    application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    shivuu.start()
    LOGGER.info("Bot started")
    main()