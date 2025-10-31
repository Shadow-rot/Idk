# plugins_manager.py
import logging
import importlib
import sys
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

LOGGER = logging.getLogger(__name__)

OWNER_ID = 5147822244

# Dictionary to track loaded plugins and their handlers
LOADED_PLUGINS = {}
AVAILABLE_PLUGINS = []

def is_authorized(user_id: int) -> bool:
    """Check if user is authorized (sudo or owner)"""
    from shivu import sudo_users, OWNER_ID
    return user_id in sudo_users or user_id == OWNER_ID

async def enable_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enable a plugin dynamically"""
    user_id = update.effective_user.id
    
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ You don't have permission to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ **Usage:** `/enable <plugin_name>`\n\n"
            "**Example:** `/enable stats`",
            parse_mode='Markdown'
        )
        return
    
    plugin_name = context.args[0].lower()
    
    # Check if plugin is already loaded
    if plugin_name in LOADED_PLUGINS and LOADED_PLUGINS[plugin_name].get('enabled', False):
        await update.message.reply_text(f"⚠️ Plugin `{plugin_name}` is already enabled!", parse_mode='Markdown')
        return
    
    # Check if plugin exists
    if plugin_name not in AVAILABLE_PLUGINS:
        await update.message.reply_text(
            f"❌ Plugin `{plugin_name}` not found!\n\n"
            f"Available plugins: {', '.join(AVAILABLE_PLUGINS)}",
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
        
        # Get or create plugin data
        if plugin_name not in LOADED_PLUGINS:
            LOADED_PLUGINS[plugin_name] = {
                'module': module,
                'handlers': [],
                'enabled': False
            }
        
        plugin_data = LOADED_PLUGINS[plugin_name]
        plugin_data['module'] = module
        
        # Remove old handlers if any
        for handler in plugin_data['handlers']:
            try:
                application.remove_handler(handler)
            except:
                pass
        plugin_data['handlers'] = []
        
        # Register handlers if the module has them
        if hasattr(module, '__handlers__'):
            for handler in module.__handlers__:
                application.add_handler(handler)
                plugin_data['handlers'].append(handler)
            plugin_data['enabled'] = True
            LOGGER.info(f"Plugin {plugin_name} enabled by user {user_id}")
            await update.message.reply_text(
                f"✅ Plugin `{plugin_name}` has been enabled successfully!\n"
                f"Loaded {len(plugin_data['handlers'])} handler(s)",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"⚠️ Plugin `{plugin_name}` has no handlers to register!",
                parse_mode='Markdown'
            )
        
    except Exception as e:
        LOGGER.error(f"Error enabling plugin {plugin_name}: {e}")
        await update.message.reply_text(
            f"❌ Failed to enable plugin `{plugin_name}`\n\nError: `{str(e)}`",
            parse_mode='Markdown'
        )

async def disable_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Disable a plugin dynamically"""
    user_id = update.effective_user.id
    
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ You don't have permission to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ **Usage:** `/disable <plugin_name>`\n\n"
            "**Example:** `/disable stats`",
            parse_mode='Markdown'
        )
        return
    
    plugin_name = context.args[0].lower()
    
    # Check if plugin is loaded
    if plugin_name not in LOADED_PLUGINS or not LOADED_PLUGINS[plugin_name].get('enabled', False):
        await update.message.reply_text(
            f"⚠️ Plugin `{plugin_name}` is not currently enabled!",
            parse_mode='Markdown'
        )
        return
    
    # Don't allow disabling the plugin manager itself
    if plugin_name == 'plugins_manager':
        await update.message.reply_text(
            "⛔ Cannot disable the plugin manager itself!",
            parse_mode='Markdown'
        )
        return
    
    try:
        from shivu import application
        
        # Remove all handlers for this plugin
        plugin_data = LOADED_PLUGINS[plugin_name]
        
        for handler in plugin_data['handlers']:
            application.remove_handler(handler)
        
        # Mark as disabled but keep in LOADED_PLUGINS for re-enabling
        plugin_data['enabled'] = False
        plugin_data['handlers'] = []
        
        LOGGER.info(f"Plugin {plugin_name} disabled by user {user_id}")
        await update.message.reply_text(
            f"✅ Plugin `{plugin_name}` has been disabled successfully!",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        LOGGER.error(f"Error disabling plugin {plugin_name}: {e}")
        await update.message.reply_text(
            f"❌ Failed to disable plugin `{plugin_name}`\n\nError: `{str(e)}`",
            parse_mode='Markdown'
        )

async def pinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show information about loaded plugins"""
    user_id = update.effective_user.id
    
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ You don't have permission to use this command.")
        return
    
    enabled_plugins = {name: data for name, data in LOADED_PLUGINS.items() if data.get('enabled', False)}
    
    if not enabled_plugins:
        await update.message.reply_text(
            "📋 **Plugin Information**\n\n⚠️ No plugins are currently enabled!",
            parse_mode='Markdown'
        )
        return
    
    response = "📋 **Loaded Plugins Information**\n\n"
    
    for idx, (plugin_name, plugin_data) in enumerate(sorted(enabled_plugins.items()), 1):
        handler_count = len(plugin_data['handlers'])
        response += f"{idx}. `{plugin_name}` - {handler_count} handler(s)\n"
    
    response += f"\n**Total:** {len(enabled_plugins)} plugin(s) active"
    response += f"\n**Available:** {len(AVAILABLE_PLUGINS)} plugin(s) total"
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def plist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all available plugins"""
    user_id = update.effective_user.id
    
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ You don't have permission to use this command.")
        return
    
    if not AVAILABLE_PLUGINS:
        await update.message.reply_text("⚠️ No plugins available!")
        return
    
    enabled = [p for p in AVAILABLE_PLUGINS if p in LOADED_PLUGINS and LOADED_PLUGINS[p].get('enabled', False)]
    disabled = [p for p in AVAILABLE_PLUGINS if p not in LOADED_PLUGINS or not LOADED_PLUGINS[p].get('enabled', False)]
    
    response = "📋 **All Available Plugins**\n\n"
    
    if enabled:
        response += "✅ **Enabled:**\n"
        response += ", ".join(f"`{p}`" for p in sorted(enabled)) + "\n\n"
    
    if disabled:
        response += "❌ **Disabled:**\n"
        response += ", ".join(f"`{p}`" for p in sorted(disabled)) + "\n\n"
    
    response += f"**Total:** {len(AVAILABLE_PLUGINS)} plugin(s)"
    
    await update.message.reply_text(response, parse_mode='Markdown')

def initialize_plugin_manager(all_modules):
    """Initialize the plugin manager with available modules"""
    global AVAILABLE_PLUGINS, LOADED_PLUGINS
    
    AVAILABLE_PLUGINS = [m for m in all_modules if m != 'plugins_manager']
    
    # Mark all initially loaded modules as loaded and enabled
    for module_name in all_modules:
        if module_name != 'plugins_manager':
            module_path = f"shivu.modules.{module_name}"
            if module_path in sys.modules:
                LOADED_PLUGINS[module_name] = {
                    'module': sys.modules[module_path],
                    'handlers': [],
                    'enabled': True
                }
    
    LOGGER.info(f"Plugin manager initialized with {len(AVAILABLE_PLUGINS)} available plugins")

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