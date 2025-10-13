from datetime import datetime
from html import escape
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
import traceback

from shivu import application, collection, LOGGER

# Log chat ID
LOG_CHAT_ID = -1003071132623
OWNER_ID = 5147822244


async def remove_chr(update: Update, context: CallbackContext) -> None:
    """Remove character from circulation (Owner only)"""
    user_id = update.effective_user.id

    # Check if owner
    if user_id != OWNER_ID:
        await update.message.reply_text("⚠️ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ᴏɴʟʏ ғᴏʀ ᴏᴡɴᴇʀ!")
        return

    if not context.args:
        await update.message.reply_text("📝 ᴜsᴀɢᴇ: <code>/remove_chr character_id</code>", parse_mode='HTML')
        return

    character_id = str(context.args[0])

    try:
        # Find character in main collection
        character = await collection.find_one({'id': character_id})
        
        if not character:
            await update.message.reply_text(
                f"❌ ᴄʜᴀʀᴀᴄᴛᴇʀ ᴡɪᴛʜ ɪᴅ <code>{character_id}</code> ɴᴏᴛ ғᴏᴜɴᴅ!", 
                parse_mode='HTML'
            )
            return

        # Mark character as removed (add a flag instead of deleting)
        await collection.update_one(
            {'id': character_id},
            {'$set': {'removed': True, 'removed_at': datetime.now()}}
        )

        # Get rarity
        rarity = character.get('rarity', '🟢 Common')
        if isinstance(rarity, str):
            rarity_parts = rarity.split(' ', 1)
            rarity_emoji = rarity_parts[0] if len(rarity_parts) > 0 else '🟢'
            rarity_text = rarity_parts[1] if len(rarity_parts) > 1 else 'Common'
        else:
            rarity_emoji = '🟢'
            rarity_text = 'Common'

        # Get current date and time
        now = datetime.now()
        date_str = now.strftime("%d/%m/%Y")
        time_str = now.strftime("%I:%M %p")

        # Get group info if available
        group_name = update.effective_chat.title if update.effective_chat.type in ['group', 'supergroup'] else "ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ"
        group_id = update.effective_chat.id

        # Send log to log chat
        try:
            log_caption = (
                f"<b>🗑 ᴄʜᴀʀᴀᴄᴛᴇʀ ʀᴇᴍᴏᴠᴇᴅ ʟᴏɢ</b>\n"
                f"{'='*30}\n\n"
                f"<b>👤 ʀᴇᴍᴏᴠᴇᴅ ʙʏ:</b>\n"
                f"• ɴᴀᴍᴇ: <a href='tg://user?id={user_id}'>{escape(update.effective_user.first_name)}</a>\n"
                f"• ᴜsᴇʀɴᴀᴍᴇ: @{update.effective_user.username or 'N/A'}\n"
                f"• ɪᴅ: <code>{user_id}</code>\n\n"
                f"<b>🎭 ᴄʜᴀʀᴀᴄᴛᴇʀ:</b>\n"
                f"• ɴᴀᴍᴇ: <code>{escape(character.get('name', 'Unknown'))}</code>\n"
                f"• ᴀɴɪᴍᴇ: <code>{escape(character.get('anime', 'Unknown'))}</code>\n"
                f"• ɪᴅ: <code>{character.get('id', 'N/A')}</code>\n"
                f"• ʀᴀʀɪᴛʏ: {rarity_emoji} <code>{rarity_text}</code>\n\n"
                f"<b>📍 ʟᴏᴄᴀᴛɪᴏɴ:</b>\n"
                f"• ɢʀᴏᴜᴘ: <code>{escape(group_name)}</code>\n"
                f"• ɢʀᴏᴜᴘ ɪᴅ: <code>{group_id}</code>\n\n"
                f"<b>🕐 ᴛɪᴍᴇsᴛᴀᴍᴘ:</b>\n"
                f"• ᴅᴀᴛᴇ: <code>{date_str}</code>\n"
                f"• ᴛɪᴍᴇ: <code>{time_str}</code>\n\n"
                f"🗑 <i>ᴄʜᴀʀᴀᴄᴛᴇʀ ʀᴇᴍᴏᴠᴇᴅ ғʀᴏᴍ ᴄɪʀᴄᴜʟᴀᴛɪᴏɴ!</i>"
            )

            await context.bot.send_photo(
                chat_id=LOG_CHAT_ID,
                photo=character.get('img_url', 'https://i.imgur.com/placeholder.png'),
                caption=log_caption,
                parse_mode='HTML'
            )
            LOGGER.info(f"[REMOVE CHR] Log sent to chat {LOG_CHAT_ID}")
        except Exception as log_error:
            LOGGER.error(f"[REMOVE CHR] Failed to send log: {log_error}")
            LOGGER.error(traceback.format_exc())

        # Send confirmation
        await update.message.reply_text(
            f"✅ <b>ᴄʜᴀʀᴀᴄᴛᴇʀ ʀᴇᴍᴏᴠᴇᴅ!</b>\n\n"
            f"🎭 <b>ɴᴀᴍᴇ:</b> <code>{character.get('name', 'Unknown')}</code>\n"
            f"🆔 <b>ɪᴅ:</b> <code>{character_id}</code>\n\n"
            f"<i>ᴛʜɪs ᴄʜᴀʀᴀᴄᴛᴇʀ ᴡɪʟʟ ɴᴏ ʟᴏɴɢᴇʀ sᴘᴀᴡɴ ɪɴ ɢʀᴏᴜᴘs.</i>",
            parse_mode='HTML'
        )

        LOGGER.info(f"[REMOVE CHR] Character {character_id} removed by {user_id}")

    except Exception as e:
        LOGGER.error(f"[REMOVE CHR ERROR] {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text(
            f"❌ <b>ᴇʀʀᴏʀ:</b> <code>{str(e)}</code>", 
            parse_mode='HTML'
        )


def register_remove_handlers():
    """Register remove character command handler"""
    application.add_handler(CommandHandler('remove_chr', remove_chr, block=False))
    LOGGER.info("[REMOVE CHR] Handler registered")