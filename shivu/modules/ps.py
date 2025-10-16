import random
import time
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)
from telegram.ext import CommandHandler, CallbackQueryHandler, CallbackContext
from shivu import application, user_collection, user_totals_collection, db

characters_collection = db["anime_characters_lol"]

RARITY_CONFIG = {
    "🟢 Common": {"chance": 60, "min_price": 10000, "max_price": 20000},
    "🟣 Rare": {"chance": 25, "min_price": 20000, "max_price": 40000},
    "🟡 Legendary": {"chance": 10, "min_price": 40000, "max_price": 80000},
    "💮 Special Edition": {"chance": 4, "min_price": 100000, "max_price": 200000},
    "💫 Neon": {"chance": 0.8, "min_price": 120000, "max_price": 250000},
    "🎐 Celestial": {"chance": 0.2, "min_price": 150000, "max_price": 300000},
}

REFRESH_INTERVAL = 86400  # 24 hours
ITEMS_PER_SESSION = 2


def choose_rarity():
    """Choose rarity based on probability"""
    roll = random.random() * 100
    cumulative = 0
    for rarity, data in RARITY_CONFIG.items():
        cumulative += data["chance"]
        if roll <= cumulative:
            return rarity
    return "🟢 Common"


async def random_character():
    """Get a random character from database"""
    count = await characters_collection.count_documents({})
    if count == 0:
        return None
    skip = random.randint(0, count - 1)
    chars = await characters_collection.find().skip(skip).limit(1).to_list(length=1)
    return chars[0] if chars else None


def make_caption(char, rarity, price, page, total):
    """Create formatted caption for character"""
    wid = char.get("id", char.get("_id"))
    name = char.get("name", "unknown")
    anime = char.get("anime", "unknown")
    return (
        f"╭──────────────╮\n"
        f"│  ᴘʀɪᴠᴀᴛᴇ sᴛᴏʀᴇ │\n"
        f"╰──────────────╯\n\n"
        f"⋄ ɴᴀᴍᴇ: {name.lower()}\n"
        f"⋄ ᴀɴɪᴍᴇ: {anime.lower()}\n"
        f"⋄ ʀᴀʀɪᴛʏ: {rarity}\n"
        f"⋄ ɪᴅ: {wid}\n"
        f"⋄ ᴘʀɪᴄᴇ: {price:,} ɢᴏʟᴅ\n\n"
        f"ᴘᴀɢᴇ: {page}/{total}"
    )


async def generate_session(user_id):
    """Generate new session with random characters"""
    session = []
    for _ in range(ITEMS_PER_SESSION):
        char = await random_character()
        if not char:
            continue
        rarity = choose_rarity()
        cfg = RARITY_CONFIG[rarity]
        price = random.randint(cfg["min_price"], cfg["max_price"])
        session.append({
            "id": char["id"],
            "rarity": rarity,
            "price": price,
            "img": char.get("img_url")
        })
    
    await user_collection.update_one(
        {"id": user_id},
        {"$set": {"ps_session": session, "ps_refresh": time.time()}},
        upsert=True
    )
    return session


async def ps(update: Update, context: CallbackContext):
    """Main /ps command handler"""
    user_id = update.effective_user.id
    user_data = await user_collection.find_one({"id": user_id})
    
    if not user_data:
        await update.message.reply_text("ᴘʟᴇᴀsᴇ sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ ғɪʀsᴛ ᴜsɪɴɢ /start")
        return
    
    now = time.time()
    needs_refresh = (
        now - user_data.get("ps_refresh", 0) >= REFRESH_INTERVAL or
        "ps_session" not in user_data or
        not user_data.get("ps_session")
    )
    
    if needs_refresh:
        session = await generate_session(user_id)
    else:
        session = user_data["ps_session"]

    if not session:
        await update.message.reply_text("ɴᴏ ᴄʜᴀʀᴀᴄᴛᴇʀs ᴀᴠᴀɪʟᴀʙʟᴇ ᴄᴜʀʀᴇɴᴛʟʏ.")
        return

    context.user_data["ps_page"] = 0
    context.user_data["ps_user_id"] = user_id
    await show_ps_page(update, context, session, 0)


async def show_ps_page(update_or_query, context, session, page):
    """Display a specific page of the private store"""
    total = len(session)
    if page >= total or page < 0:
        page = 0
    
    data = session[page]
    char = await characters_collection.find_one({"id": data["id"]})
    
    if not char:
        if hasattr(update_or_query, "message"):
            await update_or_query.message.reply_text("ᴄʜᴀʀᴀᴄᴛᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ.")
        else:
            await update_or_query.answer("ᴄʜᴀʀᴀᴄᴛᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ.", show_alert=True)
        return
    
    caption = make_caption(char, data["rarity"], data["price"], page + 1, total)

    # Navigation buttons
    buttons = []
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀", callback_data=f"ps_page_{page-1}"))
    nav.append(InlineKeyboardButton("🔄 ʀᴇғʀᴇsʜ", callback_data="ps_refresh"))
    if page < total - 1:
        nav.append(InlineKeyboardButton("▶", callback_data=f"ps_page_{page+1}"))
    
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("✅ ʙᴜʏ", callback_data=f"ps_buy_{data['id']}")])
    markup = InlineKeyboardMarkup(buttons)

    if hasattr(update_or_query, "message"):
        # Initial /ps command - send new message
        await update_or_query.message.reply_photo(
            photo=data["img"],
            caption=caption,
            parse_mode="HTML",
            reply_markup=markup
        )
    else:
        # CallbackQuery update - edit same message
        try:
            # Try to edit the media (image + caption)
            media = InputMediaPhoto(media=data["img"], caption=caption, parse_mode="HTML")
            await update_or_query.edit_message_media(media=media, reply_markup=markup)
        except Exception as e:
            print(f"Error editing media: {e}")
            # If media edit fails, just try to update caption
            try:
                await update_or_query.edit_message_caption(
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=markup
                )
            except Exception as e2:
                print(f"Error editing caption: {e2}")
                # If all else fails, answer the callback
                await update_or_query.answer("ᴇʀʀᴏʀ ᴜᴘᴅᴀᴛɪɴɢ ᴘᴀɢᴇ.", show_alert=True)


async def ps_callback(update: Update, context: CallbackContext):
    """Handle all private store callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = await user_collection.find_one({"id": user_id})
    
    if not user_data:
        await query.answer("ᴘʟᴇᴀsᴇ sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ ғɪʀsᴛ.", show_alert=True)
        return
    
    session = user_data.get("ps_session", [])
    if not session:
        await query.answer("sᴇssɪᴏɴ ᴇxᴘɪʀᴇᴅ. ᴜsᴇ /ps ᴀɢᴀɪɴ.", show_alert=True)
        return
    
    data = query.data

    # Page navigation
    if data.startswith("ps_page_"):
        page = int(data.split("_")[2])
        context.user_data["ps_page"] = page
        await show_ps_page(query, context, session, page)
        return

    # Refresh store
    if data == "ps_refresh":
        new_session = await generate_session(user_id)
        context.user_data["ps_page"] = 0
        await show_ps_page(query, context, new_session, 0)
        await query.answer("sᴛᴏʀᴇ ʀᴇғʀᴇsʜᴇᴅ!", show_alert=False)
        return

    # Buy button clicked
    if data.startswith("ps_buy_"):
        char_id = data.split("_")[2]
        item = next((x for x in session if x["id"] == char_id), None)
        
        if not item:
            await query.answer("ᴄʜᴀʀᴀᴄᴛᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ.", show_alert=True)
            return
        
        char = await characters_collection.find_one({"id": char_id})
        if not char:
            await query.answer("ᴄʜᴀʀᴀᴄᴛᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ ɪɴ ᴅᴀᴛᴀʙᴀsᴇ.", show_alert=True)
            return
        
        caption = (
            f"╭──────────────╮\n"
            f"│  ᴄᴏɴғɪʀᴍ ʙᴜʏ │\n"
            f"╰──────────────╯\n\n"
            f"⋄ ɴᴀᴍᴇ: {char['name'].lower()}\n"
            f"⋄ ʀᴀʀɪᴛʏ: {item['rarity']}\n"
            f"⋄ ᴘʀɪᴄᴇ: {item['price']:,} ɢᴏʟᴅ\n\n"
            f"ᴘʀᴇss ᴄᴏɴғɪʀᴍ ᴛᴏ ᴄᴏᴍᴘʟᴇᴛᴇ ᴘᴜʀᴄʜᴀsᴇ."
        )
        buttons = [
            [
                InlineKeyboardButton("✅ ᴄᴏɴғɪʀᴍ", callback_data=f"ps_confirm_{char_id}"),
                InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data="ps_cancel")
            ]
        ]
        await query.edit_message_caption(
            caption=caption,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # Confirm purchase
    if data.startswith("ps_confirm_"):
        char_id = data.split("_")[2]
        item = next((x for x in session if x["id"] == char_id), None)
        
        if not item:
            await query.answer("ᴄʜᴀʀᴀᴄᴛᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ.", show_alert=True)
            return
        
        balance = user_data.get("balance", 0)
        
        # Check if already owned
        owned_ids = [c.get("id") for c in user_data.get("characters", [])]
        if char_id in owned_ids:
            await query.answer("ʏᴏᴜ ᴀʟʀᴇᴀᴅʏ ᴏᴡɴ ᴛʜɪs ᴄʜᴀʀᴀᴄᴛᴇʀ.", show_alert=True)
            return
        
        # Check balance
        if balance < item["price"]:
            await query.edit_message_caption(
                caption=f"❌ ɴᴏᴛ ᴇɴᴏᴜɢʜ ɢᴏʟᴅ!\n\nʏᴏᴜʀ ʙᴀʟᴀɴᴄᴇ: {balance:,}\nʀᴇǫᴜɪʀᴇᴅ: {item['price']:,}",
                parse_mode="HTML"
            )
            await query.answer("ɪɴsᴜғғɪᴄɪᴇɴᴛ ʙᴀʟᴀɴᴄᴇ.", show_alert=True)
            return
        
        # Get character data
        char = await characters_collection.find_one({"id": char_id})
        if not char:
            await query.answer("ᴄʜᴀʀᴀᴄᴛᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ.", show_alert=True)
            return
        
        # Update user collection and balance
        await user_collection.update_one(
            {"id": user_id},
            {
                "$inc": {"balance": -item["price"]},
                "$push": {"characters": char}
            },
            upsert=True
        )
        
        # Update user totals collection
        await user_totals_collection.update_one(
            {"id": user_id},
            {"$inc": {"count": 1}},
            upsert=True
        )
        
        # Success message
        new_balance = balance - item["price"]
        success_caption = (
            f"✅ ᴘᴜʀᴄʜᴀsᴇ sᴜᴄᴄᴇssғᴜʟ!\n\n"
            f"⋄ ʙᴏᴜɢʜᴛ: {char['name'].lower()}\n"
            f"⋄ ᴘʀɪᴄᴇ: {item['price']:,} ɢᴏʟᴅ\n"
            f"⋄ ɴᴇᴡ ʙᴀʟᴀɴᴄᴇ: {new_balance:,} ɢᴏʟᴅ\n\n"
            f"ᴄʜᴀʀᴀᴄᴛᴇʀ ᴀᴅᴅᴇᴅ ᴛᴏ ʏᴏᴜʀ ᴄᴏʟʟᴇᴄᴛɪᴏɴ!"
        )
        await query.edit_message_caption(caption=success_caption, parse_mode="HTML")
        await query.answer("ʙᴏᴜɢʜᴛ sᴜᴄᴄᴇssғᴜʟʟʏ!", show_alert=False)
        return

    # Cancel purchase
    if data == "ps_cancel":
        page = context.user_data.get("ps_page", 0)
        await show_ps_page(query, context, session, page)
        await query.answer("ᴘᴜʀᴄʜᴀsᴇ ᴄᴀɴᴄᴇʟʟᴇᴅ.", show_alert=False)
        return


# Register handlers
application.add_handler(CommandHandler("ps", ps, block=False))
application.add_handler(CallbackQueryHandler(ps_callback, pattern=r"^ps_", block=False))