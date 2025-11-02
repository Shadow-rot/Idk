from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, db

collection = db['anime_characters_lol']

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

async def rarity_count(update: Update, context: CallbackContext) -> None:
    try:
        args = context.args
        
        if not args:
            response = "<blockquote><b>Rarity List</b></blockquote>\n\n"
            for num, name in RARITY_MAP.items():
                response += f"<code>{num}</code> → {name}\n"
            response += f"\n<b>Usage:</b> <code>/r number</code>\n<b>Example:</b> <code>/r 1</code>"
            await update.message.reply_text(response, parse_mode='HTML')
            return

        try:
            rarity_num = int(args[0])
        except ValueError:
            await update.message.reply_text(
                "<blockquote>Please provide a valid rarity number (1-20)</blockquote>",
                parse_mode='HTML'
            )
            return

        if rarity_num not in RARITY_MAP:
            await update.message.reply_text(
                "<blockquote>Invalid rarity. Use number between 1-20</blockquote>",
                parse_mode='HTML'
            )
            return

        rarity_name = RARITY_MAP[rarity_num]
        
        # Count with multiple formats
        count_string = await collection.count_documents({'rarity': rarity_name})
        count_number = await collection.count_documents({'rarity': rarity_num})
        emoji = rarity_name.split()[0]
        count_emoji = await collection.count_documents({'rarity': {'$regex': f'^{emoji}'}})
        
        total = max(count_string, count_number, count_emoji)
        
        # Get sample characters
        sample = await collection.find({
            '$or': [
                {'rarity': rarity_name},
                {'rarity': rarity_num},
                {'rarity': {'$regex': f'^{emoji}'}}
            ]
        }).limit(5).to_list(length=5)
        
        response = f"<blockquote><b>{rarity_name}</b></blockquote>\n\n"
        response += f"<b>Total Characters:</b> <code>{total}</code>\n"
        
        if sample:
            response += f"\n<b>Sample Characters:</b>\n\n"
            for char in sample:
                response += f"<code>{char.get('id', '??')}</code> <b>{char.get('name', 'Unknown')}</b>\n"
                response += f"From: <i>{char.get('anime', 'Unknown')}</i>\n\n"
            
            if total > 5:
                response += f"<i>And {total - 5} more...</i>"
        
        # Navigation buttons
        keyboard = []
        nav = []
        
        if rarity_num > 1:
            nav.append(InlineKeyboardButton("← Previous", callback_data=f"rarity_{rarity_num - 1}"))
        
        if rarity_num < 20:
            nav.append(InlineKeyboardButton("Next →", callback_data=f"rarity_{rarity_num + 1}"))
        
        if nav:
            keyboard.append(nav)
        
        keyboard.append([InlineKeyboardButton("View All", callback_data="rarity_all")])
        
        await update.message.reply_text(
            response, 
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        await update.message.reply_text(f"<blockquote>Error: {str(e)}</blockquote>", parse_mode='HTML')

async def rarity_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    try:
        if query.data == "rarity_all":
            response = "<blockquote><b>All Rarities</b></blockquote>\n\n"
            
            for num, name in RARITY_MAP.items():
                count_string = await collection.count_documents({'rarity': name})
                count_number = await collection.count_documents({'rarity': num})
                emoji = name.split()[0]
                count_emoji = await collection.count_documents({'rarity': {'$regex': f'^{emoji}'}})
                total = max(count_string, count_number, count_emoji)
                
                response += f"<code>{num:2d}</code> {name} → <code>{total}</code>\n"
            
            response += f"\n<i>Use /r number for details</i>"
            
            await query.edit_message_text(
                response,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Close", callback_data="close")]])
            )
            return
        
        if query.data == "close":
            await query.message.delete()
            return
        
        rarity_num = int(query.data.split('_')[1])
        rarity_name = RARITY_MAP[rarity_num]
        
        # Count
        count_string = await collection.count_documents({'rarity': rarity_name})
        count_number = await collection.count_documents({'rarity': rarity_num})
        emoji = rarity_name.split()[0]
        count_emoji = await collection.count_documents({'rarity': {'$regex': f'^{emoji}'}})
        total = max(count_string, count_number, count_emoji)
        
        # Sample
        sample = await collection.find({
            '$or': [
                {'rarity': rarity_name},
                {'rarity': rarity_num},
                {'rarity': {'$regex': f'^{emoji}'}}
            ]
        }).limit(5).to_list(length=5)
        
        response = f"<blockquote><b>{rarity_name}</b></blockquote>\n\n"
        response += f"<b>Total Characters:</b> <code>{total}</code>\n"
        
        if sample:
            response += f"\n<b>Sample Characters:</b>\n\n"
            for char in sample:
                response += f"<code>{char.get('id', '??')}</code> <b>{char.get('name', 'Unknown')}</b>\n"
                response += f"From: <i>{char.get('anime', 'Unknown')}</i>\n\n"
            
            if total > 5:
                response += f"<i>And {total - 5} more...</i>"
        
        # Navigation
        keyboard = []
        nav = []
        
        if rarity_num > 1:
            nav.append(InlineKeyboardButton("← Previous", callback_data=f"rarity_{rarity_num - 1}"))
        
        if rarity_num < 20:
            nav.append(InlineKeyboardButton("Next →", callback_data=f"rarity_{rarity_num + 1}"))
        
        if nav:
            keyboard.append(nav)
        
        keyboard.append([InlineKeyboardButton("View All", callback_data="rarity_all")])
        
        await query.edit_message_text(
            response,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)

# Register command handler only (callback is handled by global router)
application.add_handler(CommandHandler('r', rarity_count, block=False))