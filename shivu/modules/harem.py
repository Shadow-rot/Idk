from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from html import escape 
import random
import math
from itertools import groupby
from shivu import db, application

# Database collections
collection = db['anime_characters_lol']
user_collection = db['user_collection_lmaoooo']

# Rarity mapping for harem modes
HAREM_MODE_MAPPING = {
    "common": "🟢 Common",
    "rare": "🟣 Rare",
    "legendary": "🟡 Legendary",
    "special": "💮 Special Edition",
    "neon": "💫 Neon",
    "manga": "✨ Manga",
    "cosplay": "🎭 Cosplay",
    "celestial": "🎐 Celestial",
    "premium": "🔮 Premium Edition",
    "erotic": "💋 Erotic",
    "summer": "🌤 Summer",
    "winter": "☃️ Winter",
    "monsoon": "☔️ Monsoon",
    "valentine": "💝 Valentine",
    "halloween": "🎃 Halloween",
    "christmas": "🎄 Christmas",
    "mythic": "🏵 Mythic",
    "events": "🎗 Special Events",
    "amv": "🎥 Amv",
    "default": None
}


async def harem(update: Update, context: CallbackContext, page=0, edit=False) -> None:
    """Display user's character collection (harem)"""
    user_id = update.effective_user.id
    
    try:
        user = await user_collection.find_one({'id': user_id})
        if not user:
            message = update.message or update.callback_query.message
            await message.reply_text("You need to grab a character first using /grab command!")
            return

        characters = user.get('characters', [])
        if not characters:
            message = update.message or update.callback_query.message
            await message.reply_text("You don't have any characters yet! Use /grab to catch some.")
            return

        # Get favorite character
        fav_character_id = user.get('favorites', None)
        fav_character = None
        if fav_character_id:
            fav_character = next(
                (c for c in characters if isinstance(c, dict) and c.get('id') == fav_character_id),
                None
            )

        # Get harem mode
        hmode = user.get('smode', 'default')
        
        # Filter characters based on mode
        if hmode == "default" or hmode is None:
            filtered_chars = [char for char in characters if isinstance(char, dict)]
            rarity_filter = "All"
        else:
            rarity_value = HAREM_MODE_MAPPING.get(hmode, None)
            if rarity_value:
                filtered_chars = [
                    char for char in characters 
                    if isinstance(char, dict) and char.get('rarity') == rarity_value
                ]
                rarity_filter = rarity_value
            else:
                filtered_chars = [char for char in characters if isinstance(char, dict)]
                rarity_filter = "All"

        if not filtered_chars:
            message = update.message or update.callback_query.message
            await message.reply_text(
                f"You don't have any characters with rarity: {rarity_filter}\n"
                f"Change mode using /smode"
            )
            return

        # Sort characters
        filtered_chars = sorted(filtered_chars, key=lambda x: (x.get('anime', ''), x.get('id', '')))
        
        # Count characters
        character_counts = {}
        for char in filtered_chars:
            char_id = char.get('id')
            if char_id:
                character_counts[char_id] = character_counts.get(char_id, 0) + 1

        # Pagination
        total_pages = math.ceil(len(filtered_chars) / 10)
        if page < 0 or page >= total_pages:
            page = 0

        # Build message
        user_name = escape(update.effective_user.first_name)
        harem_message = f"<b>🎴 {user_name}'s Collection ({rarity_filter})</b>\n"
        harem_message += f"<b>Page {page + 1}/{total_pages}</b>\n\n"

        # Get current page characters
        start_idx = page * 10
        end_idx = start_idx + 10
        current_chars = filtered_chars[start_idx:end_idx]

        # Group by anime
        grouped = {}
        for char in current_chars:
            anime = char.get('anime', 'Unknown')
            if anime not in grouped:
                grouped[anime] = []
            grouped[anime].append(char)

        # Track included characters to avoid duplicates
        included = set()

        for anime, chars in grouped.items():
            # Count user's characters from this anime
            user_anime_count = len([
                c for c in user['characters'] 
                if isinstance(c, dict) and c.get('anime') == anime
            ])
            
            # Count total characters in this anime
            total_anime_count = await collection.count_documents({"anime": anime})
            
            harem_message += f'<b>📺 {anime} [{user_anime_count}/{total_anime_count}]</b>\n'
            
            for char in chars:
                char_id = char.get('id')
                if char_id and char_id not in included:
                    count = character_counts.get(char_id, 1)
                    name = char.get('name', 'Unknown')
                    rarity = char.get('rarity', '🟢 Common')
                    
                    # Get rarity emoji
                    if isinstance(rarity, str):
                        rarity_emoji = rarity.split(' ')[0]
                    else:
                        rarity_emoji = '🟢'
                    
                    harem_message += f'  {rarity_emoji} <code>{char_id}</code> • <b>{escape(name)}</b> ×{count}\n'
                    included.add(char_id)
            
            harem_message += '\n'

        # Create keyboard
        keyboard = [[
            InlineKeyboardButton(
                "🎭 View All", 
                switch_inline_query_current_chat=f"collection.{user_id}"
            )
        ]]

        # Add navigation buttons
        if total_pages > 1:
            nav_buttons = []
            if page > 0:
                nav_buttons.append(
                    InlineKeyboardButton("⬅️ Prev", callback_data=f"harem:{page - 1}:{user_id}")
                )
            if page < total_pages - 1:
                nav_buttons.append(
                    InlineKeyboardButton("Next ➡️", callback_data=f"harem:{page + 1}:{user_id}")
                )
            if nav_buttons:
                keyboard.append(nav_buttons)

        reply_markup = InlineKeyboardMarkup(keyboard)
        message = update.message or update.callback_query.message

        # Determine which image to show
        display_img = None
        if fav_character and 'img_url' in fav_character:
            display_img = fav_character['img_url']
        elif filtered_chars:
            random_char = random.choice(filtered_chars)
            display_img = random_char.get('img_url')

        # Send or edit message
        if display_img:
            if edit:
                await message.edit_caption(
                    caption=harem_message, 
                    reply_markup=reply_markup, 
                    parse_mode='HTML'
                )
            else:
                await message.reply_photo(
                    photo=display_img,
                    caption=harem_message,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
        else:
            if edit:
                await message.edit_text(
                    text=harem_message,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            else:
                await message.reply_text(
                    text=harem_message,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )

    except Exception as e:
        print(f"Error in harem command: {e}")
        message = update.message or update.callback_query.message
        await message.reply_text("An error occurred while loading your collection.")


async def harem_callback(update: Update, context: CallbackContext) -> None:
    """Handle harem pagination callbacks"""
    query = update.callback_query
    
    try:
        data = query.data
        _, page, user_id = data.split(':')
        page = int(page)
        user_id = int(user_id)
        
        # Verify user
        if query.from_user.id != user_id:
            await query.answer("⚠️ This is not your collection!", show_alert=True)
            return
        
        await query.answer()
        await harem(update, context, page, edit=True)
        
    except Exception as e:
        print(f"Error in harem callback: {e}")
        await query.answer("Error loading page", show_alert=True)


async def set_hmode(update: Update, context: CallbackContext) -> None:
    """Set harem display mode"""
    keyboard = [
        [
            InlineKeyboardButton("🧩 Default", callback_data="mode_default"),
            InlineKeyboardButton("🔮 By Rarity", callback_data="mode_rarity"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_photo(
        photo="https://te.legra.ph/file/e714526fdc85b8800e1de.jpg",
        caption="<b>⚙️ Collection Display Mode</b>\n\nChoose how to display your collection:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def hmode_rarity(update: Update, context: CallbackContext) -> None:
    """Show rarity selection menu"""
    keyboard = [
        [
            InlineKeyboardButton("🟢 Common", callback_data="mode_common"),
            InlineKeyboardButton("🟣 Rare", callback_data="mode_rare"),
            InlineKeyboardButton("🟡 Legendary", callback_data="mode_legendary"),
        ],
        [
            InlineKeyboardButton("💮 Special", callback_data="mode_special"),
            InlineKeyboardButton("💫 Neon", callback_data="mode_neon"),
            InlineKeyboardButton("✨ Manga", callback_data="mode_manga"),
        ],
        [
            InlineKeyboardButton("🎭 Cosplay", callback_data="mode_cosplay"),
            InlineKeyboardButton("🎐 Celestial", callback_data="mode_celestial"),
            InlineKeyboardButton("🔮 Premium", callback_data="mode_premium"),
        ],
        [
            InlineKeyboardButton("💋 Erotic", callback_data="mode_erotic"),
            InlineKeyboardButton("🌤 Summer", callback_data="mode_summer"),
            InlineKeyboardButton("☃️ Winter", callback_data="mode_winter"),
        ],
        [
            InlineKeyboardButton("☔️ Monsoon", callback_data="mode_monsoon"),
            InlineKeyboardButton("💝 Valentine", callback_data="mode_valentine"),
            InlineKeyboardButton("🎃 Halloween", callback_data="mode_halloween"),
        ],
        [
            InlineKeyboardButton("🎄 Christmas", callback_data="mode_christmas"),
            InlineKeyboardButton("🏵 Mythic", callback_data="mode_mythic"),
            InlineKeyboardButton("🎗 Events", callback_data="mode_events"),
        ],
        [
            InlineKeyboardButton("🎥 Amv", callback_data="mode_amv"),
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="mode_back"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query = update.callback_query
    await query.edit_message_caption(
        caption="<b>🎨 Filter by Rarity</b>\n\nSelect a rarity to display:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    await query.answer()


async def mode_button(update: Update, context: CallbackContext) -> None:
    """Handle mode selection buttons"""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    
    try:
        if data == "mode_default":
            await user_collection.update_one(
                {'id': user_id}, 
                {'$set': {'smode': 'default'}}
            )
            await query.answer("✅ Mode set to Default")
            await query.edit_message_caption(
                caption="<b>✅ Display Mode Updated</b>\n\nShowing: <b>All Characters</b>",
                parse_mode='HTML'
            )
            
        elif data == "mode_rarity":
            await hmode_rarity(update, context)
            
        elif data == "mode_back":
            keyboard = [
                [
                    InlineKeyboardButton("🧩 Default", callback_data="mode_default"),
                    InlineKeyboardButton("🔮 By Rarity", callback_data="mode_rarity"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_caption(
                caption="<b>⚙️ Collection Display Mode</b>\n\nChoose how to display your collection:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            await query.answer()
            
        elif data.startswith("mode_"):
            # Extract mode name
            mode_name = data.replace("mode_", "")
            rarity_display = HAREM_MODE_MAPPING.get(mode_name, "Unknown")
            
            await user_collection.update_one(
                {'id': user_id}, 
                {'$set': {'smode': mode_name}}
            )
            await query.answer(f"✅ Mode set to {rarity_display}")
            await query.edit_message_caption(
                caption=f"<b>✅ Display Mode Updated</b>\n\nShowing: <b>{rarity_display}</b>",
                parse_mode='HTML'
            )
            
    except Exception as e:
        print(f"Error in mode button: {e}")
        await query.answer("Error updating mode", show_alert=True)


# Register handlers
application.add_handler(CommandHandler(["pharem"], harem, block=False))
application.add_handler(CallbackQueryHandler(harem_callback, pattern='^harem:', block=False))
application.add_handler(CommandHandler("smode", set_hmode, block=False))
application.add_handler(CallbackQueryHandler(mode_button, pattern='^mode_', block=False))