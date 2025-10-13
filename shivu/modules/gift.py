from pyrogram import Client, filters
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import shivuu as bot, LOGGER
from telegram.ext import MessageHandler, filters
from shivu import user_collection, application
from html import escape

# Store pending gifts
pending_gifts = {}

async def handle_gift_command(update: Update, context: CallbackContext):
    """Handle the /gift command"""
    try:
        message = update.message
        sender_id = message.from_user.id

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

        # Get character rarity
        rarity = character.get('rarity', '🟢 Common')
        if isinstance(rarity, str):
            rarity_parts = rarity.split(' ', 1)
            rarity_emoji = rarity_parts[0] if len(rarity_parts) > 0 else '🟢'
            rarity_text = rarity_parts[1] if len(rarity_parts) > 1 else 'Common'
        else:
            rarity_emoji = '🟢'
            rarity_text = 'Common'

        # Create confirmation message with user-specific callback data
        callback_base = f"{sender_id}"
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

        # Create confirmation buttons with user-specific callback data
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"gift_confirm_{callback_base}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"gift_cancel_{callback_base}")
            ]
        ]

        await message.reply_photo(
            photo=character['img_url'],
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

    except Exception as e:
        LOGGER.error(f"Error in gift command: {e}")
        await message.reply_text(
            "<b>❌ An error occurred!</b>",
            parse_mode='HTML'
        )

async def handle_gift_callback(update: Update, context: CallbackContext):
    """Handle gift confirmation callbacks"""
    query = update.callback_query
    
    try:
        # Extract data from callback
        data = query.data
        if not data.startswith(('gift_confirm_', 'gift_cancel_')):
            return
        
        user_id = int(data.split('_')[-1])
        action = data.split('_')[1]  # confirm or cancel

        # Verify user
        if query.from_user.id != user_id:
            await query.answer("⚠️ This is not your gift confirmation!", show_alert=True)
            return

        if user_id not in pending_gifts:
            await query.answer("❌ No pending gift found!", show_alert=True)
            return

        gift_data = pending_gifts[user_id]
        
        if action == "confirm":
            try:
                # Get sender and receiver data
                sender = await user_collection.find_one({'id': user_id})
                receiver = await user_collection.find_one({'id': gift_data['receiver_id']})
                character = gift_data['character']

                # Remove from sender
                await user_collection.update_one(
                    {'id': user_id},
                    {'$pull': {'characters': {'id': character['id']}}}
                )

                # Add to receiver
                if receiver:
                    await user_collection.update_one(
                        {'id': gift_data['receiver_id']},
                        {'$push': {'characters': character}}
                    )
                else:
                    await user_collection.insert_one({
                        'id': gift_data['receiver_id'],
                        'username': gift_data['receiver_username'],
                        'first_name': gift_data['receiver_first_name'],
                        'characters': [character]
                    })

                await query.edit_message_caption(
                    caption=f"✅ Successfully gifted {character['name']} to {gift_data['receiver_first_name']}!",
                    parse_mode='HTML'
                )

            except Exception as e:
                LOGGER.error(f"Error processing gift: {e}")
                await query.edit_message_caption(
                    caption="❌ Failed to process gift!",
                    parse_mode='HTML'
                )

        elif action == "cancel":
            await query.edit_message_caption(
                caption="❌ Gift cancelled!",
                parse_mode='HTML'
            )

        # Clean up
        if user_id in pending_gifts:
            del pending_gifts[user_id]

    except Exception as e:
        LOGGER.error(f"Error in gift callback: {e}")
        await query.answer("❌ An error occurred!", show_alert=True)

def register_handlers():
    """Register command and callback handlers"""
    application.add_handler(CommandHandler("gift", handle_gift_command))
    application.add_handler(CallbackQueryHandler(handle_gift_callback, pattern=r"^gift_"))

# Register handlers
register_handlers()