from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from pyrogram import filters
from pyrogram import types as t
from html import escape

from shivu import (
    application,
    user_collection,
    collection,
    shivuu as bot,
    LOGGER
)

# ==================== FAVORITE COMMAND ====================

async def fav_cmd(update: Update, context: CallbackContext) -> None:
    """Set a character as favorite"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "<b>Usage:</b>\n"
            "➥ <code>/fav character_id</code>\n\n"
            "<i>Example: /fav 123</i>",
            parse_mode='HTML'
        )
        return

    character_id = str(context.args[0])

    try:
        # Find user and their characters
        user = await user_collection.find_one({'id': user_id})
        if not user:
            await update.message.reply_text(
                "❌ You don't have any characters yet!",
                parse_mode='HTML'
            )
            return

        # Find character in user's collection
        character = next(
            (c for c in user.get('characters', []) if str(c.get('id')) == character_id),
            None
        )

        if not character:
            await update.message.reply_text(
                "❌ You don't own this character!",
                parse_mode='HTML'
            )
            return

        # Create confirmation buttons
        keyboard = [
            [
                InlineKeyboardButton("✅ Set as Favorite", callback_data=f"fav_yes_{character_id}_{user_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"fav_no_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Get character rarity
        rarity = character.get('rarity', '🟢 Common')
        if isinstance(rarity, str):
            rarity_parts = rarity.split(' ', 1)
            rarity_emoji = rarity_parts[0] if len(rarity_parts) > 0 else '🟢'
            rarity_text = rarity_parts[1] if len(rarity_parts) > 1 else 'Common'
        else:
            rarity_emoji = '🟢'
            rarity_text = 'Common'

        await update.message.reply_photo(
            photo=character['img_url'],
            caption=(
                f"<b>💖 Set this character as your favorite?</b>\n\n"
                f"<b>🎀 Name:</b> <code>{escape(character['name'])}</code>\n"
                f"<b>📺 Anime:</b> <code>{escape(character['anime'])}</code>\n"
                f"<b>{rarity_emoji} Rarity:</b> <code>{escape(rarity_text)}</code>\n"
                f"<b>🆔 ID:</b> <code>{character_id}</code>"
            ),
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    except Exception as e:
        LOGGER.error(f"Error in fav command: {e}")
        await update.message.reply_text('❌ An error occurred!')

# ==================== CALLBACK HANDLER ====================

async def fav_callback(update: Update, context: CallbackContext) -> None:
    """Handle favorite button callbacks"""
    query = update.callback_query
    await query.answer()

    try:
        # Parse callback data
        data_parts = query.data.split('_')
        action = data_parts[1]

        if action == 'yes':
            character_id = str(data_parts[2])
            user_id = int(data_parts[3])

            # Verify user
            if query.from_user.id != user_id:
                await query.answer("⚠️ This is not your request!", show_alert=True)
                return

            # Update user's favorite character
            result = await user_collection.update_one(
                {'id': user_id},
                {'$set': {'favorite': character_id}},
                upsert=True
            )

            if result.modified_count > 0 or result.upserted_id:
                await query.edit_message_caption(
                    caption=(
                        f"<b>✅ Success!</b>\n\n"
                        f"💖 Character set as your favorite!\n"
                        f"🆔 ID: <code>{character_id}</code>\n\n"
                        f"<i>Use inline mode to show your favorite!</i>"
                    ),
                    parse_mode='HTML'
                )
            else:
                await query.edit_message_caption(
                    caption="❌ Failed to set favorite. Please try again.",
                    parse_mode='HTML'
                )

        elif action == 'no':
            user_id = int(data_parts[2])
            if query.from_user.id != user_id:
                await query.answer("⚠️ This is not your request!", show_alert=True)
                return

            await query.edit_message_caption(
                caption="❌ Action cancelled.",
                parse_mode='HTML'
            )

    except Exception as e:
        LOGGER.error(f"Error in fav callback: {e}")
        try:
            await query.edit_message_caption(
                caption="❌ An error occurred!",
                parse_mode='HTML'
            )
        except:
            pass

# ==================== INLINE QUERY HANDLER ====================

@bot.on_inline_query()
async def inline_query(client, query):
    """Handle inline queries for favorites"""
    try:
        # Get user's data
        user_id = query.from_user.id
        user_data = await user_collection.find_one({'id': user_id})

        if not user_data or 'favorite' not in user_data:
            await query.answer(
                results=[],
                switch_pm_text="❌ No favorite character set!",
                switch_pm_parameter="setfav",
                cache_time=1
            )
            return

        # Get favorite character
        favorite_id = user_data['favorite']
        character = next(
            (c for c in user_data.get('characters', []) if str(c.get('id')) == favorite_id),
            None
        )

        if not character:
            await query.answer(
                results=[],
                switch_pm_text="❌ Favorite character not found!",
                switch_pm_parameter="setfav",
                cache_time=1
            )
            return

        # Get rarity info
        rarity = character.get('rarity', '🟢 Common')
        if isinstance(rarity, str):
            rarity_parts = rarity.split(' ', 1)
            rarity_emoji = rarity_parts[0] if len(rarity_parts) > 0 else '🟢'
            rarity_text = rarity_parts[1] if len(rarity_parts) > 1 else 'Common'
        else:
            rarity_emoji = '🟢'
            rarity_text = 'Common'

        # Create inline result
        caption = (
            f"<b>💖 {query.from_user.first_name}'s Favorite Character</b>\n\n"
            f"<b>🎀 Name:</b> <code>{escape(character['name'])}</code>\n"
            f"<b>📺 Anime:</b> <code>{escape(character['anime'])}</code>\n"
            f"<b>{rarity_emoji} Rarity:</b> <code>{escape(rarity_text)}</code>\n"
            f"<b>🆔 ID:</b> <code>{favorite_id}</code>"
        )

        result = [
            t.InlineQueryResultPhoto(
                photo_url=character['img_url'],
                thumb_url=character['img_url'],
                caption=caption,
                parse_mode='HTML',
                title=f"Your Favorite: {character['name']}"
            )
        ]

        await query.answer(
            results=result,
            cache_time=1
        )

    except Exception as e:
        LOGGER.error(f"Error in inline query: {e}")
        await query.answer(
            results=[],
            switch_pm_text="❌ An error occurred!",
            switch_pm_parameter="error",
            cache_time=1
        )

# ==================== REGISTER HANDLERS ====================

def register_handlers():
    """Register handlers"""
    application.add_handler(CommandHandler("fav", fav_cmd))
    application.add_handler(CallbackQueryHandler(fav_callback, pattern="^fav_"))

register_handlers()