import traceback
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, user_collection, LOGGER

pending_gifts = {}


async def handle_gift_command(update: Update, context: CallbackContext):
    """Handle the /gift command"""
    try:
        message = update.message
        sender_id = message.from_user.id

        if not message.reply_to_message:
            await message.reply_text("You need to reply to someone's message to gift!")
            return

        receiver_id = message.reply_to_message.from_user.id
        receiver_username = message.reply_to_message.from_user.username or "N/A"
        receiver_first_name = message.reply_to_message.from_user.first_name

        if sender_id == receiver_id:
            await message.reply_text("You can't gift characters to yourself!")
            return

        if len(context.args) != 1:
            await message.reply_text("Usage: Reply with /gift character_id")
            return

        character_id = context.args[0]

        sender = await user_collection.find_one({'id': sender_id})
        if not sender:
            await message.reply_text("You don't have any characters to gift!")
            return

        character = None
        for char in sender.get('characters', []):
            if isinstance(char, dict) and str(char.get('id')) == str(character_id):
                character = char
                break

        if not character:
            await message.reply_text("You don't own this character!")
            return

        if sender_id in pending_gifts:
            await message.reply_text("You already have a pending gift! Please confirm or cancel it first.")
            return

        pending_gifts[sender_id] = {
            'character': character,
            'receiver_id': receiver_id,
            'receiver_username': receiver_username,
            'receiver_first_name': receiver_first_name,
            'sender_username': message.from_user.username or "N/A",
            'sender_first_name': message.from_user.first_name
        }

        rarity = character.get('rarity', 'Common')
        if isinstance(rarity, str):
            rarity_parts = rarity.split(' ', 1)
            rarity_text = rarity_parts[1] if len(rarity_parts) > 1 else 'Common'
        else:
            rarity_text = 'Common'

        caption = (
            f"Gift Confirmation\n\n"
            f"To: {receiver_first_name}\n\n"
            f"Character Details:\n"
            f"Name: {character.get('name', 'Unknown')}\n"
            f"Anime: {character.get('anime', 'Unknown')}\n"
            f"ID: {character.get('id', 'N/A')}\n"
            f"Rarity: {rarity_text}\n\n"
            f"Are you sure you want to gift this character?"
        )

        keyboard = [
            [
                InlineKeyboardButton("Confirm", callback_data=f"gift_confirm:{sender_id}"),
                InlineKeyboardButton("Cancel", callback_data=f"gift_cancel:{sender_id}")
            ]
        ]

        await message.reply_photo(
            photo=character.get('img_url', 'https://i.imgur.com/placeholder.png'),
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        LOGGER.error(f"[GIFT ERROR] {e}\n{traceback.format_exc()}")
        try:
            await message.reply_text(f"An error occurred!\n{str(e)}")
        except:
            pass


async def handle_gift_callback(update: Update, context: CallbackContext):
    """Handle gift confirmation callbacks"""
    query = update.callback_query

    try:
        data = query.data

        if ':' not in data:
            await query.answer("Invalid gift data!", show_alert=True)
            return

        action, user_id_str = data.split(':', 1)
        user_id = int(user_id_str)

        if query.from_user.id != user_id:
            await query.answer("This is not your gift confirmation!", show_alert=True)
            return

        await query.answer()

        if user_id not in pending_gifts:
            await query.answer("No pending gift found or already processed!", show_alert=True)
            return

        gift_data = pending_gifts[user_id]
        character = gift_data['character']

        if action == "gift_confirm":
            try:
                sender = await user_collection.find_one({'id': user_id})
                receiver = await user_collection.find_one({'id': gift_data['receiver_id']})

                if not sender:
                    raise Exception("Sender not found in database")

                char_exists = False
                for char in sender.get('characters', []):
                    if isinstance(char, dict) and str(char.get('id')) == str(character['id']):
                        char_exists = True
                        break

                if not char_exists:
                    raise Exception("Character no longer in sender's collection")

                await user_collection.update_one(
                    {'id': user_id},
                    {'$pull': {'characters': {'id': character['id']}}}
                )

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

                success_msg = (
                    f"Gift Successful!\n\n"
                    f"{character.get('name', 'Unknown')} has been gifted to {gift_data['receiver_first_name']}!"
                )

                await query.edit_message_caption(caption=success_msg)
                LOGGER.info(f"[GIFT] Success: {user_id} -> {gift_data['receiver_id']}")

            except Exception as e:
                LOGGER.error(f"[GIFT ERROR] {e}\n{traceback.format_exc()}")
                await query.edit_message_caption(caption=f"Failed to process gift!\n{str(e)}")

        elif action == "gift_cancel":
            await query.edit_message_caption(caption="Gift cancelled!")

        if user_id in pending_gifts:
            del pending_gifts[user_id]

    except Exception as e:
        LOGGER.error(f"[GIFT CALLBACK ERROR] {e}\n{traceback.format_exc()}")
        try:
            await query.answer(f"Error: {str(e)}", show_alert=True)
        except:
            pass


application.add_handler(CommandHandler("gift", handle_gift_command, block=False))
application.add_handler(CallbackQueryHandler(handle_gift_callback, pattern='^gift_(confirm|cancel):', block=False))