"""
Spawn Rarity Control System - Command Based
Allows admins to control which rarities spawn and their spawn rates using commands
"""

import traceback
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

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

# Sudo users who can access the commands
SUDO_USERS = [5147822244, 8420981179]  # Add your admin user IDs here

# Emoji to name mapping for easier command usage
EMOJI_TO_NAME = {
    '🟢': 'common',
    '🟣': 'rare',
    '🟡': 'legendary',
    '💮': 'special',
    '💫': 'neon',
    '✨': 'manga',
    '🎭': 'cosplay',
    '🎐': 'celestial',
    '🔮': 'premium',
    '💋': 'erotic',
    '🌤': 'summer',
    '☃️': 'winter',
    '☔️': 'monsoon',
    '💝': 'valentine',
    '🎃': 'halloween',
    '🎄': 'christmas',
    '🏵': 'mythic',
    '🎗': 'events',
    '🎥': 'amv',
    '👼': 'tiny'
}

# Reverse mapping
NAME_TO_EMOJI = {v: k for k, v in EMOJI_TO_NAME.items()}


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


def find_rarity_emoji(rarity_input):
    """Find rarity emoji from input (name or emoji)"""
    rarity_input = rarity_input.lower().strip()
    
    # Check if input is emoji
    if rarity_input in DEFAULT_RARITIES:
        return rarity_input
    
    # Check if input is name
    if rarity_input in NAME_TO_EMOJI:
        return NAME_TO_EMOJI[rarity_input]
    
    # Partial name matching
    for name, emoji in NAME_TO_EMOJI.items():
        if rarity_input in name:
            return emoji
    
    return None


# ==================== VIEW COMMAND ====================
async def rview_command(update: Update, context: CallbackContext):
    """View all rarity spawn settings - Usage: /rview"""
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

        # Calculate statistics
        enabled_count = sum(1 for r in rarities.values() if r['enabled'])
        total_count = len(rarities)
        total_chance = sum(r['chance'] for r in rarities.values() if r['enabled'])

        # Build message
        text = (
            "🎯 **SPAWN RARITY SETTINGS**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 **Status**: {enabled_count}/{total_count} rarities enabled\n"
            f"💯 **Total Chance**: {total_chance:.2f}%\n\n"
            "**Current Configuration:**\n\n"
        )

        # Sort rarities by chance (descending)
        sorted_rarities = sorted(
            rarities.items(),
            key=lambda x: x[1]['chance'],
            reverse=True
        )

        for emoji, data in sorted_rarities:
            status = "✅" if data['enabled'] else "❌"
            text += (
                f"{emoji} **{data['name']}**\n"
                f"  └ Status: {status} | Chance: `{data['chance']:.2f}%`\n"
            )

        text += (
            "\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**Available Commands:**\n"
            "`/renable <rarity>` - Enable a rarity\n"
            "`/rdisable <rarity>` - Disable a rarity\n"
            "`/rchance <rarity> <value>` - Set spawn chance\n"
            "`/rnormalize` - Normalize chances to 100%\n"
            "`/rreset` - Reset to defaults\n"
            "`/renableall` - Enable all rarities\n"
            "`/rdisableall` - Disable all rarities\n\n"
            "**Example:**\n"
            "`/renable legendary`\n"
            "`/rchance mythic 5.0`\n"
            "`/rdisable common`"
        )

        await update.message.reply_text(text, parse_mode='Markdown')
        LOGGER.info(f"Rarity settings viewed by user {user_id}")

    except Exception as e:
        LOGGER.error(f"Error in rview command: {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text("❌ An error occurred while fetching settings.")


# ==================== ENABLE COMMAND ====================
async def renable_command(update: Update, context: CallbackContext):
    """Enable a rarity - Usage: /renable <rarity>"""
    try:
        user_id = update.effective_user.id

        if user_id not in SUDO_USERS:
            await update.message.reply_text("⚠️ Access denied!")
            return

        if not context.args:
            await update.message.reply_text(
                "❌ **Usage:** `/renable <rarity>`\n\n"
                "**Example:** `/renable legendary`",
                parse_mode='Markdown'
            )
            return

        rarity_input = ' '.join(context.args)
        emoji = find_rarity_emoji(rarity_input)

        if not emoji:
            await update.message.reply_text(
                f"❌ Rarity '{rarity_input}' not found!\n"
                "Use `/rview` to see available rarities.",
                parse_mode='Markdown'
            )
            return

        settings = await get_spawn_settings()
        rarities = settings['rarities']

        if rarities[emoji]['enabled']:
            await update.message.reply_text(
                f"ℹ️ {emoji} **{rarities[emoji]['name']}** is already enabled!",
                parse_mode='Markdown'
            )
            return

        rarities[emoji]['enabled'] = True
        await update_spawn_settings(rarities)

        await update.message.reply_text(
            f"✅ Successfully enabled {emoji} **{rarities[emoji]['name']}**!",
            parse_mode='Markdown'
        )
        LOGGER.info(f"User {user_id} enabled rarity: {rarities[emoji]['name']}")

    except Exception as e:
        LOGGER.error(f"Error in renable command: {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text("❌ An error occurred.")


# ==================== DISABLE COMMAND ====================
async def rdisable_command(update: Update, context: CallbackContext):
    """Disable a rarity - Usage: /rdisable <rarity>"""
    try:
        user_id = update.effective_user.id

        if user_id not in SUDO_USERS:
            await update.message.reply_text("⚠️ Access denied!")
            return

        if not context.args:
            await update.message.reply_text(
                "❌ **Usage:** `/rdisable <rarity>`\n\n"
                "**Example:** `/rdisable common`",
                parse_mode='Markdown'
            )
            return

        rarity_input = ' '.join(context.args)
        emoji = find_rarity_emoji(rarity_input)

        if not emoji:
            await update.message.reply_text(
                f"❌ Rarity '{rarity_input}' not found!\n"
                "Use `/rview` to see available rarities.",
                parse_mode='Markdown'
            )
            return

        settings = await get_spawn_settings()
        rarities = settings['rarities']

        if not rarities[emoji]['enabled']:
            await update.message.reply_text(
                f"ℹ️ {emoji} **{rarities[emoji]['name']}** is already disabled!",
                parse_mode='Markdown'
            )
            return

        rarities[emoji]['enabled'] = False
        await update_spawn_settings(rarities)

        await update.message.reply_text(
            f"✅ Successfully disabled {emoji} **{rarities[emoji]['name']}**!",
            parse_mode='Markdown'
        )
        LOGGER.info(f"User {user_id} disabled rarity: {rarities[emoji]['name']}")

    except Exception as e:
        LOGGER.error(f"Error in rdisable command: {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text("❌ An error occurred.")


# ==================== SET CHANCE COMMAND ====================
async def rchance_command(update: Update, context: CallbackContext):
    """Set spawn chance for a rarity - Usage: /rchance <rarity> <percentage>"""
    try:
        user_id = update.effective_user.id

        if user_id not in SUDO_USERS:
            await update.message.reply_text("⚠️ Access denied!")
            return

        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ **Usage:** `/rchance <rarity> <percentage>`\n\n"
                "**Example:** `/rchance legendary 15.5`",
                parse_mode='Markdown'
            )
            return

        # Get percentage (last argument)
        try:
            chance = float(context.args[-1])
        except ValueError:
            await update.message.reply_text("❌ Invalid percentage value!")
            return

        if chance < 0 or chance > 100:
            await update.message.reply_text("❌ Percentage must be between 0 and 100!")
            return

        # Get rarity name (all args except last)
        rarity_input = ' '.join(context.args[:-1])
        emoji = find_rarity_emoji(rarity_input)

        if not emoji:
            await update.message.reply_text(
                f"❌ Rarity '{rarity_input}' not found!\n"
                "Use `/rview` to see available rarities.",
                parse_mode='Markdown'
            )
            return

        settings = await get_spawn_settings()
        rarities = settings['rarities']

        old_chance = rarities[emoji]['chance']
        rarities[emoji]['chance'] = round(chance, 2)
        await update_spawn_settings(rarities)

        await update.message.reply_text(
            f"✅ Updated {emoji} **{rarities[emoji]['name']}** spawn chance!\n"
            f"Previous: `{old_chance:.2f}%` → New: `{chance:.2f}%`\n\n"
            "💡 Tip: Use `/rnormalize` to balance all chances to 100%",
            parse_mode='Markdown'
        )
        LOGGER.info(f"User {user_id} set {rarities[emoji]['name']} chance to {chance}%")

    except Exception as e:
        LOGGER.error(f"Error in rchance command: {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text("❌ An error occurred.")


# ==================== NORMALIZE COMMAND ====================
async def rnormalize_command(update: Update, context: CallbackContext):
    """Normalize all spawn chances to total 100% - Usage: /rnormalize"""
    try:
        user_id = update.effective_user.id

        if user_id not in SUDO_USERS:
            await update.message.reply_text("⚠️ Access denied!")
            return

        settings = await get_spawn_settings()
        rarities = settings['rarities']

        # Get enabled rarities before normalization
        enabled_rarities = {k: v for k, v in rarities.items() if v['enabled']}
        
        if not enabled_rarities:
            await update.message.reply_text("❌ No rarities are enabled!")
            return

        old_total = sum(r['chance'] for r in enabled_rarities.values())

        # Normalize
        rarities = normalize_chances(rarities)
        await update_spawn_settings(rarities)

        new_total = sum(r['chance'] for r in rarities.values() if r['enabled'])

        await update.message.reply_text(
            f"✅ Successfully normalized spawn chances!\n\n"
            f"Previous Total: `{old_total:.2f}%`\n"
            f"New Total: `{new_total:.2f}%`\n\n"
            "All enabled rarities have been proportionally adjusted.",
            parse_mode='Markdown'
        )
        LOGGER.info(f"User {user_id} normalized spawn chances")

    except Exception as e:
        LOGGER.error(f"Error in rnormalize command: {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text("❌ An error occurred.")


# ==================== RESET COMMAND ====================
async def rreset_command(update: Update, context: CallbackContext):
    """Reset all settings to defaults - Usage: /rreset"""
    try:
        user_id = update.effective_user.id

        if user_id not in SUDO_USERS:
            await update.message.reply_text("⚠️ Access denied!")
            return

        rarities = DEFAULT_RARITIES.copy()
        await update_spawn_settings(rarities)

        await update.message.reply_text(
            "✅ Successfully reset all rarity settings to defaults!\n\n"
            "All rarities are now enabled with balanced spawn chances.\n"
            "Use `/rview` to see the current configuration.",
            parse_mode='Markdown'
        )
        LOGGER.info(f"User {user_id} reset spawn settings to defaults")

    except Exception as e:
        LOGGER.error(f"Error in rreset command: {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text("❌ An error occurred.")


# ==================== ENABLE ALL COMMAND ====================
async def renableall_command(update: Update, context: CallbackContext):
    """Enable all rarities - Usage: /renableall"""
    try:
        user_id = update.effective_user.id

        if user_id not in SUDO_USERS:
            await update.message.reply_text("⚠️ Access denied!")
            return

        settings = await get_spawn_settings()
        rarities = settings['rarities']

        for emoji in rarities:
            rarities[emoji]['enabled'] = True

        await update_spawn_settings(rarities)

        await update.message.reply_text(
            "✅ Successfully enabled all rarities!\n\n"
            f"All {len(rarities)} rarities are now active.",
            parse_mode='Markdown'
        )
        LOGGER.info(f"User {user_id} enabled all rarities")

    except Exception as e:
        LOGGER.error(f"Error in renableall command: {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text("❌ An error occurred.")


# ==================== DISABLE ALL COMMAND ====================
async def rdisableall_command(update: Update, context: CallbackContext):
    """Disable all rarities - Usage: /rdisableall"""
    try:
        user_id = update.effective_user.id

        if user_id not in SUDO_USERS:
            await update.message.reply_text("⚠️ Access denied!")
            return

        settings = await get_spawn_settings()
        rarities = settings['rarities']

        for emoji in rarities:
            rarities[emoji]['enabled'] = False

        await update_spawn_settings(rarities)

        await update.message.reply_text(
            "⚠️ Successfully disabled all rarities!\n\n"
            "**Warning:** No characters will spawn until you enable at least one rarity.\n"
            "Use `/renable <rarity>` or `/renableall` to re-enable rarities.",
            parse_mode='Markdown'
        )
        LOGGER.info(f"User {user_id} disabled all rarities")

    except Exception as e:
        LOGGER.error(f"Error in rdisableall command: {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text("❌ An error occurred.")


# ==================== HELP COMMAND ====================
async def rhelp_command(update: Update, context: CallbackContext):
    """Show help for rarity commands - Usage: /rhelp"""
    try:
        user_id = update.effective_user.id

        if user_id not in SUDO_USERS:
            await update.message.reply_text("⚠️ Access denied!")
            return

        text = (
            "🎯 **RARITY CONTROL COMMANDS**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "**View Settings:**\n"
            "`/rview` - View all rarity settings\n\n"
            "**Enable/Disable:**\n"
            "`/renable <rarity>` - Enable a specific rarity\n"
            "`/rdisable <rarity>` - Disable a specific rarity\n"
            "`/renableall` - Enable all rarities\n"
            "`/rdisableall` - Disable all rarities\n\n"
            "**Adjust Spawn Rates:**\n"
            "`/rchance <rarity> <percentage>` - Set spawn chance\n"
            "`/rnormalize` - Balance all chances to 100%\n\n"
            "**Reset:**\n"
            "`/rreset` - Reset to default settings\n\n"
            "**Examples:**\n"
            "```\n"
            "/renable legendary\n"
            "/rdisable common\n"
            "/rchance mythic 2.5\n"
            "/rnormalize\n"
            "```\n\n"
            "**Available Rarities:**\n"
            "common, rare, legendary, special, neon, manga, "
            "cosplay, celestial, premium, erotic, summer, winter, "
            "monsoon, valentine, halloween, christmas, mythic, "
            "events, amv, tiny"
        )

        await update.message.reply_text(text, parse_mode='Markdown')

    except Exception as e:
        LOGGER.error(f"Error in rhelp command: {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text("❌ An error occurred.")


# ==================== HANDLER REGISTRATION ====================
def register_rarity_handlers():
    """Register handlers for rarity control system"""
    try:
        application.add_handler(CommandHandler("rview", rview_command, block=False))
        application.add_handler(CommandHandler("renable", renable_command, block=False))
        application.add_handler(CommandHandler("rdisable", rdisable_command, block=False))
        application.add_handler(CommandHandler("rchance", rchance_command, block=False))
        application.add_handler(CommandHandler("rnormalize", rnormalize_command, block=False))
        application.add_handler(CommandHandler("rreset", rreset_command, block=False))
        application.add_handler(CommandHandler("renableall", renableall_command, block=False))
        application.add_handler(CommandHandler("rdisableall", rdisableall_command, block=False))
        application.add_handler(CommandHandler("rhelp", rhelp_command, block=False))
        
        LOGGER.info("✅ Registered spawn rarity control handlers (command-based)")
    except Exception as e:
        LOGGER.error(f"❌ Failed to register rarity handlers: {e}")


# Export for use in main bot file
__all__ = ['register_rarity_handlers', 'spawn_settings_collection', 'get_spawn_settings']