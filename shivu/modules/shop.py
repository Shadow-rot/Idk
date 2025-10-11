import random
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler

from shivu import application, db, user_collection, CHARA_CHANNEL_ID, SUPPORT_CHAT

# Database collections
collection = db['anime_characters_lol']  # Main character collection
shop_collection = db['shop']  # Shop collection

# Character collection
characters_collection = collection

# Sudo users list
sudo_users = ["8297659126", "8420981179", "5147822244"]

# Items per page
ITEMS_PER_PAGE = 1

async def is_sudo_user(user_id: int) -> bool:
    """Check if user is sudo user"""
    return str(user_id) in sudo_users

async def addshop(update: Update, context: CallbackContext):
    """Add character to shop - Sudo only"""
    user_id = update.effective_user.id
    
    if not await is_sudo_user(user_id):
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: /addshop <character_id> <price>")
        return
    
    try:
        char_id = context.args[0]
        price = int(context.args[1])
        
        if price <= 0:
            await update.message.reply_text("❌ Price must be greater than 0.")
            return
        
        # Check if character exists
        character = await characters_collection.find_one({"id": char_id})
        if not character:
            await update.message.reply_text(f"❌ Character with ID {char_id} not found in database.")
            return
        
        # Check if already in shop
        existing = await shop_collection.find_one({"id": char_id})
        if existing:
            await update.message.reply_text(f"❌ Character {character['name']} is already in the shop.")
            return
        
        # Add to shop with price
        shop_item = {
            "id": char_id,
            "price": price,
            "added_by": user_id,
            "added_at": datetime.utcnow()
        }
        
        await shop_collection.insert_one(shop_item)
        await update.message.reply_text(
            f"✅ Successfully added <b>{character['name']}</b> to shop!\n"
            f"💰 Price: {price} Gold",
            parse_mode="HTML"
        )
    
    except ValueError:
        await update.message.reply_text("❌ Invalid price. Please provide a valid number.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def rmshop(update: Update, context: CallbackContext):
    """Remove character from shop - Sudo only"""
    user_id = update.effective_user.id
    
    if not await is_sudo_user(user_id):
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("❌ Usage: /rmshop <character_id>")
        return
    
    try:
        char_id = context.args[0]
        
        # Check if in shop
        shop_item = await shop_collection.find_one({"id": char_id})
        if not shop_item:
            await update.message.reply_text(f"❌ Character with ID {char_id} is not in the shop.")
            return
        
        # Get character details
        character = await characters_collection.find_one({"id": char_id})
        char_name = character['name'] if character else char_id
        
        # Remove from shop
        await shop_collection.delete_one({"id": char_id})
        await update.message.reply_text(f"✅ Successfully removed <b>{char_name}</b> from shop!", parse_mode="HTML")
    
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

def build_caption(waifu: dict, shop_item: dict, page: int, total: int) -> str:
    """Create HTML caption for the waifu"""
    wid = waifu.get("id", waifu.get("_id"))
    name = waifu.get("name", "Unknown")
    anime = waifu.get("anime", "Unknown")
    rarity = waifu.get("rarity", "Unknown")
    price = shop_item.get("price", 0)
    img_url = waifu.get("img_url", "")

    caption = (
        f"<b>🏪 Character Shop</b>\n\n"
        f"<b>{name}</b>\n"
        f"🎌 <b>Anime:</b> {anime}\n"
        f"💠 <b>Rarity:</b> {rarity}\n"
        f"🆔 <b>ID:</b> <code>{wid}</code>\n"
        f"💰 <b>Price:</b> {price} Gold\n\n"
        f"📄 Page {page}/{total}\n\n"
        "Tap <b>Buy</b> to purchase. Use /bal to check your balance."
    )
    return caption, img_url

async def store(update: Update, context: CallbackContext):
    """Show waifus in the store with pagination"""
    user_id = update.effective_user.id
    
    # Get all shop items
    shop_items = await shop_collection.find({}).to_list(length=None)
    
    if not shop_items:
        await update.message.reply_text("🏪 The shop is currently empty. Check back later!")
        return
    
    # Start at page 0
    page = 0
    total_pages = len(shop_items)
    
    # Store in context for pagination
    context.user_data['shop_items'] = [item['id'] for item in shop_items]
    context.user_data['shop_page'] = page
    
    # Get first character
    char_id = shop_items[page]['id']
    character = await characters_collection.find_one({"id": char_id})
    
    if not character:
        await update.message.reply_text("❌ Error loading shop character.")
        return
    
    caption, img_url = build_caption(character, shop_items[page], page + 1, total_pages)
    
    # Build keyboard
    buttons = []
    nav_buttons = []
    
    if total_pages > 1:
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("◀️ Prev", callback_data=f"shop_page_{page-1}"))
        nav_buttons.append(InlineKeyboardButton("🔄 Refresh", callback_data="shop_refresh"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"shop_page_{page+1}"))
    else:
        nav_buttons.append(InlineKeyboardButton("🔄 Refresh", callback_data="shop_refresh"))
    
    buttons.append([InlineKeyboardButton("💳 Buy", callback_data=f"shop_buy_{char_id}")])
    if nav_buttons:
        buttons.append(nav_buttons)
    
    markup = InlineKeyboardMarkup(buttons)
    
    msg = await update.message.reply_photo(
        photo=img_url,
        caption=caption,
        parse_mode="HTML",
        reply_markup=markup
    )
    
    # Store message ID for editing
    context.user_data['shop_message_id'] = msg.message_id

async def shop_callback(update: Update, context: CallbackContext):
    """Handle all shop callbacks"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    # Handle pagination
    if data.startswith("shop_page_"):
        page = int(data.split("_")[2])
        shop_items_ids = context.user_data.get('shop_items', [])
        
        if not shop_items_ids or page >= len(shop_items_ids):
            await query.answer("❌ Invalid page.", show_alert=True)
            return
        
        context.user_data['shop_page'] = page
        char_id = shop_items_ids[page]
        
        # Get character and shop item
        character = await characters_collection.find_one({"id": char_id})
        shop_item = await shop_collection.find_one({"id": char_id})
        
        if not character or not shop_item:
            await query.answer("❌ Character not found.", show_alert=True)
            return
        
        caption, img_url = build_caption(character, shop_item, page + 1, len(shop_items_ids))
        
        # Build keyboard
        buttons = []
        nav_buttons = []
        
        if len(shop_items_ids) > 1:
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("◀️ Prev", callback_data=f"shop_page_{page-1}"))
            nav_buttons.append(InlineKeyboardButton("🔄 Refresh", callback_data="shop_refresh"))
            if page < len(shop_items_ids) - 1:
                nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"shop_page_{page+1}"))
        else:
            nav_buttons.append(InlineKeyboardButton("🔄 Refresh", callback_data="shop_refresh"))
        
        buttons.append([InlineKeyboardButton("💳 Buy", callback_data=f"shop_buy_{char_id}")])
        if nav_buttons:
            buttons.append(nav_buttons)
        
        markup = InlineKeyboardMarkup(buttons)
        
        try:
            await query.edit_message_media(
                media=query.message.photo[0].file_id if query.message.photo else img_url,
                reply_markup=markup
            )
            await query.edit_message_caption(
                caption=caption,
                parse_mode="HTML",
                reply_markup=markup
            )
        except:
            await query.message.reply_photo(
                photo=img_url,
                caption=caption,
                parse_mode="HTML",
                reply_markup=markup
            )
    
    # Handle refresh
    elif data == "shop_refresh":
        shop_items = await shop_collection.find({}).to_list(length=None)
        
        if not shop_items:
            await query.edit_message_caption("🏪 The shop is currently empty. Check back later!")
            return
        
        # Reset to first page
        page = 0
        context.user_data['shop_items'] = [item['id'] for item in shop_items]
        context.user_data['shop_page'] = page
        
        char_id = shop_items[page]['id']
        character = await characters_collection.find_one({"id": char_id})
        
        if not character:
            await query.answer("❌ Error loading shop.", show_alert=True)
            return
        
        caption, img_url = build_caption(character, shop_items[page], page + 1, len(shop_items))
        
        # Build keyboard
        buttons = []
        nav_buttons = []
        
        if len(shop_items) > 1:
            nav_buttons.append(InlineKeyboardButton("🔄 Refresh", callback_data="shop_refresh"))
            nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"shop_page_{page+1}"))
        else:
            nav_buttons.append(InlineKeyboardButton("🔄 Refresh", callback_data="shop_refresh"))
        
        buttons.append([InlineKeyboardButton("💳 Buy", callback_data=f"shop_buy_{char_id}")])
        if nav_buttons:
            buttons.append(nav_buttons)
        
        markup = InlineKeyboardMarkup(buttons)
        
        await query.edit_message_caption(
            caption=caption,
            parse_mode="HTML",
            reply_markup=markup
        )
        await query.answer("🔄 Shop refreshed!", show_alert=False)
    
    # Handle buy
    elif data.startswith("shop_buy_"):
        char_id = data.split("_", 2)[2]
        
        # Get shop item and character
        shop_item = await shop_collection.find_one({"id": char_id})
        if not shop_item:
            await query.answer("❌ This item is no longer available.", show_alert=True)
            return
        
        character = await characters_collection.find_one({"id": char_id})
        if not character:
            await query.answer("❌ Character not found.", show_alert=True)
            return
        
        price = shop_item.get("price", 0)
        
        # Show confirmation
        buttons = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"shop_confirm_{char_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data="shop_cancel")
            ]
        ]
        markup = InlineKeyboardMarkup(buttons)
        
        await query.edit_message_caption(
            caption=f"<b>Confirm Purchase</b>\n\n"
                    f"<b>{character['name']}</b>\n"
                    f"💰 Price: {price} Gold\n\n"
                    f"Are you sure you want to buy this character?",
            parse_mode="HTML",
            reply_markup=markup
        )
    
    # Handle confirm
    elif data.startswith("shop_confirm_"):
        char_id = data.split("_", 2)[2]
        
        # Get shop item and character
        shop_item = await shop_collection.find_one({"id": char_id})
        if not shop_item:
            await query.answer("❌ This item is no longer available.", show_alert=True)
            return
        
        character = await characters_collection.find_one({"id": char_id})
        if not character:
            await query.answer("❌ Character not found.", show_alert=True)
            return
        
        price = shop_item.get("price", 0)
        
        # Check user balance
        user_data = await user_collection.find_one({"id": user_id})
        balance = user_data.get("balance", 0) if user_data else 0
        
        if balance < price:
            await query.answer("❌ You don't have enough Gold!", show_alert=True)
            await query.edit_message_caption(
                caption=f"❌ <b>Insufficient Balance</b>\n\n"
                        f"You need {price} Gold but only have {balance} Gold.\n"
                        f"Use /bal to check your balance.",
                parse_mode="HTML"
            )
            return
        
        # Process purchase
        await user_collection.update_one(
            {"id": user_id},
            {
                "$inc": {"balance": -price},
                "$push": {"characters": character}
            },
            upsert=True
        )
        
        await query.edit_message_caption(
            caption=f"✅ <b>Purchase Successful!</b>\n\n"
                    f"You bought <b>{character['name']}</b> for {price} Gold!\n"
                    f"The character has been added to your harem.\n\n"
                    f"Remaining balance: {balance - price} Gold",
            parse_mode="HTML"
        )
        await query.answer("✅ Purchase successful!", show_alert=False)
    
    # Handle cancel
    elif data == "shop_cancel":
        page = context.user_data.get('shop_page', 0)
        shop_items_ids = context.user_data.get('shop_items', [])
        
        if not shop_items_ids:
            await query.answer("❌ Session expired. Please use /store again.", show_alert=True)
            return
        
        char_id = shop_items_ids[page]
        character = await characters_collection.find_one({"id": char_id})
        shop_item = await shop_collection.find_one({"id": char_id})
        
        if not character or not shop_item:
            await query.answer("❌ Error loading shop.", show_alert=True)
            return
        
        caption, img_url = build_caption(character, shop_item, page + 1, len(shop_items_ids))
        
        # Build keyboard
        buttons = []
        nav_buttons = []
        
        if len(shop_items_ids) > 1:
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("◀️ Prev", callback_data=f"shop_page_{page-1}"))
            nav_buttons.append(InlineKeyboardButton("🔄 Refresh", callback_data="shop_refresh"))
            if page < len(shop_items_ids) - 1:
                nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"shop_page_{page+1}"))
        else:
            nav_buttons.append(InlineKeyboardButton("🔄 Refresh", callback_data="shop_refresh"))
        
        buttons.append([InlineKeyboardButton("💳 Buy", callback_data=f"shop_buy_{char_id}")])
        if nav_buttons:
            buttons.append(nav_buttons)
        
        markup = InlineKeyboardMarkup(buttons)
        
        await query.edit_message_caption(
            caption=caption,
            parse_mode="HTML",
            reply_markup=markup
        )
        await query.answer("Purchase cancelled.", show_alert=False)

# Register handlers
application.add_handler(CommandHandler("store", store, block=False))
application.add_handler(CommandHandler("addshop", addshop, block=False))
application.add_handler(CommandHandler("rmshop", rmshop, block=False))
application.add_handler(CallbackQueryHandler(shop_callback, pattern=r"^shop_", block=False))