"""
Global Callback Router
Add this file as: shivu/callback_router.py
"""

import traceback
from telegram import Update
from telegram.ext import CallbackContext, CallbackQueryHandler
from shivu import application, LOGGER

# Import your callback handlers
from shivu.modules.fav import handle_fav_callback
from shivu.modules.balance import pay_callback

async def global_callback_router(update: Update, context: CallbackContext):
    """Route callback queries to appropriate handlers"""
    query = update.callback_query
    
    if not query or not query.data:
        return
    
    try:
        data = query.data
        
        # Route based on callback data prefix
        if data.startswith('fvc_') or data.startswith('fvx_'):
            # Favorite callbacks
            await handle_fav_callback(update, context)
            
        elif data.startswith('pay_yes_') or data.startswith('pay_no_'):
            # Payment callbacks
            await pay_callback(update, context)
            
        else:
            # Unknown callback - log it
            LOGGER.warning(f"Unknown callback data: {data}")
            await query.answer("Unknown action", show_alert=True)
            
    except Exception as e:
        LOGGER.error(f"[CALLBACK ROUTER ERROR] {e}\n{traceback.format_exc()}")
        try:
            await query.answer("An error occurred", show_alert=True)
        except:
            pass

# Register the global callback handler
application.add_handler(CallbackQueryHandler(global_callback_router, block=False))