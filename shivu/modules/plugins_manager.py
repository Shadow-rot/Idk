# plugins_manager.py
import logging
import importlib
import sys
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

LOGGER = logging.getLogger(__name__)

OWNER_ID = 5147822244

# Dictionary to track loaded plugins and their handler instances
LOADED_PLUGINS = {}
AVAILABLE_PLUGINS = []

def is_authorized(user_id: int) -> bool:
    """Check if user is owner"""
    return user_id == OWNER_ID

async def enable_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enable a plugin dynamically"""
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text("Access denied. Owner only.")
        return

    if not context.args:
        await update.message.reply_text(
            "```\nUsage: /enable <plugin_name>\n\n"
            "Example: /enable stats\n```",
            parse_mode='Markdown'
        )
        return

    plugin_name = context.args[0].lower()

    # Check if plugin is already loaded
    if plugin_name in LOADED_PLUGINS and LOADED_PLUGINS[plugin_name].get('enabled', False):
        await update.message.reply_text(
            f"```\nPlugin '{plugin_name}' is already enabled.\n```",
            parse_mode='Markdown'
        )
        return

    # Check if plugin exists
    if plugin_name not in AVAILABLE_PLUGINS:
        plugins_list = '\n'.join(AVAILABLE_PLUGINS)
        await update.message.reply_text(
            f"```\nPlugin '{plugin_name}' not found.\n\n"
            f"Available plugins:\n{plugins_list}\n```",
            parse_mode='Markdown'
        )
        return

    try:
        from shivu import application

        # Import the plugin module
        module_path = f"shivu.modules.{plugin_name}"

        # Check if already in sys.modules and reload if necessary
        if module_path in sys.modules:
            module = importlib.reload(sys.modules[module_path])
        else:
            module = importlib.import_module(module_path)

        # Create or update plugin data
        if plugin_name not in LOADED_PLUGINS:
            LOADED_PLUGINS[plugin_name] = {
                'module': module,
                'handlers': [],
                'enabled': False
            }
        
        plugin_data = LOADED_PLUGINS[plugin_name]
        plugin_data['module'] = module

        # Remove old handlers if they exist
        for handler in plugin_data.get('handlers', []):
            try:
                application.remove_handler(handler)
            except Exception as e:
                LOGGER.warning(f"Failed to remove old handler: {e}")
        
        plugin_data['handlers'] = []

        # Try to register handlers if available
        handlers_count = 0
        if hasattr(module, '__handlers__'):
            for handler in module.__handlers__:
                try:
                    application.add_handler(handler)
                    plugin_data['handlers'].append(handler)
                    handlers_count += 1
                except Exception as e:
                    LOGGER.warning(f"Failed to add handler from {plugin_name}: {e}")

        plugin_data['enabled'] = True

        LOGGER.info(f"Plugin {plugin_name} enabled by user {user_id}")
        
        if handlers_count > 0:
            await update.message.reply_text(
                f"```\nPlugin '{plugin_name}' enabled successfully.\n"
                f"Handlers loaded: {handlers_count}\n```",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"```\nPlugin '{plugin_name}' loaded successfully.\n"
                f"(No handlers registered)\n```",
                parse_mode='Markdown'
            )

    except Exception as e:
        LOGGER.error(f"Error enabling plugin {plugin_name}: {e}")
        await update.message.reply_text(
            f"```\nFailed to enable plugin '{plugin_name}'.\n\n"
            f"Error: {str(e)}\n```",
            parse_mode='Markdown'
        )

async def disable_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Disable a plugin dynamically"""
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text("Access denied. Owner only.")
        return

    if not context.args:
        await update.message.reply_text(
            "```\nUsage: /disable <plugin_name>\n\n"
            "Example: /disable stats\n```",
            parse_mode='Markdown'
        )
        return

    plugin_name = context.args[0].lower()

    # Check if plugin is loaded
    if plugin_name not in LOADED_PLUGINS or not LOADED_PLUGINS[plugin_name].get('enabled', False):
        await update.message.reply_text(
            f"```\nPlugin '{plugin_name}' is not currently enabled.\n```",
            parse_mode='Markdown'
        )
        return

    # Don't allow disabling the plugin manager itself
    if plugin_name == 'plugins_manager':
        await update.message.reply_text(
            "```\nCannot disable the plugin manager itself.\n```",
            parse_mode='Markdown'
        )
        return

    try:
        from shivu import application

        plugin_data = LOADED_PLUGINS[plugin_name]

        # Remove all handlers that were stored during enable
        removed_handlers = 0
        for handler in plugin_data.get('handlers', []):
            try:
                application.remove_handler(handler)
                removed_handlers += 1
            except Exception as e:
                LOGGER.warning(f"Failed to remove handler from {plugin_name}: {e}")

        # Clear handlers list and mark as disabled
        plugin_data['handlers'] = []
        plugin_data['enabled'] = False

        LOGGER.info(f"Plugin {plugin_name} disabled by user {user_id}")
        
        if removed_handlers > 0:
            await update.message.reply_text(
                f"```\nPlugin '{plugin_name}' disabled successfully.\n"
                f"Handlers removed: {removed_handlers}\n```",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"```\nPlugin '{plugin_name}' disabled successfully.\n```",
                parse_mode='Markdown'
            )

    except Exception as e:
        LOGGER.error(f"Error disabling plugin {plugin_name}: {e}")
        await update.message.reply_text(
            f"```\nFailed to disable plugin '{plugin_name}'.\n\n"
            f"Error: {str(e)}\n```",
            parse_mode='Markdown'
        )

async def pinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show information about loaded plugins"""
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text("Access denied. Owner only.")
        return

    enabled_plugins = {name: data for name, data in LOADED_PLUGINS.items() if data.get('enabled', False)}

    if not enabled_plugins:
        await update.message.reply_text(
            "```\nPlugin Information\n\n"
            "No plugins are currently enabled.\n```",
            parse_mode='Markdown'
        )
        return

    response = "Plugin Information\n\n"

    for idx, (plugin_name, plugin_data) in enumerate(sorted(enabled_plugins.items()), 1):
        handler_count = len(plugin_data.get('handlers', []))
        status = f"{handler_count} handler(s)" if handler_count > 0 else "loaded"
        response += f"{idx}. {plugin_name} - {status}\n"

    response += f"\nTotal: {len(enabled_plugins)} plugin(s) active"
    response += f"\nAvailable: {len(AVAILABLE_PLUGINS)} plugin(s) total"

    await update.message.reply_text(f"```\n{response}\n```", parse_mode='Markdown')

async def plist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all available plugins"""
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text("Access denied. Owner only.")
        return

    if not AVAILABLE_PLUGINS:
        await update.message.reply_text("```\nNo plugins available.\n```", parse_mode='Markdown')
        return

    enabled = [p for p in AVAILABLE_PLUGINS if p in LOADED_PLUGINS and LOADED_PLUGINS[p].get('enabled', False)]
    disabled = [p for p in AVAILABLE_PLUGINS if p not in LOADED_PLUGINS or not LOADED_PLUGINS[p].get('enabled', False)]

    response = "All Available Plugins\n\n"

    if enabled:
        response += "✅ Enabled:\n"
        response += ", ".join(sorted(enabled)) + "\n\n"

    if disabled:
        response += "❌ Disabled:\n"
        response += ", ".join(sorted(disabled)) + "\n\n"

    response += f"Total: {len(AVAILABLE_PLUGINS)} plugin(s)"

    await update.message.reply_text(f"```\n{response}\n```", parse_mode='Markdown')

def initialize_plugin_manager(all_modules):
    """Initialize the plugin manager with available modules"""
    global AVAILABLE_PLUGINS, LOADED_PLUGINS

    # Store all available plugins except the manager itself
    AVAILABLE_PLUGINS = [m for m in all_modules if m != 'plugins_manager']

    # Mark all initially loaded modules as enabled and store their handlers
    for module_name in all_modules:
        if module_name != 'plugins_manager':
            module_path = f"shivu.modules.{module_name}"
            if module_path in sys.modules:
                module = sys.modules[module_path]
                handlers = []
                
                # Get handlers from module if available
                if hasattr(module, '__handlers__'):
                    handlers = list(module.__handlers__)
                
                LOADED_PLUGINS[module_name] = {
                    'module': module,
                    'handlers': handlers,
                    'enabled': True
                }

    LOGGER.info(f"Plugin manager initialized with {len(AVAILABLE_PLUGINS)} available plugins")
    LOGGER.info(f"Currently loaded: {len(LOADED_PLUGINS)} plugins")

def register_handlers(application):
    """Register plugin manager handlers"""
    application.add_handler(CommandHandler("enable", enable_command, block=False))
    application.add_handler(CommandHandler("disable", disable_command, block=False))
    application.add_handler(CommandHandler("pinfo", pinfo_command, block=False))
    application.add_handler(CommandHandler("plist", plist_command, block=False))
    LOGGER.info("Plugin manager handlers registered")

# Export handlers for auto-loading
__handlers__ = [
    CommandHandler("enable", enable_command, block=False),
    CommandHandler("disable", disable_command, block=False),
    CommandHandler("pinfo", pinfo_command, block=False),
    CommandHandler("plist", plist_command, block=False),
]