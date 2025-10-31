import importlib
import pkgutil
import traceback
from telegram import Update
from telegram.ext import CallbackContext

from shivu import application


# Prefix-based cache for faster routing
callback_modules = {}

async def global_callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data or ""
    await query.answer()

    try:
        # Check cache first
        for prefix, handler_func in callback_modules.items():
            if data.startswith(prefix):
                await handler_func(update, context, data)
                return

        # Auto-discover modules in shivu/plugins
        for module_info in pkgutil.iter_modules(["shivu/modules"]):
            mod_name = module_info.name
            full_name = f"shivu.modules.{mod_name}"

            try:
                module = importlib.import_module(full_name)
                if hasattr(module, "handle_callback"):
                    handler_func = getattr(module, "handle_callback")
                    if callable(handler_func):
                        # Store prefix for reuse
                        prefix = getattr(module, "CALLBACK_PREFIX", mod_name + "_")
                        callback_modules[prefix] = handler_func
                        if data.startswith(prefix):
                            await handler_func(update, context, data)
                            return
            except Exception as e:
                print(f"❌ Error loading module {mod_name}: {e}")

        # Fallback
        await query.edit_message_text("⚙ Unknown action, please try again.")
    except Exception as e:
        print("⚠ Callback Error:", e)
        traceback.print_exc()
        await query.answer("Error occurred.", show_alert=True)