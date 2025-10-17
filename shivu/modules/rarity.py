from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
import traceback

from shivu import application, db, collection, user_collection, LOGGER

# Database collection for spawn settings
spawn_settings_collection = db['spawn_settings']

# Owner ID
OWNER_ID = 5147822244

# Rarity list with emojis
RARITY_LIST = {
    '🟢': 'ᴄᴏᴍᴍᴏɴ',
    '🟣': 'ʀᴀʀᴇ',
    '🟡': 'ʟᴇɢᴇɴᴅᴀʀʏ',
    '💮': 'sᴘᴇᴄɪᴀʟ ᴇᴅɪᴛɪᴏɴ',
    '💫': 'ɴᴇᴏɴ',
    '✨': 'ᴍᴀɴɢᴀ',
    '🎭': 'ᴄᴏsᴘʟᴀʏ',
    '🎐': 'ᴄᴇʟᴇsᴛɪᴀʟ',
    '🔮': 'ᴘʀᴇᴍɪᴜᴍ ᴇᴅɪᴛɪᴏɴ',
    '💋': 'ᴇʀᴏᴛɪᴄ',
    '🌤': 'sᴜᴍᴍᴇʀ',
    '☃️': 'ᴡɪɴᴛᴇʀ',
    '☔️': 'ᴍᴏɴsᴏᴏɴ',
    '💝': 'ᴠᴀʟᴇɴᴛɪɴᴇ',
    '🎃': 'ʜᴀʟʟᴏᴡᴇᴇɴ',
    '🎄': 'ᴄʜʀɪsᴛᴍᴀs',
    '🏵': 'ᴍʏᴛʜɪᴄ',
    '🎗': 'sᴘᴇᴄɪᴀʟ ᴇᴠᴇɴᴛs',
    '🎥': 'ᴀᴍᴠ'
}


async def set_off_rarity(update: Update, context: CallbackContext) -> None:
    """Disable spawning for specific rarity (Owner only)"""
    user_id = update.effective_user.id

    if user_id != OWNER_ID:
        await update.message.reply_text("⚠️ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ᴏɴʟʏ ғᴏʀ ᴏᴡɴᴇʀ!")
        return

    if not context.args:
        rarity_list = "\n".join([f"{emoji} {name}" for emoji, name in RARITY_LIST.items()])
        await update.message.reply_text(
            f"📝 <b>ᴜsᴀɢᴇ:</b> <code>/set_off [rarity emoji or name]</code>\n\n"
            f"<b>ᴀᴠᴀɪʟᴀʙʟᴇ ʀᴀʀɪᴛɪᴇs:</b>\n{rarity_list}",
            parse_mode='HTML'
        )
        return

    rarity_input = ' '.join(context.args).lower()

    # Find matching rarity
    matched_emoji = None
    matched_name = None

    for emoji, name in RARITY_LIST.items():
        if emoji == rarity_input or name.lower() == rarity_input:
            matched_emoji = emoji
            matched_name = name
            break

    if not matched_emoji:
        await update.message.reply_text("❌ ɪɴᴠᴀʟɪᴅ ʀᴀʀɪᴛʏ! ᴜsᴇ /set_off ᴛᴏ sᴇᴇ ᴀᴠᴀɪʟᴀʙʟᴇ ʀᴀʀɪᴛɪᴇs.")
        return

    try:
        # Get or create settings
        settings = await spawn_settings_collection.find_one({'type': 'global'})

        if not settings:
            settings = {
                'type': 'global',
                'disabled_rarities': [],
                'disabled_animes': []
            }
            await spawn_settings_collection.insert_one(settings)

        # Check if already disabled
        if matched_emoji in settings.get('disabled_rarities', []):
            await update.message.reply_text(
                f"⚠️ {matched_emoji} <b>{matched_name}</b> ɪs ᴀʟʀᴇᴀᴅʏ ᴅɪsᴀʙʟᴇᴅ!",
                parse_mode='HTML'
            )
            return

        # Add to disabled list
        await spawn_settings_collection.update_one(
            {'type': 'global'},
            {'$addToSet': {'disabled_rarities': matched_emoji}}
        )

        await update.message.reply_text(
            f"✅ <b>ʀᴀʀɪᴛʏ sᴘᴀᴡɴɪɴɢ ᴅɪsᴀʙʟᴇᴅ!</b>\n\n"
            f"{matched_emoji} <b>{matched_name}</b> ᴄʜᴀʀᴀᴄᴛᴇʀs ᴡɪʟʟ ɴᴏᴛ sᴘᴀᴡɴ ᴀɴʏᴍᴏʀᴇ.",
            parse_mode='HTML'
        )

        LOGGER.info(f"[SET_OFF] Rarity {matched_emoji} {matched_name} disabled by {user_id}")

    except Exception as e:
        LOGGER.error(f"[SET_OFF ERROR] {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text(f"❌ <b>ᴇʀʀᴏʀ:</b> <code>{str(e)}</code>", parse_mode='HTML')


async def set_on_rarity(update: Update, context: CallbackContext) -> None:
    """Enable spawning for specific rarity (Owner only)"""
    user_id = update.effective_user.id

    if user_id != OWNER_ID:
        await update.message.reply_text("⚠️ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ᴏɴʟʏ ғᴏʀ ᴏᴡɴᴇʀ!")
        return

    if not context.args:
        rarity_list = "\n".join([f"{emoji} {name}" for emoji, name in RARITY_LIST.items()])
        await update.message.reply_text(
            f"📝 <b>ᴜsᴀɢᴇ:</b> <code>/set_on [rarity emoji or name]</code>\n\n"
            f"<b>ᴀᴠᴀɪʟᴀʙʟᴇ ʀᴀʀɪᴛɪᴇs:</b>\n{rarity_list}",
            parse_mode='HTML'
        )
        return

    rarity_input = ' '.join(context.args).lower()

    # Find matching rarity
    matched_emoji = None
    matched_name = None

    for emoji, name in RARITY_LIST.items():
        if emoji == rarity_input or name.lower() == rarity_input:
            matched_emoji = emoji
            matched_name = name
            break

    if not matched_emoji:
        await update.message.reply_text("❌ ɪɴᴠᴀʟɪᴅ ʀᴀʀɪᴛʏ! ᴜsᴇ /set_on ᴛᴏ sᴇᴇ ᴀᴠᴀɪʟᴀʙʟᴇ ʀᴀʀɪᴛɪᴇs.")
        return

    try:
        # Get settings
        settings = await spawn_settings_collection.find_one({'type': 'global'})

        if not settings or matched_emoji not in settings.get('disabled_rarities', []):
            await update.message.reply_text(
                f"⚠️ {matched_emoji} <b>{matched_name}</b> ɪs ɴᴏᴛ ᴅɪsᴀʙʟᴇᴅ!",
                parse_mode='HTML'
            )
            return

        # Remove from disabled list
        await spawn_settings_collection.update_one(
            {'type': 'global'},
            {'$pull': {'disabled_rarities': matched_emoji}}
        )

        await update.message.reply_text(
            f"✅ <b>ʀᴀʀɪᴛʏ sᴘᴀᴡɴɪɴɢ ᴇɴᴀʙʟᴇᴅ!</b>\n\n"
            f"{matched_emoji} <b>{matched_name}</b> ᴄʜᴀʀᴀᴄᴛᴇʀs ᴡɪʟʟ sᴘᴀᴡɴ ᴀɢᴀɪɴ.",
            parse_mode='HTML'
        )

        LOGGER.info(f"[SET_ON] Rarity {matched_emoji} {matched_name} enabled by {user_id}")

    except Exception as e:
        LOGGER.error(f"[SET_ON ERROR] {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text(f"❌ <b>ᴇʀʀᴏʀ:</b> <code>{str(e)}</code>", parse_mode='HTML')


async def off_anime(update: Update, context: CallbackContext) -> None:
    """Disable spawning for specific anime (Owner only)"""
    user_id = update.effective_user.id

    if user_id != OWNER_ID:
        await update.message.reply_text("⚠️ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ᴏɴʟʏ ғᴏʀ ᴏᴡɴᴇʀ!")
        return

    if not context.args:
        await update.message.reply_text(
            "📝 <b>ᴜsᴀɢᴇ:</b> <code>/off [anime name]</code>\n\n"
            "<i>ᴇxᴀᴍᴘʟᴇ: /off Naruto</i>",
            parse_mode='HTML'
        )
        return

    anime_name = ' '.join(context.args)

    try:
        # Get or create settings
        settings = await spawn_settings_collection.find_one({'type': 'global'})

        if not settings:
            settings = {
                'type': 'global',
                'disabled_rarities': [],
                'disabled_animes': []
            }
            await spawn_settings_collection.insert_one(settings)

        # Check if already disabled
        if anime_name.lower() in [a.lower() for a in settings.get('disabled_animes', [])]:
            await update.message.reply_text(
                f"⚠️ <b>{anime_name}</b> ɪs ᴀʟʀᴇᴀᴅʏ ᴅɪsᴀʙʟᴇᴅ!",
                parse_mode='HTML'
            )
            return

        # Add to disabled list
        await spawn_settings_collection.update_one(
            {'type': 'global'},
            {'$addToSet': {'disabled_animes': anime_name}}
        )

        await update.message.reply_text(
            f"✅ <b>ᴀɴɪᴍᴇ sᴘᴀᴡɴɪɴɢ ᴅɪsᴀʙʟᴇᴅ!</b>\n\n"
            f"📺 <b>{anime_name}</b> ᴄʜᴀʀᴀᴄᴛᴇʀs ᴡɪʟʟ ɴᴏᴛ sᴘᴀᴡɴ ᴀɴʏᴍᴏʀᴇ.",
            parse_mode='HTML'
        )

        LOGGER.info(f"[OFF] Anime {anime_name} disabled by {user_id}")

    except Exception as e:
        LOGGER.error(f"[OFF ERROR] {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text(f"❌ <b>ᴇʀʀᴏʀ:</b> <code>{str(e)}</code>", parse_mode='HTML')


async def on_anime(update: Update, context: CallbackContext) -> None:
    """Enable spawning for specific anime (Owner only)"""
    user_id = update.effective_user.id

    if user_id != OWNER_ID:
        await update.message.reply_text("⚠️ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ᴏɴʟʏ ғᴏʀ ᴏᴡɴᴇʀ!")
        return

    if not context.args:
        await update.message.reply_text(
            "📝 <b>ᴜsᴀɢᴇ:</b> <code>/on [anime name]</code>\n\n"
            "<i>ᴇxᴀᴍᴘʟᴇ: /on Naruto</i>",
            parse_mode='HTML'
        )
        return

    anime_name = ' '.join(context.args)

    try:
        # Get settings
        settings = await spawn_settings_collection.find_one({'type': 'global'})

        if not settings:
            await update.message.reply_text(
                f"⚠️ <b>{anime_name}</b> ɪs ɴᴏᴛ ᴅɪsᴀʙʟᴇᴅ!",
                parse_mode='HTML'
            )
            return

        # Find exact match (case-insensitive)
        disabled_animes = settings.get('disabled_animes', [])
        matched_anime = None

        for anime in disabled_animes:
            if anime.lower() == anime_name.lower():
                matched_anime = anime
                break

        if not matched_anime:
            await update.message.reply_text(
                f"⚠️ <b>{anime_name}</b> ɪs ɴᴏᴛ ᴅɪsᴀʙʟᴇᴅ!",
                parse_mode='HTML'
            )
            return

        # Remove from disabled list
        await spawn_settings_collection.update_one(
            {'type': 'global'},
            {'$pull': {'disabled_animes': matched_anime}}
        )

        await update.message.reply_text(
            f"✅ <b>ᴀɴɪᴍᴇ sᴘᴀᴡɴɪɴɢ ᴇɴᴀʙʟᴇᴅ!</b>\n\n"
            f"📺 <b>{anime_name}</b> ᴄʜᴀʀᴀᴄᴛᴇʀs ᴡɪʟʟ sᴘᴀᴡɴ ᴀɢᴀɪɴ.",
            parse_mode='HTML'
        )

        LOGGER.info(f"[ON] Anime {anime_name} enabled by {user_id}")

    except Exception as e:
        LOGGER.error(f"[ON ERROR] {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text(f"❌ <b>ᴇʀʀᴏʀ:</b> <code>{str(e)}</code>", parse_mode='HTML')


async def remove_character_from_all(update: Update, context: CallbackContext) -> None:
    """Remove a character from all user collections by character ID (Owner only)"""
    user_id = update.effective_user.id

    if user_id != OWNER_ID:
        await update.message.reply_text("⚠️ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ᴏɴʟʏ ғᴏʀ ᴏᴡɴᴇʀ!")
        return

    if not context.args:
        await update.message.reply_text(
            "📝 <b>ᴜsᴀɢᴇ:</b> <code>/rmcol [character_id]</code>\n\n"
            "<i>ᴇxᴀᴍᴘʟᴇ: /rmcol 12345</i>\n\n"
            "⚠️ <b>ᴡᴀʀɴɪɴɢ:</b> ᴛʜɪs ᴡɪʟʟ ʀᴇᴍᴏᴠᴇ ᴛʜᴇ ᴄʜᴀʀᴀᴄᴛᴇʀ ғʀᴏᴍ ᴀʟʟ ᴜsᴇʀs!",
            parse_mode='HTML'
        )
        return

    try:
        character_id = context.args[0]

        # First, check if character exists in main collection
        character = await collection.find_one({'id': character_id})

        if not character:
            await update.message.reply_text(
                f"❌ <b>ᴄʜᴀʀᴀᴄᴛᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ!</b>\n\n"
                f"ɴᴏ ᴄʜᴀʀᴀᴄᴛᴇʀ ᴡɪᴛʜ ɪᴅ: <code>{character_id}</code>",
                parse_mode='HTML'
            )
            return

        char_name = character.get('name', 'ᴜɴᴋɴᴏᴡɴ')
        char_anime = character.get('anime', 'ᴜɴᴋɴᴏᴡɴ')
        char_rarity = character.get('rarity', '❓')

        # Send confirmation message
        processing_msg = await update.message.reply_text(
            f"🔄 <b>ᴘʀᴏᴄᴇssɪɴɢ...</b>\n\n"
            f"ʀᴇᴍᴏᴠɪɴɢ ᴄʜᴀʀᴀᴄᴛᴇʀ ғʀᴏᴍ ᴀʟʟ ᴜsᴇʀs:\n"
            f"📛 <b>{char_name}</b>\n"
            f"📺 {char_anime}\n"
            f"{char_rarity} ɪᴅ: <code>{character_id}</code>",
            parse_mode='HTML'
        )

        # Remove character from all users who have it
        result = await user_collection.update_many(
            {'characters.id': character_id},
            {'$pull': {'characters': {'id': character_id}}}
        )

        users_affected = result.modified_count

        await processing_msg.edit_text(
            f"✅ <b>ᴄʜᴀʀᴀᴄᴛᴇʀ ʀᴇᴍᴏᴠᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!</b>\n\n"
            f"📛 <b>{char_name}</b>\n"
            f"📺 {char_anime}\n"
            f"{char_rarity} ɪᴅ: <code>{character_id}</code>\n\n"
            f"👥 <b>ᴜsᴇʀs ᴀғғᴇᴄᴛᴇᴅ:</b> {users_affected}\n"
            f"🗑 ʀᴇᴍᴏᴠᴇᴅ ғʀᴏᴍ ᴀʟʟ ᴜsᴇʀ ᴄᴏʟʟᴇᴄᴛɪᴏɴs",
            parse_mode='HTML'
        )

        LOGGER.info(f"[RMCOL] Character {character_id} ({char_name}) removed from {users_affected} users by owner {user_id}")

    except ValueError:
        await update.message.reply_text(
            "❌ <b>ɪɴᴠᴀʟɪᴅ ᴄʜᴀʀᴀᴄᴛᴇʀ ɪᴅ!</b>\n\n"
            "ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴠᴀʟɪᴅ ᴄʜᴀʀᴀᴄᴛᴇʀ ɪᴅ.",
            parse_mode='HTML'
        )
    except Exception as e:
        LOGGER.error(f"[RMCOL ERROR] {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text(
            f"❌ <b>ᴇʀʀᴏʀ:</b> <code>{str(e)}</code>\n\n"
            f"ғᴀɪʟᴇᴅ ᴛᴏ ʀᴇᴍᴏᴠᴇ ᴄʜᴀʀᴀᴄᴛᴇʀ.",
            parse_mode='HTML'
        )


# Register all handlers
application.add_handler(CommandHandler('set_off', set_off_rarity, block=False))
application.add_handler(CommandHandler('set_on', set_on_rarity, block=False))
application.add_handler(CommandHandler('off', off_anime, block=False))
application.add_handler(CommandHandler('on', on_anime, block=False))
application.add_handler(CommandHandler('rmcol', remove_character_from_all, block=False))

LOGGER.info("[RARITY CONTROL] All handlers registered successfully")