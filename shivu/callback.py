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
from shivu.modules.balance import callback_handler
from shivu.modules.gift import handle_gift_callback 
from shivu.modules.check import handle_show_owners, handle_back_to_card, handle_char_stats
from shivu.modules.games import games_callback_query
from shivu.modules.harem import harem_callback, mode_button, handle_unfav_callback, handle_char_count_info
from shivu.modules.help import help_callback
from shivu.modules.inlinequery import show_smashers_callback
from shivu.modules.pass_system import pass_callback
from shivu.modules.shop import shop_callback
from shivu.modules.ps import luv_callback
from shivu.modules.start import button_callback
from shivu.modules.find import rarity_callback  # Add rarity callback import

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

        elif data.startswith(('bal_', 'bank_', 'loan_', 'repay_', 'clr_', 'pok_', 'pno_', 'help_guide_')):
            # Balance module callbacks (bal, bank, loan, repay, clear, poke, etc.)
            await callback_handler(update, context)

        elif data.startswith('gift_confirm:') or data.startswith('gift_cancel:'): 
            # Gift callbacks 
            await handle_gift_callback(update, context)

        elif data.startswith('show_owners_'):
            # Show owners callback
            await handle_show_owners(update, context)

        elif data.startswith('back_to_card_'):
            # Back to card callback
            await handle_back_to_card(update, context)

        elif data.startswith('char_stats_'):
            # Character stats callback
            await handle_char_stats(update, context)

        elif data.startswith('rarity_') or data == 'close':
            # Rarity callbacks (rarity_1, rarity_all, close)
            await rarity_callback(update, context)

        elif data.startswith('games:repeat:'):
            # Games repeat callback
            await games_callback_query(update, context)

        elif data.startswith('harem_page:'):
            # Harem pagination callback
            await harem_callback(update, context)

        elif data.startswith('harem_mode_'):
            # Harem mode button callback
            await mode_button(update, context)

        elif data.startswith('harem_unfav_'):
            # Harem unfavorite callback
            await handle_unfav_callback(update, context)

        elif data == 'harem_char_count':
            # Harem character count info callback
            await handle_char_count_info(update, context)

        elif data.startswith('hlp_') and len(data) >= 8:
            # Help callback (pattern: hlp_XX_N where XX is 2 letters, N is digit)
            await help_callback(update, context)

        elif data.startswith('show_smashers_'):
            # Show smashers callback (inline query)
            await show_smashers_callback(update, context)

        elif data.startswith('ps_'):
            # Pass system callback
            await pass_callback(update, context)

        elif data.startswith('luv_'):
            # LUV store callback
            await luv_callback(update, context)

        elif data.startswith('shop_'):
            # Shop callback
            await shop_callback(update, context)

        else:
            # Start module button_callback handles all remaining callbacks
            # This should be last as it's a catch-all
            await button_callback(update, context)

    except Exception as e: 
        LOGGER.error(f"[CALLBACK ROUTER ERROR] {e}\n{traceback.format_exc()}") 
        try: 
            await query.answer("An error occurred", show_alert=True) 
        except: 
            pass 

# Register the global callback handler 
application.add_handler(CallbackQueryHandler(global_callback_router, block=False))