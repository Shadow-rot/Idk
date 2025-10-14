import traceback
from html import escape
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from shivu import application, user_collection, LOGGER

# Owner ID
OWNER_ID = 8420981179

# Log chat ID
LOG_CHAT_ID = -1003071132623


async def kill(update: Update, context: CallbackContext) -> None:
    """Remove all characters from user's collection (Owner only)"""
    user_id = update.effective_user.id

    LOGGER.info(f"[KILL] Command called by user {user_id}")

    # Check if owner
    if user_id != OWNER_ID:
        await update.message.reply_text("⚠️ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ᴏɴʟʏ ғᴏʀ ᴏᴡɴᴇʀ!")
        LOGGER.warning(f"[KILL] Unauthorized access attempt by user {user_id}")
        return

    # Check if reply to user or provided user ID
    target_user_id = None
    target_username = None
    target_first_name = None

    if update.message.reply_to_message:
        # Get from replied message
        target_user_id = update.message.reply_to_message.from_user.id
        target_username = update.message.reply_to_message.from_user.username
        target_first_name = update.message.reply_to_message.from_user.first_name
        LOGGER.info(f"[KILL] Target user from reply: {target_user_id}")
    elif context.args:
        # Get from command argument
        try:
            target_user_id = int(context.args[0])
            LOGGER.info(f"[KILL] Target user from argument: {target_user_id}")
        except ValueError:
            await update.message.reply_text(
                "❌ <b>ɪɴᴠᴀʟɪᴅ ᴜsᴇʀ ɪᴅ!</b>\n\n"
                "📝 <b>ᴜsᴀɢᴇ:</b>\n"
                "• Reply to user's message: <code>/kill</code>\n"
                "• Use user ID: <code>/kill user_id</code>",
                parse_mode='HTML'
            )
            return
    else:
        await update.message.reply_text(
            "📝 <b>ᴜsᴀɢᴇ:</b>\n"
            "• Reply to user's message: <code>/kill</code>\n"
            "• Use user ID: <code>/kill user_id</code>",
            parse_mode='HTML'
        )
        return

    try:
        # Find user in database
        user = await user_collection.find_one({'id': target_user_id})

        if not user:
            await update.message.reply_text(
                f"❌ <b>ᴜsᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ!</b>\n\n"
                f"🆔 ᴜsᴇʀ ɪᴅ: <code>{target_user_id}</code>",
                parse_mode='HTML'
            )
            LOGGER.warning(f"[KILL] User {target_user_id} not found in database")
            return

        # Get current characters
        characters = user.get('characters', [])
        character_count = len(characters)
        
        # If target info not from reply, get from database
        if not target_username:
            target_username = user.get('username', 'N/A')
        if not target_first_name:
            target_first_name = user.get('first_name', 'Unknown')

        LOGGER.info(f"[KILL] Current character count for user {target_user_id}: {character_count}")

        if character_count == 0:
            await update.message.reply_text(
                f"⚠️ <b>ᴜsᴇʀ ʜᴀs ɴᴏ ᴄʜᴀʀᴀᴄᴛᴇʀs!</b>\n\n"
                f"👤 ᴜsᴇʀ: <a href='tg://user?id={target_user_id}'>{escape(target_first_name)}</a>\n"
                f"🆔 ɪᴅ: <code>{target_user_id}</code>",
                parse_mode='HTML'
            )
            return

        # Get character details for logging (top 10)
        character_details = []
        for i, char in enumerate(characters[:10]):
            char_name = char.get('name', 'Unknown')
            char_anime = char.get('anime', 'Unknown')
            char_id = char.get('id', 'N/A')
            character_details.append(f"{i+1}. {char_name} ({char_anime}) - ID: {char_id}")

        # Remove all characters
        result = await user_collection.update_one(
            {'id': target_user_id},
            {'$set': {'characters': []}}
        )

        LOGGER.info(f"[KILL] Database update - modified={result.modified_count}")

        if result.modified_count > 0:
            # Send log to log chat
            try:
                from datetime import datetime
                now = datetime.now()
                date_str = now.strftime("%d/%m/%Y")
                time_str = now.strftime("%I:%M %p")

                # Get group info if available
                group_name = update.effective_chat.title if update.effective_chat.type in ['group', 'supergroup'] else "ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ"
                group_id = update.effective_chat.id

                # Character list for log
                char_list = "\n".join(character_details)
                if character_count > 10:
                    char_list += f"\n... ᴀɴᴅ {character_count - 10} ᴍᴏʀᴇ"

                log_caption = (
                    f"<b>💀 ᴄʜᴀʀᴀᴄᴛᴇʀs ᴡɪᴘᴇᴅ ʟᴏɢ</b>\n"
                    f"{'='*30}\n\n"
                    f"<b>👤 ᴇxᴇᴄᴜᴛᴇᴅ ʙʏ:</b>\n"
                    f"• ɴᴀᴍᴇ: <a href='tg://user?id={user_id}'>{escape(update.effective_user.first_name)}</a>\n"
                    f"• ᴜsᴇʀɴᴀᴍᴇ: @{update.effective_user.username or 'N/A'}\n"
                    f"• ɪᴅ: <code>{user_id}</code>\n\n"
                    f"<b>🎯 ᴛᴀʀɢᴇᴛ ᴜsᴇʀ:</b>\n"
                    f"• ɴᴀᴍᴇ: <a href='tg://user?id={target_user_id}'>{escape(target_first_name)}</a>\n"
                    f"• ᴜsᴇʀɴᴀᴍᴇ: @{target_username or 'N/A'}\n"
                    f"• ɪᴅ: <code>{target_user_id}</code>\n\n"
                    f"<b>🎭 ᴄʜᴀʀᴀᴄᴛᴇʀs ʀᴇᴍᴏᴠᴇᴅ:</b>\n"
                    f"• ᴛᴏᴛᴀʟ: <code>{character_count}</code> ᴄʜᴀʀᴀᴄᴛᴇʀs\n\n"
                    f"<b>📋 ᴛᴏᴘ 10 ᴄʜᴀʀᴀᴄᴛᴇʀs:</b>\n"
                    f"<code>{char_list}</code>\n\n"
                    f"<b>📍 ʟᴏᴄᴀᴛɪᴏɴ:</b>\n"
                    f"• ɢʀᴏᴜᴘ: <code>{escape(group_name)}</code>\n"
                    f"• ɢʀᴏᴜᴘ ɪᴅ: <code>{group_id}</code>\n\n"
                    f"<b>🕐 ᴛɪᴍᴇsᴛᴀᴍᴘ:</b>\n"
                    f"• ᴅᴀᴛᴇ: <code>{date_str}</code>\n"
                    f"• ᴛɪᴍᴇ: <code>{time_str}</code>\n\n"
                    f"💀 <i>ᴀʟʟ ᴄʜᴀʀᴀᴄᴛᴇʀs ᴡɪᴘᴇᴅ!</i>"
                )

                await context.bot.send_message(
                    chat_id=LOG_CHAT_ID,
                    text=log_caption,
                    parse_mode='HTML'
                )
                LOGGER.info(f"[KILL] Log sent to chat {LOG_CHAT_ID}")
            except Exception as log_error:
                LOGGER.error(f"[KILL] Failed to send log: {log_error}")
                LOGGER.error(traceback.format_exc())

            # Send confirmation
            await update.message.reply_text(
                f"✅ <b>ᴄʜᴀʀᴀᴄᴛᴇʀs ᴡɪᴘᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!</b>\n\n"
                f"<b>👤 ᴜsᴇʀ:</b> <a href='tg://user?id={target_user_id}'>{escape(target_first_name)}</a>\n"
                f"<b>🆔 ɪᴅ:</b> <code>{target_user_id}</code>\n\n"
                f"<b>🎭 ʀᴇᴍᴏᴠᴇᴅ:</b> <code>{character_count}</code> ᴄʜᴀʀᴀᴄᴛᴇʀs\n\n"
                f"<b>📋 ᴛᴏᴘ 10 ʀᴇᴍᴏᴠᴇᴅ ᴄʜᴀʀᴀᴄᴛᴇʀs:</b>\n"
                f"<code>{chr(10).join(character_details[:10])}</code>\n\n"
                f"<i>ᴀʟʟ ᴄʜᴀʀᴀᴄᴛᴇʀs ʜᴀᴠᴇ ʙᴇᴇɴ ʀᴇᴍᴏᴠᴇᴅ ғʀᴏᴍ ᴄᴏʟʟᴇᴄᴛɪᴏɴ.</i>",
                parse_mode='HTML'
            )

            LOGGER.info(f"[KILL] Successfully removed {character_count} characters from user {target_user_id}")

        else:
            await update.message.reply_text(
                "❌ <b>ғᴀɪʟᴇᴅ ᴛᴏ ʀᴇᴍᴏᴠᴇ ᴄʜᴀʀᴀᴄᴛᴇʀs!</b>",
                parse_mode='HTML'
            )
            LOGGER.error(f"[KILL] Failed to remove characters for user {target_user_id}")

    except Exception as e:
        LOGGER.error(f"[KILL ERROR] {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text(
            f"❌ <b>ᴇʀʀᴏʀ:</b> <code>{str(e)}</code>",
            parse_mode='HTML'
        )


def register_kill_handler():
    """Register kill command handler"""
    application.add_handler(CommandHandler('kill', kill, block=False))
    LOGGER.info("[KILL] Handler registered")