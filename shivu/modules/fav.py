import traceback
from html import escape
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler

from shivu import db, LOGGER

# Database collection
user_collection = db['user_collection_lmaoooo']


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

        # Create confirmation buttons
        buttons = [
            [
                InlineKeyboardButton("✅ ʏᴇs", callback_data=f"fc_{user_id}_{character_id}"),
                InlineKeyboardButton("❌ ɴᴏ", callback_data=f"fx_{user_id}")
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
        if not (data.startswith('fc_') or data.startswith('fx_')):
            LOGGER.info(f"[FAV CALLBACK] Not a fav callback: {data}")
            return

        # Parse callback data
        parts = data.split('_', 2)
        if len(parts) < 2:
            LOGGER.error(f"[FAV CALLBACK] Malformed data: {data}")
            await query.answer("❌ ɪɴᴠᴀʟɪᴅ ᴄᴀʟʟʙᴀᴄᴋ ᴅᴀᴛᴀ!", show_alert=True)
            return

        action_code = parts[0]  # 'fc' (confirm) or 'fx' (cancel)

        LOGGER.info(f"[FAV CALLBACK] Action: {action_code}, Parts: {parts}")

        if action_code == 'fc':  # Confirm
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

            # Get user and character
            user = await user_collection.find_one({'id': user_id})
            if not user:
                await query.answer("❌ ᴜsᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ!", show_alert=True)
                return

            character = next(
                (c for c in user.get('characters', []) if str(c.get('id')) == character_id),
                None
            )

            if not character:
                await query.answer("❌ ᴄʜᴀʀᴀᴄᴛᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ!", show_alert=True)
                return

            # Update favorite character
            await user_collection.update_one(
                {'id': user_id},
                {'$set': {'favorites': character}}
            )

            # Get rarity information
            rarity = character.get('rarity', '🟢 Common')
            if isinstance(rarity, str):
                rarity_parts = rarity.split(' ', 1)
                rarity_emoji = rarity_parts[0] if len(rarity_parts) > 0 else '🟢'
                rarity_text = rarity_parts[1] if len(rarity_parts) > 1 else 'Common'
            else:
                rarity_emoji = '🟢'
                rarity_text = 'Common'

            # Edit message with success
            await query.edit_message_caption(
                caption=(
                    f"<b>✅ sᴜᴄᴄᴇssғᴜʟʟʏ sᴇᴛ ᴀs ғᴀᴠᴏʀɪᴛᴇ!</b>\n\n"
                    f"💖 <b>ɴᴀᴍᴇ:</b> <code>{character.get('name', 'Unknown')}</code>\n"
                    f"📺 <b>ᴀɴɪᴍᴇ:</b> <code>{character.get('anime', 'Unknown')}</code>\n"
                    f"{rarity_emoji} <b>ʀᴀʀɪᴛʏ:</b> <code>{rarity_text}</code>\n"
                    f"🆔 <b>ɪᴅ:</b> <code>{character.get('id', 'Unknown')}</code>"
                ),
                parse_mode='HTML'
            )

            LOGGER.info(f"[FAV CALLBACK] Successfully set favorite for user {user_id}")

        elif action_code == 'fx':  # Cancel
            user_id = int(parts[1])

            # Verify user
            if query.from_user.id != user_id:
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


def register_fav_handlers(application):
    """Register favorite command handlers"""
    application.add_handler(CommandHandler('fav', fav, block=False))
    application.add_handler(CallbackQueryHandler(handle_fav_callback, pattern="^f[cx]_", block=False))
    LOGGER.info("[FAV] Favorite command handlers registered")