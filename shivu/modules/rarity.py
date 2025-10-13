from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
import traceback

from shivu import application, db, LOGGER, OWNER_ID

# Database collection for spawn settings
spawn_settings_collection = db['spawn_settings']

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


async def set_on_rarity(update: Update, context: CallbackContext) -> None:
    """Disable spawning for specific rarity (Owner only)"""
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

        LOGGER.info(f"[SET_ON] Rarity {matched_emoji} {matched_name} disabled by {user_id}")

    except Exception as e:
        LOGGER.error(f"[SET_ON ERROR] {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text(f"❌ <b>ᴇʀʀᴏʀ:</b> <code>{str(e)}</code>", parse_mode='HTML')


async def set_off_rarity(update: Update, context: CallbackContext) -> None:
    """Enable spawning for specific rarity (Owner only)"""
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

        LOGGER.info(f"[SET_OFF] Rarity {matched_emoji} {matched_name} enabled by {user_id}")

    except Exception as e:
        LOGGER.error(f"[SET_OFF ERROR] {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text(f"❌ <b>ᴇʀʀᴏʀ:</b> <code>{str(e)}</code>", parse_mode='HTML')


async def on_anime(update: Update, context: CallbackContext) -> None:
    """Disable spawning for specific anime (Owner only)"""
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

        LOGGER.info(f"[ON] Anime {anime_name} disabled by {user_id}")

    except Exception as e:
        LOGGER.error(f"[ON ERROR] {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text(f"❌ <b>ᴇʀʀᴏʀ:</b> <code>{str(e)}</code>", parse_mode='HTML')


async def off_anime(update: Update, context: CallbackContext) -> None:
    """Enable spawning for specific anime (Owner only)"""
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

        LOGGER.info(f"[OFF] Anime {anime_name} enabled by {user_id}")

    except Exception as e:
        LOGGER.error(f"[OFF ERROR] {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text(f"❌ <b>ᴇʀʀᴏʀ:</b> <code>{str(e)}</code>", parse_mode='HTML')


def register_rarity_handlers():
    """Register rarity and anime control handlers"""
    application.add_handler(CommandHandler('set_on', set_on_rarity, block=False))
    application.add_handler(CommandHandler('set_off', set_off_rarity, block=False))
    application.add_handler(CommandHandler('on', on_anime, block=False))
    application.add_handler(CommandHandler('off', off_anime, block=False))
    LOGGER.info("[RARITY CONTROL] Handlers registered")