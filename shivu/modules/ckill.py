import traceback
from html import escape
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from shivu import application, user_collection, LOGGER

# Owner ID
OWNER_ID = 5147822244

# Log chat ID
LOG_CHAT_ID = -1003071132623


async def ckill(update: Update, context: CallbackContext) -> None:
    """Remove user's balance (wallet + bank) to 0 (Owner only)"""
    user_id = update.effective_user.id

    LOGGER.info(f"[CKILL] Command called by user {user_id}")

    # Check if owner
    if user_id != OWNER_ID:
        await update.message.reply_text("⚠️ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ᴏɴʟʏ ғᴏʀ ᴏᴡɴᴇʀ!")
        LOGGER.warning(f"[CKILL] Unauthorized access attempt by user {user_id}")
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
        LOGGER.info(f"[CKILL] Target user from reply: {target_user_id}")
    elif context.args:
        # Get from command argument
        try:
            target_user_id = int(context.args[0])
            LOGGER.info(f"[CKILL] Target user from argument: {target_user_id}")
        except ValueError:
            await update.message.reply_text(
                "❌ <b>ɪɴᴠᴀʟɪᴅ ᴜsᴇʀ ɪᴅ!</b>\n\n"
                "📝 <b>ᴜsᴀɢᴇ:</b>\n"
                "• Reply to user's message: <code>/ckill</code>\n"
                "• Use user ID: <code>/ckill user_id</code>",
                parse_mode='HTML'
            )
            return
    else:
        await update.message.reply_text(
            "📝 <b>ᴜsᴀɢᴇ:</b>\n"
            "• Reply to user's message: <code>/ckill</code>\n"
            "• Use user ID: <code>/ckill user_id</code>",
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
            LOGGER.warning(f"[CKILL] User {target_user_id} not found in database")
            return

        # Get current balances
        wallet_balance = user.get('balance', 0)
        bank_balance = user.get('bank', 0)
        total_balance = wallet_balance + bank_balance
        
        # If target info not from reply, get from database
        if not target_username:
            target_username = user.get('username', 'N/A')
        if not target_first_name:
            target_first_name = user.get('first_name', 'Unknown')

        LOGGER.info(f"[CKILL] Current balance for user {target_user_id} - Wallet: {wallet_balance}, Bank: {bank_balance}, Total: {total_balance}")

        # Update both balance and bank to 0
        result = await user_collection.update_one(
            {'id': target_user_id},
            {'$set': {'balance': 0, 'bank': 0}}
        )

        LOGGER.info(f"[CKILL] Database update - modified={result.modified_count}")

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

                log_caption = (
                    f"<b>💰 ʙᴀʟᴀɴᴄᴇ ʀᴇsᴇᴛ ʟᴏɢ</b>\n"
                    f"{'='*30}\n\n"
                    f"<b>👤 ᴇxᴇᴄᴜᴛᴇᴅ ʙʏ:</b>\n"
                    f"• ɴᴀᴍᴇ: <a href='tg://user?id={user_id}'>{escape(update.effective_user.first_name)}</a>\n"
                    f"• ᴜsᴇʀɴᴀᴍᴇ: @{update.effective_user.username or 'N/A'}\n"
                    f"• ɪᴅ: <code>{user_id}</code>\n\n"
                    f"<b>🎯 ᴛᴀʀɢᴇᴛ ᴜsᴇʀ:</b>\n"
                    f"• ɴᴀᴍᴇ: <a href='tg://user?id={target_user_id}'>{escape(target_first_name)}</a>\n"
                    f"• ᴜsᴇʀɴᴀᴍᴇ: @{target_username or 'N/A'}\n"
                    f"• ɪᴅ: <code>{target_user_id}</code>\n\n"
                    f"<b>💸 ʙᴀʟᴀɴᴄᴇ ᴄʜᴀɴɢᴇ:</b>\n"
                    f"• 💰 ᴡᴀʟʟᴇᴛ: <code>{wallet_balance:,}</code> → <code>0</code> 🪙\n"
                    f"• 💳 ʙᴀɴᴋ: <code>{bank_balance:,}</code> → <code>0</code> 🪙\n"
                    f"• 📊 ᴛᴏᴛᴀʟ ʀᴇᴍᴏᴠᴇᴅ: <code>{total_balance:,}</code> 🪙\n\n"
                    f"<b>📍 ʟᴏᴄᴀᴛɪᴏɴ:</b>\n"
                    f"• ɢʀᴏᴜᴘ: <code>{escape(group_name)}</code>\n"
                    f"• ɢʀᴏᴜᴘ ɪᴅ: <code>{group_id}</code>\n\n"
                    f"<b>🕐 ᴛɪᴍᴇsᴛᴀᴍᴘ:</b>\n"
                    f"• ᴅᴀᴛᴇ: <code>{date_str}</code>\n"
                    f"• ᴛɪᴍᴇ: <code>{time_str}</code>\n\n"
                    f"💀 <i>ᴀʟʟ ʙᴀʟᴀɴᴄᴇs ʀᴇsᴇᴛ ᴛᴏ 0!</i>"
                )

                await context.bot.send_message(
                    chat_id=LOG_CHAT_ID,
                    text=log_caption,
                    parse_mode='HTML'
                )
                LOGGER.info(f"[CKILL] Log sent to chat {LOG_CHAT_ID}")
            except Exception as log_error:
                LOGGER.error(f"[CKILL] Failed to send log: {log_error}")
                LOGGER.error(traceback.format_exc())

            # Send confirmation
            await update.message.reply_text(
                f"✅ <b>ʙᴀʟᴀɴᴄᴇ ʀᴇsᴇᴛ sᴜᴄᴄᴇssғᴜʟʟʏ!</b>\n\n"
                f"<b>👤 ᴜsᴇʀ:</b> <a href='tg://user?id={target_user_id}'>{escape(target_first_name)}</a>\n"
                f"<b>🆔 ɪᴅ:</b> <code>{target_user_id}</code>\n\n"
                f"<b>💸 ᴘʀᴇᴠɪᴏᴜs ʙᴀʟᴀɴᴄᴇs:</b>\n"
                f"• 💰 ᴡᴀʟʟᴇᴛ: <code>{wallet_balance:,}</code> 🪙\n"
                f"• 💳 ʙᴀɴᴋ: <code>{bank_balance:,}</code> 🪙\n"
                f"• 📊 ᴛᴏᴛᴀʟ: <code>{total_balance:,}</code> 🪙\n\n"
                f"<b>💰 ɴᴇᴡ ʙᴀʟᴀɴᴄᴇ:</b> <code>0</code> 🪙\n\n"
                f"<i>ᴀʟʟ ɢᴏʟᴅ ᴄᴏɪɴs ʜᴀᴠᴇ ʙᴇᴇɴ ʀᴇᴍᴏᴠᴇᴅ.</i>",
                parse_mode='HTML'
            )

            LOGGER.info(f"[CKILL] Successfully reset balance for user {target_user_id} - Removed {total_balance} coins")

        else:
            await update.message.reply_text(
                "❌ <b>ғᴀɪʟᴇᴅ ᴛᴏ ᴜᴘᴅᴀᴛᴇ ʙᴀʟᴀɴᴄᴇ!</b>",
                parse_mode='HTML'
            )
            LOGGER.error(f"[CKILL] Failed to update balance for user {target_user_id}")

    except Exception as e:
        LOGGER.error(f"[CKILL ERROR] {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text(
            f"❌ <b>ᴇʀʀᴏʀ:</b> <code>{str(e)}</code>",
            parse_mode='HTML'
        )


def register_ckill_handler():
    """Register ckill command handler"""
    application.add_handler(CommandHandler('ckill', ckill, block=False))
    LOGGER.info("[CKILL] Handler registered")