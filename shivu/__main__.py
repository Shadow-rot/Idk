import importlib
import time
import random
import re
import asyncio
from html import escape
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, filters
from telegram.error import BadRequest, Forbidden

from shivu import (
    db,
    shivuu,
    application,
    LOGGER
)
from shivu.modules import ALL_MODULES

# Custom modules
from shivu.modules.remove import register_remove_handlers
from shivu.modules.rarity import register_rarity_handlers, spawn_settings_collection
from shivu.modules.ckill import register_ckill_handler
from shivu.modules.kill import register_kill_handler
from shivu.modules.hclaim import register_hclaim_handler
from shivu.modules.gift import register_gift_handlers

# Database collections
collection = db['anime_characters_lol']
user_collection = db['user_collection_lmaoooo']
user_totals_collection = db['user_totals_lmaoooo']
group_user_totals_collection = db['group_user_totalsssssss']
top_global_groups_collection = db['top_global_groups']

LOG_CHAT_ID = -1003071132623

# Global state
locks = {}
sent_characters = {}
last_characters = {}
first_correct_guesses = {}
message_counts = {}
last_user = {}
warned_users = {}

DEFAULT_MESSAGE_FREQUENCY = 50

# Import all modules dynamically
for module_name in ALL_MODULES:
    try:
        importlib.import_module("shivu.modules." + module_name)
        LOGGER.info(f"✅ Imported module: {module_name}")
    except Exception as e:
        LOGGER.error(f"⚠️ Failed to import {module_name}: {e}")


def escape_markdown(text):
    escape_chars = r'\*_`\\~>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)


async def is_character_allowed(character):
    try:
        if character.get('removed', False):
            return False

        settings = await spawn_settings_collection.find_one({'type': 'global'})
        if not settings:
            return True

        disabled_rarities = settings.get('disabled_rarities', [])
        disabled_animes = settings.get('disabled_animes', [])

        rarity = character.get('rarity', '🟢 Common')
        rarity_emoji = rarity.split(' ')[0] if ' ' in rarity else rarity
        anime_name = character.get('anime', '').lower()

        if rarity_emoji in disabled_rarities or anime_name in [a.lower() for a in disabled_animes]:
            return False

        return True
    except Exception as e:
        LOGGER.error(f"Error checking allowed character: {e}")
        return True


async def message_counter(update: Update, context: CallbackContext) -> None:
    """Count **all messages** and spawn characters every 50 messages."""
    chat_id = str(update.effective_chat.id)
    user_id = update.effective_user.id if update.effective_user else 0

    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()
    lock = locks[chat_id]

    async with lock:
        try:
            chat_data = await user_totals_collection.find_one({'chat_id': chat_id})
            message_frequency = chat_data.get('message_frequency', DEFAULT_MESSAGE_FREQUENCY) if chat_data else DEFAULT_MESSAGE_FREQUENCY

            # Anti-spam (same user)
            if chat_id in last_user and last_user[chat_id]['user_id'] == user_id:
                last_user[chat_id]['count'] += 1
                if last_user[chat_id]['count'] >= 10:
                    if user_id in warned_users and time.time() - warned_users[user_id] < 600:
                        return
                    try:
                        await update.message.reply_text(
                            f"⚠️ ᴅᴏɴ'ᴛ sᴘᴀᴍ {escape(update.effective_user.first_name)}.\n"
                            "ʏᴏᴜʀ ᴍᴇssᴀɢᴇs ᴡɪʟʟ ʙᴇ ɪɢɴᴏʀᴇᴅ ғᴏʀ 10 ᴍɪɴᴜᴛᴇs."
                        )
                    except Exception:
                        pass
                    warned_users[user_id] = time.time()
                    return
            else:
                last_user[chat_id] = {'user_id': user_id, 'count': 1}

            # Count message
            message_counts[chat_id] = message_counts.get(chat_id, 0) + 1

            # Spawn every N messages (includes bots, commands, media, etc.)
            if message_counts[chat_id] >= message_frequency:
                await send_image(update, context)
                message_counts[chat_id] = 0

        except Exception as e:
            LOGGER.error(f"Error in message counter: {e}")


async def send_image(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    try:
        characters = list(await collection.find({}).to_list(length=None))
        if not characters:
            LOGGER.warning("No characters in database.")
            return

        sent_characters.setdefault(chat_id, [])
        if len(sent_characters[chat_id]) >= len(characters):
            sent_characters[chat_id] = []

        available = [c for c in characters if 'id' in c and c['id'] not in sent_characters[chat_id]]
        if not available:
            available = characters
            sent_characters[chat_id] = []

        allowed = [c for c in available if await is_character_allowed(c)]
        if not allowed:
            LOGGER.info(f"No allowed characters to spawn in chat {chat_id}")
            return

        char = random.choice(allowed)
        sent_characters[chat_id].append(char['id'])
        last_characters[chat_id] = char
        first_correct_guesses.pop(chat_id, None)

        rarity = char.get('rarity', '🟢 Common')
        emoji = rarity.split(' ')[0] if isinstance(rarity, str) and ' ' in rarity else '🟢'

        caption = (
            f"***{emoji} ᴀ ᴡᴀɪғᴜ ʜᴀs sᴘᴀᴡɴᴇᴅ!***\n"
            f"ᴜsᴇ /grab ᴡᴀɪғᴜ_ɴᴀᴍᴇ ᴛᴏ ᴄʟᴀɪᴍ ʜᴇʀ 💖"
        )

        await context.bot.send_photo(
            chat_id=chat_id,
            photo=char['img_url'],
            caption=caption,
            parse_mode='Markdown'
        )
        LOGGER.info(f"Spawned: {char.get('name')} in chat {chat_id}")

    except Exception as e:
        LOGGER.error(f"Error sending character: {e}")


async def guess(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in last_characters:
        return
    if chat_id in first_correct_guesses:
        await update.message.reply_text("🚫 ᴡᴀɪғᴜ ᴀʟʀᴇᴀᴅʏ ɢʀᴀʙʙᴇᴅ ʙʏ sᴏᴍᴇᴏɴᴇ ᴇʟsᴇ ⚡")
        return

    guess_text = ' '.join(context.args).lower() if context.args else ''
    if not guess_text:
        await update.message.reply_text('ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ɴᴀᴍᴇ.')
        return

    char = last_characters[chat_id]
    name = char.get('name', '').lower()
    parts = name.split()
    correct = (
        guess_text == name or
        any(part == guess_text for part in parts) or
        sorted(parts) == sorted(guess_text.split())
    )

    if not correct:
        await update.message.reply_text('ᴡʀᴏɴɢ ɴᴀᴍᴇ ❌')
        return

    first_correct_guesses[chat_id] = user_id

    try:
        # Update user data
        user = await user_collection.find_one({'id': user_id})
        if user:
            await user_collection.update_one({'id': user_id}, {'$push': {'characters': char}})
        else:
            await user_collection.insert_one({
                'id': user_id,
                'username': getattr(update.effective_user, 'username', None),
                'first_name': update.effective_user.first_name,
                'characters': [char],
            })

        # Update group stats
        await group_user_totals_collection.update_one(
            {'user_id': user_id, 'group_id': chat_id},
            {'$inc': {'count': 1}},
            upsert=True
        )
        await top_global_groups_collection.update_one(
            {'group_id': chat_id},
            {'$inc': {'count': 1}, '$set': {'group_name': update.effective_chat.title}},
            upsert=True
        )

        rarity = char.get('rarity', '🟢 Common')
        emoji = rarity.split(' ')[0] if ' ' in rarity else '🟢'
        text = (
            f"<b><a href='tg://user?id={user_id}'>{escape(update.effective_user.first_name)}</a></b> "
            f"ᴄʟᴀɪᴍᴇᴅ ᴀ ɴᴇᴡ ᴡᴀɪғᴜ 💖\n\n"
            f"🍁 ɴᴀᴍᴇ: <code>{char.get('name')}</code>\n"
            f"⛩️ ᴀɴɪᴍᴇ: <code>{char.get('anime')}</code>\n"
            f"{emoji} ʀᴀʀɪᴛʏ: <code>{rarity}</code>"
        )
        keyboard = [[InlineKeyboardButton("🪼 ʜᴀʀᴇᴍ", switch_inline_query_current_chat=f"collection.{user_id}")]]
        await update.message.reply_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

    except Exception as e:
        LOGGER.error(f"Error processing grab: {e}")
        await update.message.reply_text("ᴇʀʀᴏʀ ᴡʜɪʟᴇ ᴘʀᴏᴄᴇssɪɴɢ ɢʀᴀʙ.")


def main():
    try:
        application.add_handler(CommandHandler(["grab", "g"], guess, block=False))
        register_remove_handlers()
        register_rarity_handlers()
        register_ckill_handler()
        register_kill_handler()
        register_hclaim_handler()
        register_gift_handlers()

        # Count all messages (no filter restriction)
        application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))

        LOGGER.info("✅ Handlers registered. Starting bot...")
        application.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        LOGGER.error(f"Main error: {e}")
        raise


if __name__ == "__main__":
    try:
        shivuu.start()
        LOGGER.info("Shivuu client started.")
        main()
    except KeyboardInterrupt:
        LOGGER.info("Bot stopped manually.")
    except Exception as e:
        LOGGER.error(f"Fatal error: {e}")
    finally:
        try:
            shivuu.stop()
            LOGGER.info("Shivuu client stopped.")
        except:
            pass