# plugins_manager.py
import logging
import importlib
import sys
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from shivu import application, sudo_users, OWNER_ID

LOGGER = logging.getLogger(__name__)

# Dictionary to track loaded plugins and their handlers
LOADED_PLUGINS = {}
AVAILABLE_PLUGINS = []

def is_authorized(user_id: int) -> bool:
    """Check if user is authorized (sudo or owner)"""
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
            "**Example:** `/enable stats`"
        )
        return
    
    plugin_name = context.args[0].lower()
    
    # Check if plugin is already loaded
    if plugin_name in LOADED_PLUGINS:
        await update.message.reply_text(f"⚠️ Plugin `{plugin_name}` is already enabled!")
        return
    
    # Check if plugin exists
    if plugin_name not in AVAILABLE_PLUGINS:
        await update.message.reply_text(
            f"❌ Plugin `{plugin_name}` not found!\n\n"
            f"Available plugins: {', '.join(AVAILABLE_PLUGINS)}"
        )
        return
    
    try:
        # Import the plugin module
        module_path = f"shivu.modules.{plugin_name}"
        
        # Check if already in sys.modules and reload if necessary
        if module_path in sys.modules:
            module = importlib.reload(sys.modules[module_path])
        else:
            module = importlib.import_module(module_path)
        
        # Store the module
        LOADED_PLUGINS[plugin_name] = {
            'module': module,
            'handlers': []
        }
        
        # Register handlers if the module has them
        if hasattr(module, '__handlers__'):
            for handler in module.__handlers__:
                application.add_handler(handler)
                LOADED_PLUGINS[plugin_name]['handlers'].append(handler)
        
        LOGGER.info(f"Plugin {plugin_name} enabled by user {user_id}")
        await update.message.reply_text(f"✅ Plugin `{plugin_name}` has been enabled successfully!")
        
    except Exception as e:
        LOGGER.error(f"Error enabling plugin {plugin_name}: {e}")
        await update.message.reply_text(f"❌ Failed to enable plugin `{plugin_name}`\n\nError: `{str(e)}`")

async def disable_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Disable a plugin dynamically"""
    user_id = update.effective_user.id
    
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ You don't have permission to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ **Usage:** `/disable <plugin_name>`\n\n"
            "**Example:** `/disable stats`"
        )
        return
    
    plugin_name = context.args[0].lower()
    
    # Check if plugin is loaded
    if plugin_name not in LOADED_PLUGINS:
        await update.message.reply_text(f"⚠️ Plugin `{plugin_name}` is not currently enabled!")
        return
    
    try:
        # Remove all handlers for this plugin
        plugin_data = LOADED_PLUGINS[plugin_name]
        
        for handler in plugin_data['handlers']:
            application.remove_handler(handler)
        
        # Remove from loaded plugins
        del LOADED_PLUGINS[plugin_name]
        
        # Remove from sys.modules to ensure clean reload
        module_path = f"shivu.modules.{plugin_name}"
        if module_path in sys.modules:
            del sys.modules[module_path]
        
        LOGGER.info(f"Plugin {plugin_name} disabled by user {user_id}")
        await update.message.reply_text(f"✅ Plugin `{plugin_name}` has been disabled successfully!")
        
    except Exception as e:
        LOGGER.error(f"Error disabling plugin {plugin_name}: {e}")
        await update.message.reply_text(f"❌ Failed to disable plugin `{plugin_name}`\n\nError: `{str(e)}`")

async def pinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show information about loaded plugins"""
    user_id = update.effective_user.id
    
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ You don't have permission to use this command.")
        return
    
    if not LOADED_PLUGINS:
        await update.message.reply_text("📋 **Plugin Information**\n\n⚠️ No plugins are currently loaded!")
        return
    
    response = "📋 **Loaded Plugins Information**\n\n"
    
    for idx, (plugin_name, plugin_data) in enumerate(LOADED_PLUGINS.items(), 1):
        handler_count = len(plugin_data['handlers'])
        response += f"{idx}. `{plugin_name}` - {handler_count} handler(s)\n"
    
    response += f"\n**Total:** {len(LOADED_PLUGINS)} plugin(s) active"
    response += f"\n**Available:** {len(AVAILABLE_PLUGINS)} plugin(s) total"
    
    await update.message.reply_text(response)

async def plist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all available plugins"""
    user_id = update.effective_user.id
    
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ You don't have permission to use this command.")
        return
    
    if not AVAILABLE_PLUGINS:
        await update.message.reply_text("⚠️ No plugins available!")
        return
    
    enabled = [p for p in AVAILABLE_PLUGINS if p in LOADED_PLUGINS]
    disabled = [p for p in AVAILABLE_PLUGINS if p not in LOADED_PLUGINS]
    
    response = "📋 **All Available Plugins**\n\n"
    
    if enabled:
        response += "✅ **Enabled:**\n"
        response += ", ".join(f"`{p}`" for p in sorted(enabled)) + "\n\n"
    
    if disabled:
        response += "❌ **Disabled:**\n"
        response += ", ".join(f"`{p}`" for p in sorted(disabled)) + "\n\n"
    
    response += f"**Total:** {len(AVAILABLE_PLUGINS)} plugin(s)"
    
    await update.message.reply_text(response)

def initialize_plugin_manager(all_modules):
    """Initialize the plugin manager with available modules"""
    global AVAILABLE_PLUGINS, LOADED_PLUGINS
    
    AVAILABLE_PLUGINS = [m for m in all_modules if m != 'plugins_manager']
    
    # Mark all initially loaded modules as loaded
    for module_name in all_modules:
        if module_name != 'plugins_manager':
            module_path = f"shivu.modules.{module_name}"
            if module_path in sys.modules:
                LOADED_PLUGINS[module_name] = {
                    'module': sys.modules[module_path],
                    'handlers': []
                }
    
    LOGGER.info(f"Plugin manager initialized with {len(AVAILABLE_PLUGINS)} available plugins")

# Register handlers
__handlers__ = [
    CommandHandler("enable", enable_command),
    CommandHandler("disable", disable_command),
    CommandHandler("pinfo", pinfo_command),
    CommandHandler("plist", plist_command),
]