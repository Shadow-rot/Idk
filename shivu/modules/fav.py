import traceback
from html import escape
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler

from shivu import application, user_collection, LOGGER

# Log chat ID
LOG_CHAT_ID = -1003071132623


async def fav(update: Update, context: CallbackContext) -> None:
    """Set a character as favorite"""
    user_id = update.effective_user.id

    LOGGER.info(f"[FAV] Command called by user {user_id}")

    if not context.args:
        await update.message.reply_text('𝙋𝙡𝙚𝙖𝙨𝙚 𝙥𝙧𝙤𝙫𝙞𝙙𝙚 𝙒𝘼𝙄𝙁𝙐 𝙞𝙙...')
        return

    character_id = str(context.args[0])

    try:
        user = await user_collection.find_one({'id': user_id})
        if not user:
            LOGGER.warning(f"[FAV] User {user_id} not found in database")
            await update.message.reply_text('𝙔𝙤𝙪 𝙝𝙖𝙫𝙚 𝙣𝙤𝙩 𝙂𝙤𝙩 𝘼𝙣𝙮 𝙒𝘼𝙄𝙁𝙐 𝙮𝙚𝙩...')
            return

        character = next(
            (c for c in user.get('characters', []) if str(c.get('id')) == character_id),
            None
        )

        if not character:
            LOGGER.warning(f"[FAV] Character {character_id} not found for user {user_id}")
            await update.message.reply_text('𝙏𝙝𝙞𝙨 𝙒𝘼𝙄𝙁𝙐 𝙞𝙨 𝙉𝙤𝙩 𝙄𝙣 𝙮𝙤𝙪𝙧 𝙒𝘼𝙄𝙁𝙐 𝙡𝙞𝙨𝙩')
            return

        # Use same callback format as gift
        buttons = [
            [
                InlineKeyboardButton("✅ ʏᴇs", callback_data=f"fvc_{user_id}_{character_id}"),
                InlineKeyboardButton("❌ ɴᴏ", callback_data=f"fvx_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)

        await update.message.reply_photo(
            photo=character.get("img_url", ""),
            caption=(
                f"<b>💖 ᴅᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴍᴀᴋᴇ ᴛʜɪs ᴡᴀɪғᴜ ʏᴏᴜʀ ғᴀᴠᴏʀɪᴛᴇ?</b>\n\n"
                f"✨ <b>ɴᴀᴍᴇ:</b> <code>{character.get('name', 'Unknown')}</code>\n"
                f"📺 <b>ᴀɴɪᴍᴇ:</b> <code>{character.get('anime', 'Unknown')}</code>\n"
                f"🆔 <b>ɪᴅ:</b> <code>{character.get('id', 'Unknown')}</code>"
            ),
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        LOGGER.info(f"[FAV] Confirmation message sent for user {user_id}, character {character_id}")

    except Exception as e:
        LOGGER.error(f"[FAV ERROR] Command failed: {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text('ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴡʜɪʟᴇ ᴘʀᴏᴄᴇssɪɴɢ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ.')


async def handle_fav_callback(update: Update, context: CallbackContext) -> None:
    """Handle favorite button callbacks"""
    query = update.callback_query

    try:
        LOGGER.info(f"[FAV CALLBACK] Received: {query.data} from user {query.from_user.id}")
        
        # Answer callback immediately
        await query.answer()

        # Extract data from callback
        data = query.data
        
        # Check if it's a fav callback
        if not (data.startswith('fvc_') or data.startswith('fvx_')):
            LOGGER.info(f"[FAV CALLBACK] Not a fav callback: {data}")
            return

        # Parse callback data
        parts = data.split('_', 2)
        if len(parts) < 2:
            LOGGER.error(f"[FAV CALLBACK] Malformed data: {data}")
            await query.answer("❌ ɪɴᴠᴀʟɪᴅ ᴄᴀʟʟʙᴀᴄᴋ ᴅᴀᴛᴀ!", show_alert=True)
            return

        action_code = parts[0]  # 'fvc' (confirm) or 'fvx' (cancel)
        
        LOGGER.info(f"[FAV CALLBACK] Action: {action_code}, Parts: {parts}")

        if action_code == 'fvc':  # Confirm
            if len(parts) != 3:
                LOGGER.error(f"[FAV CALLBACK] Invalid parts length: {len(parts)}")
                await query.answer("❌ ɪɴᴠᴀʟɪᴅ ᴅᴀᴛᴀ!", show_alert=True)
                return
            
            user_id = int(parts[1])
            character_id = str(parts[2])

            LOGGER.info(f"[FAV CALLBACK] Processing confirmation - user={user_id}, char={character_id}")

            # Verify user
            if query.from_user.id != user_id:
                LOGGER.warning(f"[FAV CALLBACK] Unauthorized access attempt by {query.from_user.id} for user {user_id}")
                await query.answer("⚠️ ᴛʜɪs ɪs ɴᴏᴛ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ!", show_alert=True)
                return

            # Get character info before updating
            user = await user_collection.find_one({'id': user_id})
            if not user:
                LOGGER.error(f"[FAV CALLBACK] User {user_id} not found in database")
                await query.answer("❌ ᴜsᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ!", show_alert=True)
                return

            character = next(
                (c for c in user.get('characters', []) if str(c.get('id')) == character_id),
                None
            )

            if not character:
                LOGGER.error(f"[FAV CALLBACK] Character {character_id} not found for user {user_id}")
                await query.answer("❌ ᴄʜᴀʀᴀᴄᴛᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ!", show_alert=True)
                return

            LOGGER.info(f"[FAV CALLBACK] Character found: {character.get('name', 'Unknown')}")

            # Update favorite
            result = await user_collection.update_one(
                {'id': user_id},
                {'$set': {'favorites': character_id}},
                upsert=True
            )

            LOGGER.info(f"[FAV CALLBACK] Database update - modified={result.modified_count}, upserted={result.upserted_id}")

            if result.modified_count > 0 or result.upserted_id:
                # Get rarity
                rarity = character.get('rarity', '🟢 Common')
                if isinstance(rarity, str):
                    rarity_parts = rarity.split(' ', 1)
                    rarity_emoji = rarity_parts[0] if len(rarity_parts) > 0 else '🟢'
                    rarity_text = rarity_parts[1] if len(rarity_parts) > 1 else 'Common'
                else:
                    rarity_emoji = '🟢'
                    rarity_text = 'Common'

                # Send log to log chat
                try:
                    log_caption = (
                        f"<b>💖 ғᴀᴠᴏʀɪᴛᴇ sᴇᴛ ʟᴏɢ</b>\n"
                        f"{'='*30}\n\n"
                        f"<b>👤 ᴜsᴇʀ:</b>\n"
                        f"• ɴᴀᴍᴇ: <a href='tg://user?id={user_id}'>{escape(query.from_user.first_name)}</a>\n"
                        f"• ᴜsᴇʀɴᴀᴍᴇ: @{query.from_user.username or 'N/A'}\n"
                        f"• ɪᴅ: <code>{user_id}</code>\n\n"
                        f"<b>💝 ᴄʜᴀʀᴀᴄᴛᴇʀ:</b>\n"
                        f"• ɴᴀᴍᴇ: <code>{escape(character.get('name', 'Unknown'))}</code>\n"
                        f"• ᴀɴɪᴍᴇ: <code>{escape(character.get('anime', 'Unknown'))}</code>\n"
                        f"• ɪᴅ: <code>{character.get('id', 'N/A')}</code>\n"
                        f"• ʀᴀʀɪᴛʏ: {rarity_emoji} <code>{rarity_text}</code>\n\n"
                        f"✅ <i>ғᴀᴠᴏʀɪᴛᴇ sᴇᴛ sᴜᴄᴄᴇssғᴜʟʟʏ!</i>"
                    )

                    await context.bot.send_photo(
                        chat_id=LOG_CHAT_ID,
                        photo=character.get('img_url', 'https://i.imgur.com/placeholder.png'),
                        caption=log_caption,
                        parse_mode='HTML'
                    )
                    LOGGER.info(f"[FAV CALLBACK] Log sent to chat {LOG_CHAT_ID}")
                except Exception as log_error:
                    LOGGER.error(f"[FAV CALLBACK] Failed to send log: {log_error}")
                    LOGGER.error(traceback.format_exc())

                # Update message
                await query.edit_message_caption(
                    caption=(
                        f"<b>✅ sᴜᴄᴄᴇss!</b>\n\n"
                        f"💖 ᴡᴀɪғᴜ ᴍᴀʀᴋᴇᴅ ᴀs ʏᴏᴜʀ ғᴀᴠᴏʀɪᴛᴇ!\n"
                        f"🆔 ᴄʜᴀʀᴀᴄᴛᴇʀ ɪᴅ: <code>{character_id}</code>\n\n"
                        f"<i>ʏᴏᴜʀ ғᴀᴠᴏʀɪᴛᴇ ᴡɪʟʟ ʙᴇ sʜᴏᴡɴ ɪɴ ɪɴʟɪɴᴇ ǫᴜᴇʀɪᴇs!</i>"
                    ),
                    parse_mode='HTML'
                )
                LOGGER.info(f"[FAV CALLBACK] Favorite set successfully for user {user_id}")
            else:
                LOGGER.error(f"[FAV CALLBACK] Database update failed - no changes made")
                await query.edit_message_caption(
                    caption="❌ ғᴀɪʟᴇᴅ ᴛᴏ sᴇᴛ ғᴀᴠᴏʀɪᴛᴇ. ᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ.",
                    parse_mode='HTML'
                )

        elif action_code == 'fvx':  # Cancel
            user_id = int(parts[1])

            LOGGER.info(f"[FAV CALLBACK] Cancel requested by user {user_id}")

            if query.from_user.id != user_id:
                LOGGER.warning(f"[FAV CALLBACK] Unauthorized cancel attempt by {query.from_user.id}")
                await query.answer("⚠️ ᴛʜɪs ɪs ɴᴏᴛ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ!", show_alert=True)
                return

            await query.edit_message_caption(
                caption="❌ ᴀᴄᴛɪᴏɴ ᴄᴀɴᴄᴇʟᴇᴅ. ɴᴏ ᴄʜᴀɴɢᴇs ᴍᴀᴅᴇ.",
                parse_mode='HTML'
            )
            LOGGER.info(f"[FAV CALLBACK] Action cancelled by user {user_id}")

    except Exception as e:
        LOGGER.error(f"[FAV CALLBACK] Callback handler failed: {e}")
        LOGGER.error(traceback.format_exc())
        try:
            await query.answer(f"❌ ᴇʀʀᴏʀ: {str(e)}", show_alert=True)
        except:
            pass


def register_fav_handlers():
    """Register favorite command and callback handlers"""
    application.add_handler(CommandHandler('fav', fav, block=False))
    application.add_handler(CallbackQueryHandler(handle_fav_callback, pattern="^fv[cx]_", block=False))
    LOGGER.info("[FAV] Favorite handlers registered with pattern ^fv[cx]_")