import traceback
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler

from shivu import application, user_collection, LOGGER


async def fav(update: Update, context: CallbackContext) -> None:
    """Set a character as favorite"""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text('Please provide character id...')
        return

    character_id = str(context.args[0])

    try:
        user = await user_collection.find_one({'id': user_id})
        if not user:
            await update.message.reply_text('You have not got any character yet...')
            return

        character = next(
            (c for c in user.get('characters', []) if str(c.get('id')) == character_id),
            None
        )

        if not character:
            await update.message.reply_text('This character is not in your list')
            return

        buttons = [
            [
                InlineKeyboardButton("Yes", callback_data=f"fvc_{user_id}_{character_id}"),
                InlineKeyboardButton("No", callback_data=f"fvx_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)

        await update.message.reply_photo(
            photo=character.get("img_url", ""),
            caption=(
                f"Do you want to make this character your favorite?\n\n"
                f"Name: {character.get('name', 'Unknown')}\n"
                f"Anime: {character.get('anime', 'Unknown')}\n"
                f"ID: {character.get('id', 'Unknown')}"
            ),
            reply_markup=reply_markup
        )

    except Exception as e:
        LOGGER.error(f"[FAV ERROR] {e}\n{traceback.format_exc()}")
        await update.message.reply_text('An error occurred while processing your request.')


async def handle_fav_callback(update: Update, context: CallbackContext) -> None:
    """Handle favorite button callbacks"""
    query = update.callback_query

    try:
        await query.answer()

        data = query.data
        if not (data.startswith('fvc_') or data.startswith('fvx_')):
            return

        parts = data.split('_', 2)
        if len(parts) < 2:
            await query.answer("Invalid callback data!", show_alert=True)
            return

        action_code = parts[0]

        if action_code == 'fvc':
            if len(parts) != 3:
                await query.answer("Invalid data!", show_alert=True)
                return

            try:
                user_id = int(parts[1])
                character_id = str(parts[2])
            except ValueError:
                await query.answer("Invalid data format!", show_alert=True)
                return

            if query.from_user.id != user_id:
                await query.answer("This is not your request!", show_alert=True)
                return

            user = await user_collection.find_one({'id': user_id})
            if not user:
                await query.answer("User not found!", show_alert=True)
                return

            character = next(
                (c for c in user.get('characters', []) if str(c.get('id')) == character_id),
                None
            )

            if not character:
                await query.answer("Character not found!", show_alert=True)
                return

            result = await user_collection.update_one(
                {'id': user_id},
                {'$set': {'favorites': character}}
            )

            if result.matched_count == 0:
                await query.answer("Failed to update!", show_alert=True)
                return

            rarity = character.get('rarity', 'Common')
            if isinstance(rarity, str):
                rarity_parts = rarity.split(' ', 1)
                rarity_text = rarity_parts[1] if len(rarity_parts) > 1 else 'Common'
            else:
                rarity_text = 'Common'

            await query.edit_message_caption(
                caption=(
                    f"Successfully set as favorite!\n\n"
                    f"Name: {character.get('name', 'Unknown')}\n"
                    f"Anime: {character.get('anime', 'Unknown')}\n"
                    f"Rarity: {rarity_text}\n"
                    f"ID: {character.get('id', 'Unknown')}\n\n"
                    f"This character will appear first in your collection!"
                )
            )

            LOGGER.info(f"[FAV] Success for user {user_id}, character {character_id}")

        elif action_code == 'fvx':
            if len(parts) < 2:
                await query.answer("Invalid data!", show_alert=True)
                return

            try:
                user_id = int(parts[1])
            except ValueError:
                await query.answer("Invalid data!", show_alert=True)
                return

            if query.from_user.id != user_id:
                await query.answer("This is not your request!", show_alert=True)
                return

            await query.edit_message_caption(caption="Action cancelled. No changes made.")

    except Exception as e:
        LOGGER.error(f"[FAV CALLBACK ERROR] {e}\n{traceback.format_exc()}")
        try:
            await query.answer(f"Error: {str(e)[:100]}", show_alert=True)
        except:
            pass


application.add_handler(CommandHandler('fav', fav, block=False))
application.add_handler(CallbackQueryHandler(handle_fav_callback, pattern="^fv[cx]_", block=False))