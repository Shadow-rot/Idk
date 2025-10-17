"""
Spawn Rarity Control System
Allows admins to control which rarities spawn and their spawn rates
"""

import traceback
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from telegram.error import BadRequest

from shivu import application, shivuu, db, LOGGER

# Database collection for spawn settings
spawn_settings_collection = db['spawn_settings']

# Your custom rarity map
RARITY_MAP = {
    1: "🟢 Common",
    2: "🟣 Rare",
    3: "🟡 Legendary", 
    4: "💮 Special Edition", 
    5: "💫 Neon",
    6: "✨ Manga", 
    7: "🎭 Cosplay",
    8: "🎐 Celestial",
    9: "🔮 Premium Edition",
    10: "💋 Erotic",
    11: "🌤 Summer",
    12: "☃️ Winter",
    13: "☔️ Monsoon",
    14: "💝 Valentine",
    15: "🎃 Halloween", 
    16: "🎄 Christmas",
    17: "🏵 Mythic",
    18: "🎗 Special Events",
    19: "🎥 AMV",
    20: "👼 Tiny"
}

# Default rarity configuration with balanced spawn chances
DEFAULT_RARITIES = {
    '🟢': {'name': 'Common', 'enabled': True, 'chance': 25.0},
    '🟣': {'name': 'Rare', 'enabled': True, 'chance': 20.0},
    '🟡': {'name': 'Legendary', 'enabled': True, 'chance': 10.0},
    '💮': {'name': 'Special Edition', 'enabled': True, 'chance': 8.0},
    '💫': {'name': 'Neon', 'enabled': True, 'chance': 7.0},
    '✨': {'name': 'Manga', 'enabled': True, 'chance': 6.0},
    '🎭': {'name': 'Cosplay', 'enabled': True, 'chance': 5.0},
    '🎐': {'name': 'Celestial', 'enabled': True, 'chance': 4.0},
    '🔮': {'name': 'Premium Edition', 'enabled': True, 'chance': 3.0},
    '💋': {'name': 'Erotic', 'enabled': True, 'chance': 2.5},
    '🌤': {'name': 'Summer', 'enabled': True, 'chance': 2.0},
    '☃️': {'name': 'Winter', 'enabled': True, 'chance': 2.0},
    '☔️': {'name': 'Monsoon', 'enabled': True, 'chance': 1.5},
    '💝': {'name': 'Valentine', 'enabled': True, 'chance': 1.0},
    '🎃': {'name': 'Halloween', 'enabled': True, 'chance': 1.0},
    '🎄': {'name': 'Christmas', 'enabled': True, 'chance': 1.0},
    '🏵': {'name': 'Mythic', 'enabled': True, 'chance': 0.5},
    '🎗': {'name': 'Special Events', 'enabled': True, 'chance': 0.3},
    '🎥': {'name': 'AMV', 'enabled': True, 'chance': 0.15},
    '👼': {'name': 'Tiny', 'enabled': True, 'chance': 0.1},
}

# Sudo users who can access the panel
SUDO_USERS = [5147822244, 8420981179]  # Add your admin user IDs here


async def get_spawn_settings():
    """Get current spawn settings from database"""
    try:
        settings = await spawn_settings_collection.find_one({'type': 'rarity_control'})
        if not settings:
            # Initialize with defaults
            settings = {
                'type': 'rarity_control',
                'rarities': DEFAULT_RARITIES.copy()
            }
            await spawn_settings_collection.insert_one(settings)
        return settings
    except Exception as e:
        LOGGER.error(f"Error getting spawn settings: {e}")
        return {'type': 'rarity_control', 'rarities': DEFAULT_RARITIES.copy()}


async def update_spawn_settings(rarities):
    """Update spawn settings in database"""
    try:
        await spawn_settings_collection.update_one(
            {'type': 'rarity_control'},
            {'$set': {'rarities': rarities}},
            upsert=True
        )
        return True
    except Exception as e:
        LOGGER.error(f"Error updating spawn settings: {e}")
        return False


def normalize_chances(rarities):
    """Normalize all spawn chances to total 100%"""
    enabled_rarities = {k: v for k, v in rarities.items() if v['enabled']}

    if not enabled_rarities:
        return rarities

    total = sum(r['chance'] for r in enabled_rarities.values())

    if total > 0:
        for emoji in enabled_rarities:
            rarities[emoji]['chance'] = round((rarities[emoji]['chance'] / total) * 100, 2)

    return rarities


def create_panel_keyboard(rarities, page=0):
    """Create inline keyboard for spawn panel (paginated)"""
    keyboard = []

    # Header
    keyboard.append([InlineKeyboardButton("🎯 Spawn Rarity Control Panel", callback_data="noop")])
    keyboard.append([InlineKeyboardButton("━━━━━━━━━━━━━━━━━━", callback_data="noop")])

    # Calculate pagination
    items_per_page = 5
    rarity_items = list(rarities.items())
    total_pages = (len(rarity_items) + items_per_page - 1) // items_per_page
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(rarity_items))

    # Display current page items
    for emoji, data in rarity_items[start_idx:end_idx]:
        status = "✅" if data['enabled'] else "❌"
        name = data['name']
        chance = data['chance']

        # Status toggle button
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {name} {status}",
                callback_data=f"toggle_{emoji}_{page}"
            )
        ])

        # Chance adjustment buttons (only if enabled)
        if data['enabled']:
            keyboard.append([
                InlineKeyboardButton("--", callback_data=f"dec10_{emoji}_{page}"),
                InlineKeyboardButton("-", callback_data=f"dec1_{emoji}_{page}"),
                InlineKeyboardButton(f"{chance}%", callback_data="noop"),
                InlineKeyboardButton("+", callback_data=f"inc1_{emoji}_{page}"),
                InlineKeyboardButton("++", callback_data=f"inc10_{emoji}_{page}"),
            ])

    # Pagination buttons
    keyboard.append([InlineKeyboardButton("━━━━━━━━━━━━━━━━━━", callback_data="noop")])
    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"page_{page-1}"))
        nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="noop"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{page+1}"))
        keyboard.append(nav_buttons)

    # Control buttons
    keyboard.append([
        InlineKeyboardButton("🔄 Normalize", callback_data=f"normalize_{page}"),
        InlineKeyboardButton("♻️ Reset", callback_data=f"reset_{page}")
    ])
    keyboard.append([
        InlineKeyboardButton("✅ Enable All", callback_data=f"enable_all_{page}"),
        InlineKeyboardButton("❌ Disable All", callback_data=f"disable_all_{page}")
    ])
    keyboard.append([InlineKeyboardButton("❎ Close Panel", callback_data="close")])

    return InlineKeyboardMarkup(keyboard)


def format_panel_text(rarities, page=0):
    """Format the panel message text"""
    enabled_count = sum(1 for r in rarities.values() if r['enabled'])
    total_count = len(rarities)
    total_chance = sum(r['chance'] for r in rarities.values() if r['enabled'])

    # Calculate items for current page
    items_per_page = 5
    rarity_items = list(rarities.items())
    total_pages = (len(rarity_items) + items_per_page - 1) // items_per_page
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(rarity_items))

    text = (
        "🎯 **SPAWN RARITY CONTROL PANEL**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 **Status**: {enabled_count}/{total_count} rarities enabled\n"
        f"💯 **Total Chance**: {total_chance:.2f}%\n"
        f"📄 **Page**: {page+1}/{total_pages}\n\n"
        "**Current Page Configuration:**\n"
    )

    for emoji, data in rarity_items[start_idx:end_idx]:
        status = "✅ Enabled" if data['enabled'] else "❌ Disabled"
        text += f"{emoji} **{data['name']}**: {data['chance']:.2f}% - {status}\n"

    text += (
        "\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**Instructions:**\n"
        "• Click rarity name to toggle enable/disable\n"
        "• Use -/+ buttons to adjust spawn chance\n"
        "• --/++ adjusts by 10%, -/+ adjusts by 1%\n"
        "• Navigate pages to see all rarities\n"
        "• Normalize ensures total equals 100%\n"
        "• Changes apply immediately to spawns"
    )

    return text


async def spawnpanel_command(update: Update, context: CallbackContext):
    """Show spawn rarity control panel"""
    try:
        user_id = update.effective_user.id

        # Check if user is sudo
        if user_id not in SUDO_USERS:
            await update.message.reply_text(
                "⚠️ **Access Denied**\n\n"
                "This command is only available to bot administrators.",
                parse_mode='Markdown'
            )
            return

        # Get current settings
        settings = await get_spawn_settings()
        rarities = settings['rarities']

        # Create and send panel
        text = format_panel_text(rarities, page=0)
        keyboard = create_panel_keyboard(rarities, page=0)

        await update.message.reply_text(
            text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

        LOGGER.info(f"Spawn panel opened by user {user_id}")

    except Exception as e:
        LOGGER.error(f"Error in spawnpanel command: {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text(
            "❌ An error occurred while opening the spawn panel."
        )


async def panel_callback(update: Update, context: CallbackContext):
    """Handle spawn panel button callbacks"""
    try:
        query = update.callback_query
        user_id = query.from_user.id
        data = query.data

        # Check sudo access
        if user_id not in SUDO_USERS:
            await query.answer("⚠️ Access denied!", show_alert=True)
            return

        # Handle noop (display only)
        if data == "noop":
            await query.answer()
            return

        # Handle close
        if data == "close":
            await query.message.delete()
            await query.answer("Panel closed")
            return

        # Get current settings
        settings = await get_spawn_settings()
        rarities = settings['rarities']

        # Parse callback data using underscore separator
        parts = data.split('_')
        action = parts[0]

        page = 0
        changed = False
        answer_text = ""

        # Handle different actions
        if action == "page":
            page = int(parts[1])
            answer_text = f"Page {page+1}"

        elif action == "toggle":
            emoji = parts[1]
            page = int(parts[2])
            if emoji in rarities:
                rarities[emoji]['enabled'] = not rarities[emoji]['enabled']
                changed = True
                answer_text = f"{'Enabled' if rarities[emoji]['enabled'] else 'Disabled'} {rarities[emoji]['name']}"

        elif action == "inc1":
            emoji = parts[1]
            page = int(parts[2])
            if emoji in rarities and rarities[emoji]['enabled']:
                rarities[emoji]['chance'] = min(100, round(rarities[emoji]['chance'] + 1, 2))
                changed = True
                answer_text = f"Increased to {rarities[emoji]['chance']}%"

        elif action == "inc10":
            emoji = parts[1]
            page = int(parts[2])
            if emoji in rarities and rarities[emoji]['enabled']:
                rarities[emoji]['chance'] = min(100, round(rarities[emoji]['chance'] + 10, 2))
                changed = True
                answer_text = f"Increased to {rarities[emoji]['chance']}%"

        elif action == "dec1":
            emoji = parts[1]
            page = int(parts[2])
            if emoji in rarities and rarities[emoji]['enabled']:
                rarities[emoji]['chance'] = max(0.1, round(rarities[emoji]['chance'] - 1, 2))
                changed = True
                answer_text = f"Decreased to {rarities[emoji]['chance']}%"

        elif action == "dec10":
            emoji = parts[1]
            page = int(parts[2])
            if emoji in rarities and rarities[emoji]['enabled']:
                rarities[emoji]['chance'] = max(0.1, round(rarities[emoji]['chance'] - 10, 2))
                changed = True
                answer_text = f"Decreased to {rarities[emoji]['chance']}%"

        elif action == "normalize":
            page = int(parts[1])
            rarities = normalize_chances(rarities)
            changed = True
            answer_text = "Chances normalized to 100%"

        elif action == "reset":
            page = int(parts[1]) if len(parts) > 1 else 0
            rarities = DEFAULT_RARITIES.copy()
            changed = True
            answer_text = "Reset to default settings"
            page = 0

        elif action == "enable":
            # enable_all
            page = int(parts[2])
            for emoji in rarities:
                rarities[emoji]['enabled'] = True
            changed = True
            answer_text = "All rarities enabled"

        elif action == "disable":
            # disable_all
            page = int(parts[2])
            for emoji in rarities:
                rarities[emoji]['enabled'] = False
            changed = True
            answer_text = "All rarities disabled"

        # Update database if changes were made
        if changed:
            success = await update_spawn_settings(rarities)
            if not success:
                await query.answer("❌ Failed to save changes", show_alert=True)
                return

        # Answer callback query
        await query.answer(answer_text if answer_text else "")

        # Update panel display
        text = format_panel_text(rarities, page)
        keyboard = create_panel_keyboard(rarities, page)

        try:
            await query.edit_message_text(
                text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        except BadRequest as e:
            # Message unchanged or other non-critical error
            if "Message is not modified" not in str(e):
                LOGGER.warning(f"BadRequest in panel update: {e}")

    except Exception as e:
        LOGGER.error(f"Error in panel callback: {e}")
        LOGGER.error(traceback.format_exc())
        try:
            await query.answer("❌ An error occurred", show_alert=True)
        except:
            pass


def register_rarity_handlers():
    """Register handlers for rarity control system"""
    try:
        application.add_handler(CommandHandler("spawnpanel", spawnpanel_command, block=False))
        application.add_handler(CallbackQueryHandler(
            panel_callback, 
            pattern=r"^(toggle|inc1|inc10|dec1|dec10|normalize|reset|enable|disable|page|close|noop)", 
            block=False
        ))
        LOGGER.info("✅ Registered spawn rarity control handlers")
    except Exception as e:
        LOGGER.error(f"❌ Failed to register rarity handlers: {e}")


# Export for use in main bot file
__all__ = ['register_rarity_handlers', 'spawn_settings_collection', 'get_spawn_settings']