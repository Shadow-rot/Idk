# ==================== CALLBACK HANDLERS ====================

async def handle_top_owners(update: Update, context: CallbackContext) -> None:
    """Show top owners of a character (edits message with list)"""
    query = update.callback_query
    await query.answer()

    try:
        character_id = query.data.split('_')[2]
        users = await get_users_by_character(character_id)
        character = await get_character_by_id(character_id)

        if not character:
            await query.edit_message_text(
                f"<b>❌ {to_small_caps('character not found')}</b>",
                parse_mode='HTML'
            )
            return

        if not users:
            await query.edit_message_text(
                f"<b>{to_small_caps('no users found with character')}</b> <code>{character_id}</code>",
                parse_mode='HTML'
            )
            return

        # Sort users
        users.sort(key=lambda x: x['count'], reverse=True)

        # Header
        response = f"<b>🏆 {to_small_caps('top owners')}</b> <code>{character_id}</code>\n"
        response += f"<b>{escape(character.get('name', 'Unknown'))}</b>\n\n"

        # Build list (Top 50)
        for i, user in enumerate(users[:50], 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            user_id = user['id']
            name = escape(user['first_name'])
            username = user.get('username')
            count = user['count']

            user_link = f"<a href='tg://user?id={user_id}'>{name}</a>"
            if username:
                user_link += f" (@{escape(username)})"

            response += f"{medal} {user_link} <code>x{count}</code>\n"

        if len(users) > 50:
            response += f"\n<i>{to_small_caps('showing top 50 of')} {len(users)}</i>"

        # Inline buttons
        keyboard = [
            [
                InlineKeyboardButton(
                    f"📊 {to_small_caps('stats')}",
                    callback_data=f"char_stats_{character_id}"
                ),
                InlineKeyboardButton(
                    f"🔄 {to_small_caps('back to card')}",
                    callback_data=f"back_to_card_{character_id}"
                )
            ]
        ]

        # Edit original message with results
        await query.edit_message_caption(
            caption=response,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        print(f"Error showing top owners: {e}")
        await query.answer(to_small_caps("error loading owners"), show_alert=True)


async def handle_back_to_card(update: Update, context: CallbackContext) -> None:
    """Go back to original character card"""
    query = update.callback_query
    await query.answer()

    try:
        character_id = query.data.split('_')[3]
        character = await get_character_by_id(character_id)
        if not character:
            await query.edit_message_text(
                f"<b>❌ {to_small_caps('character not found')}</b>",
                parse_mode='HTML'
            )
            return

        global_count = await get_global_count(character_id)
        caption = format_character_card(character, global_count)

        # Restore main inline buttons
        keyboard = [
            [
                InlineKeyboardButton(
                    f"🏆 {to_small_caps('top owners')}",
                    callback_data=f"top_owners_{character_id}"
                ),
                InlineKeyboardButton(
                    f"📊 {to_small_caps('stats')}",
                    callback_data=f"char_stats_{character_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    f"🔗 {to_small_caps('share character')}",
                    url=f"https://t.me/share/url?url=Check out this character: /check {character_id}"
                )
            ]
        ]

        # Restore original message with photo & caption
        await query.edit_message_caption(
            caption=caption,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        print(f"Error in handle_back_to_card: {e}")
        await query.answer(to_small_caps("error restoring card"), show_alert=True)