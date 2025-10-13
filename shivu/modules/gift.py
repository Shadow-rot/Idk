from pyrogram import Client, filters
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import shivuu as bot, LOGGER
from telegram.ext import MessageHandler, filters as ptb_filters
from shivu import user_collection, application
from html import escape
import traceback

# Store pending gifts
pending_gifts = {}

async def handle_gift_command(update: Update, context: CallbackContext):
    """Handle the /gift command"""
    try:
        message = update.message
        sender_id = message.from_user.id

        LOGGER.info(f"Gift command called by user {sender_id}")

        # Check if replying to a message
        if not message.reply_to_message:
            await message.reply_text(
                "<b>❌ You need to reply to someone's message to gift!</b>",
                parse_mode='HTML'
            )
            return

        # Get receiver info
        receiver_id = message.reply_to_message.from_user.id
        receiver_username = message.reply_to_message.from_user.username
        receiver_first_name = escape(message.reply_to_message.from_user.first_name)

        # Check if gifting to self
        if sender_id == receiver_id:
            await message.reply_text(
                "<b>❌ You can't gift characters to yourself!</b>",
                parse_mode='HTML'
            )
            return

        # Check command format
        if len(context.args) != 1:
            await message.reply_text(
                "<b>❌ Usage:</b> Reply with <code>/gift character_id</code>",
                parse_mode='HTML'
            )
            return

        character_id = context.args[0]

        # Get sender's data
        sender = await user_collection.find_one({'id': sender_id})
        if not sender:
            await message.reply_text(
                "<b>❌ You don't have any characters to gift!</b>",
                parse_mode='HTML'
            )
            return

        # Find character in sender's collection
        character = None
        for char in sender.get('characters', []):
            if isinstance(char, dict) and str(char.get('id')) == str(character_id):
                character = char
                break

        if not character:
            await message.reply_text(
                "<b>❌ You don't own this character!</b>",
                parse_mode='HTML'
            )
            return

        # Check pending gifts
        if sender_id in pending_gifts:
            await message.reply_text(
                "<b>❌ You already have a pending gift!\nPlease confirm or cancel it first.</b>",
                parse_mode='HTML'
            )
            return

        # Store gift info
        pending_gifts[sender_id] = {
            'character': character,
            'receiver_id': receiver_id,
            'receiver_username': receiver_username,
            'receiver_first_name': receiver_first_name
        }

        LOGGER.info(f"Pending gift stored for user {sender_id}")

        # Get character rarity
        rarity = character.get('rarity', '🟢 Common')
        if isinstance(rarity, str):
            rarity_parts = rarity.split(' ', 1)
            rarity_emoji = rarity_parts[0] if len(rarity_parts) > 0 else '🟢'
            rarity_text = rarity_parts[1] if len(rarity_parts) > 1 else 'Common'
        else:
            rarity_emoji = '🟢'
            rarity_text = 'Common'

        # Create confirmation message with simpler callback data
        caption = (
            f"<b>🎁 Gift Confirmation</b>\n\n"
            f"<b>To:</b> <a href='tg://user?id={receiver_id}'>{receiver_first_name}</a>\n\n"
            f"<b>Character Details:</b>\n"
            f"• <b>Name:</b> <code>{escape(character['name'])}</code>\n"
            f"• <b>Anime:</b> <code>{escape(character['anime'])}</code>\n"
            f"• <b>ID:</b> <code>{character['id']}</code>\n"
            f"• <b>Rarity:</b> {rarity_emoji} <code>{rarity_text}</code>\n\n"
            f"<i>Are you sure you want to gift this character?</i>"
        )

        # Create confirmation buttons
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"giftconfirm_{sender_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"giftcancel_{sender_id}")
            ]
        ]

        await message.reply_photo(
            photo=character['img_url'],
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

        LOGGER.info(f"Gift confirmation message sent for user {sender_id}")

    except Exception as e:
        LOGGER.error(f"Error in gift command: {e}")
        LOGGER.error(traceback.format_exc())
        await message.reply_text(
            f"<b>❌ An error occurred!</b>\n<code>{str(e)}</code>",
            parse_mode='HTML'
        )

async def handle_gift_callback(update: Update, context: CallbackContext):
    """Handle gift confirmation callbacks"""
    query = update.callback_query
    
    try:
        await query.answer()  # Answer immediately to prevent timeout
        
        LOGGER.info(f"Callback received: {query.data} from user {query.from_user.id}")

        # Extract data from callback
        data = query.data
        
        if not (data.startswith('giftconfirm_') or data.startswith('giftcancel_')):
            LOGGER.warning(f"Invalid callback data: {data}")
            return

        # Parse callback data
        parts = data.split('_')
        if len(parts) != 2:
            LOGGER.error(f"Malformed callback data: {data}")
            await query.answer("❌ Invalid callback data!", show_alert=True)
            return

        action = parts[0].replace('gift', '')  # 'confirm' or 'cancel'
        user_id = int(parts[1])

        LOGGER.info(f"Parsed action: {action}, user_id: {user_id}")

        # Verify user
        if query.from_user.id != user_id:
            await query.answer("⚠️ This is not your gift confirmation!", show_alert=True)
            return

        if user_id not in pending_gifts:
            await query.answer("❌ No pending gift found!", show_alert=True)
            LOGGER.warning(f"No pending gift for user {user_id}")
            return

        gift_data = pending_gifts[user_id]

        if action == "confirm":
            LOGGER.info(f"Processing gift confirmation for user {user_id}")
            try:
                # Get sender and receiver data
                sender = await user_collection.find_one({'id': user_id})
                receiver = await user_collection.find_one({'id': gift_data['receiver_id']})
                character = gift_data['character']

                LOGGER.info(f"Sender found: {sender is not None}, Receiver found: {receiver is not None}")

                # Remove from sender
                result = await user_collection.update_one(
                    {'id': user_id},
                    {'$pull': {'characters': {'id': character['id']}}}
                )
                LOGGER.info(f"Character removed from sender: {result.modified_count} docs modified")

                # Add to receiver
                if receiver:
                    result = await user_collection.update_one(
                        {'id': gift_data['receiver_id']},
                        {'$push': {'characters': character}}
                    )
                    LOGGER.info(f"Character added to receiver: {result.modified_count} docs modified")
                else:
                    await user_collection.insert_one({
                        'id': gift_data['receiver_id'],
                        'username': gift_data['receiver_username'],
                        'first_name': gift_data['receiver_first_name'],
                        'characters': [character]
                    })
                    LOGGER.info(f"New receiver document created")

                success_msg = (
                    f"✅ <b>Gift Successful!</b>\n\n"
                    f"<code>{escape(character['name'])}</code> has been gifted to "
                    f"<a href='tg://user?id={gift_data['receiver_id']}'>{gift_data['receiver_first_name']}</a>!"
                )

                await query.edit_message_caption(
                    caption=success_msg,
                    parse_mode='HTML'
                )

                LOGGER.info(f"Gift successfully processed for user {user_id}")

            except Exception as e:
                LOGGER.error(f"Error processing gift: {e}")
                LOGGER.error(traceback.format_exc())
                await query.edit_message_caption(
                    caption=f"❌ <b>Failed to process gift!</b>\n<code>{str(e)}</code>",
                    parse_mode='HTML'
                )

        elif action == "cancel":
            LOGGER.info(f"Gift cancelled by user {user_id}")
            await query.edit_message_caption(
                caption="❌ <b>Gift cancelled!</b>",
                parse_mode='HTML'
            )

        # Clean up
        if user_id in pending_gifts:
            del pending_gifts[user_id]
            LOGGER.info(f"Pending gift removed for user {user_id}")

    except Exception as e:
        LOGGER.error(f"Error in gift callback: {e}")
        LOGGER.error(traceback.format_exc())
        try:
            await query.answer(f"❌ An error occurred: {str(e)}", show_alert=True)
        except:
            pass

def register_handlers():
    """Register command and callback handlers"""
    # Remove any existing handlers with same pattern
    application.add_handler(CommandHandler("gift", handle_gift_command))
    application.add_handler(CallbackQueryHandler(handle_gift_callback, pattern=r"^gift"))

# Register handlers
register_handlers()

LOGGER.info("Gift handlers registered successfully")