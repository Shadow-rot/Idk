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

        # Create confirmation message
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
                InlineKeyboardButton("✅ Confirm", callback_data="confirm_gift"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_gift")
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
    user_id = query.from_user.id

    try:
        await query.answer()

        if user_id not in pending_gifts:
            await query.edit_message_caption(
                caption="❌ No pending gift found!",
                parse_mode='HTML'
            )
            return

        gift_data = pending_gifts[user_id]
        receiver_id = gift_data['receiver_id']
        character = gift_data['character']

        if query.data == "confirm_gift":
            # Get sender and receiver data
            sender = await user_collection.find_one({'id': user_id})
            receiver = await user_collection.find_one({'id': receiver_id})

            if not sender:
                await query.edit_message_caption(
                    caption="❌ Error: Sender data not found!",
                    parse_mode='HTML'
                )
                return

            # Remove character from sender
            await user_collection.update_one(
                {'id': user_id},
                {'$pull': {'characters': {'id': character['id']}}}
            )

            # Add character to receiver
            if receiver:
                await user_collection.update_one(
                    {'id': receiver_id},
                    {'$push': {'characters': character}}
                )
            else:
                # Create new user entry for receiver
                await user_collection.insert_one({
                    'id': receiver_id,
                    'username': gift_data['receiver_username'],
                    'first_name': gift_data['receiver_first_name'],
                    'characters': [character]
                })

            # Clear pending gift
            del pending_gifts[user_id]

            await query.edit_message_caption(
                caption=(
                    f"<b>✅ Gift Sent Successfully!</b>\n\n"
                    f"<b>Character:</b> <code>{escape(character['name'])}</code>\n"
                    f"<b>To:</b> <a href='tg://user?id={receiver_id}'>{escape(gift_data['receiver_first_name'])}</a>"
                ),
                parse_mode='HTML'
            )

        elif query.data == "cancel_gift":
            del pending_gifts[user_id]
            await query.edit_message_caption(
                caption="❌ Gift cancelled!",
                parse_mode='HTML'
            )

    except Exception as e:
        LOGGER.error(f"Error in gift callback: {e}")
        await query.edit_message_caption(
            caption="❌ An error occurred!",
            parse_mode='HTML'
        )

# Register handlers
application.add_handler(CommandHandler("gift", handle_gift_command))
application.add_handler(CallbackQueryHandler(handle_gift_callback, pattern='^confirm_gift$|^cancel_gift$'))