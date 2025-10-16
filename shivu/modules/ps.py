import random
import time
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)
from telegram.ext import CommandHandler, CallbackQueryHandler, CallbackContext
from shivu import application, user_collection, db

characters_collection = db["anime_characters_lol"]

RARITY_CONFIG = {
    "🟢 Common": {"chance": 60, "min_price": 10000, "max_price": 20000},
    "🟣 Rare": {"chance": 25, "min_price": 20000, "max_price": 40000},
    "🟡 Legendary": {"chance": 10, "min_price": 40000, "max_price": 80000},
    "💮 Special Edition": {"chance": 4, "min_price": 100000, "max_price": 200000},
    "💫 Neon": {"chance": 0.8, "min_price": 120000, "max_price": 250000},
    "🎐 Celestial": {"chance": 0.2, "min_price": 150000, "max_price": 300000},
}

REFRESH_INTERVAL = 86400  # 24h
ITEMS_PER_SESSION = 2


def choose_rarity():
    roll = random.random() * 100
    cumulative = 0
    for rarity, data in RARITY_CONFIG.items():
        cumulative += data["chance"]
        if roll <= cumulative:
            return rarity
    return "🟢 Common"


async def random_character():
    count = await characters_collection.count_documents({})
    if count == 0:
        return None
    skip = random.randint(0, count - 1)
    chars = await characters_collection.find().skip(skip).limit(1).to_list(length=1)
    return chars[0] if chars else None


def make_caption(char, rarity, price, page, total):
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
    session = []
    for _ in range(ITEMS_PER_SESSION):
        char = await random_character()
        if not char:
            continue
        rarity = choose_rarity()
        cfg = RARITY_CONFIG[rarity]
        price = random.randint(cfg["min_price"], cfg["max_price"])
        session.append({"id": char["id"], "rarity": rarity, "price": price, "img": char.get("img_url")})
    await user_collection.update_one(
        {"id": user_id}, {"$set": {"ps_session": session, "ps_refresh": time.time()}}, upsert=True
    )
    return session


async def ps(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data = await user_collection.find_one({"id": user_id}) or {}
    now = time.time()
    if now - user_data.get("ps_refresh", 0) >= REFRESH_INTERVAL or "ps_session" not in user_data:
        session = await generate_session(user_id)
    else:
        session = user_data["ps_session"]

    if not session:
        await update.message.reply_text("no characters available currently.")
        return

    context.user_data["ps_page"] = 0
    await show_ps_page(update, context, session, 0)


async def show_ps_page(update_or_query, context, session, page):
    total = len(session)
    data = session[page]
    char = await characters_collection.find_one({"id": data["id"]})
    caption = make_caption(char, data["rarity"], data["price"], page + 1, total)

    buttons = []
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀", callback_data=f"ps_page_{page-1}"))
    nav.append(InlineKeyboardButton("🔄", callback_data="ps_refresh"))
    if page < total - 1:
        nav.append(InlineKeyboardButton("▶", callback_data=f"ps_page_{page+1}"))
    buttons.append(nav)
    buttons.append([InlineKeyboardButton("ʙᴜʏ", callback_data=f"ps_buy_{data['id']}")])
    markup = InlineKeyboardMarkup(buttons)

    if hasattr(update_or_query, "message"):
        # Initial /ps command
        await update_or_query.message.reply_photo(photo=data["img"], caption=caption, parse_mode="HTML", reply_markup=markup)
    else:
        # CallbackQuery update
        try:
            media = InputMediaPhoto(media=data["img"], caption=caption, parse_mode="HTML")
            await update_or_query.edit_message_media(media=media, reply_markup=markup)
        except:
            await update_or_query.edit_message_caption(caption=caption, reply_markup=markup)


async def ps_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data = await user_collection.find_one({"id": user_id}) or {}
    session = user_data.get("ps_session", [])
    if not session:
        await query.answer("Session expired. Use /ps again.", show_alert=True)
        return
    data = query.data

    if data.startswith("ps_page_"):
        page = int(data.split("_")[2])
        context.user_data["ps_page"] = page
        await show_ps_page(query, context, session, page)
        return

    if data == "ps_refresh":
        await ps(query, context)
        return

    if data.startswith("ps_buy_"):
        char_id = data.split("_")[2]
        item = next((x for x in session if x["id"] == char_id), None)
        if not item:
            await query.answer("Character not found.", show_alert=True)
            return
        char = await characters_collection.find_one({"id": char_id})
        caption = f"╭──────────────╮\n│  ᴄᴏɴꜰɪʀᴍ ʙᴜʏ │\n╰──────────────╯\n\n⋄ {char['name']}\n⋄ ᴘʀɪᴄᴇ: {item['price']:,} ɢᴏʟᴅ\n\nᴘʀᴇꜱꜱ ᴄᴏɴꜰɪʀᴍ ᴛᴏ ᴄᴏᴍᴘʟᴇᴛᴇ."
        buttons = [
            [InlineKeyboardButton("✅ ᴄᴏɴꜰɪʀᴍ", callback_data=f"ps_confirm_{char_id}"),
             InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data="ps_cancel")]
        ]
        await query.edit_message_caption(caption=caption, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("ps_confirm_"):
        char_id = data.split("_")[2]
        item = next((x for x in session if x["id"] == char_id), None)
        balance = user_data.get("balance", 0)
        owned = [c.get("id") for c in user_data.get("characters", [])]
        if char_id in owned:
            await query.answer("Already owned.", show_alert=True)
            return
        if balance < item["price"]:
            await query.edit_message_caption("Not enough gold.", parse_mode="HTML")
            return
        char = await characters_collection.find_one({"id": char_id})
        await user_collection.update_one(
            {"id": user_id},
            {"$inc": {"balance": -item["price"]}, "$push": {"characters": char}},
            upsert=True,
        )
        await query.edit_message_caption(f"Purchase success! You bought {char['name']} for {item['price']:,} gold.", parse_mode="HTML")
        await query.answer("Bought successfully.", show_alert=False)
        return

    if data == "ps_cancel":
        page = context.user_data.get("ps_page", 0)
        await show_ps_page(query, context, session, page)
        await query.answer("Cancelled.", show_alert=False)
        return


def register_handlers(app):
    app.add_handler(CommandHandler("ps", ps, block=False))
    app.add_handler(CallbackQueryHandler(ps_callback, pattern=r"^ps_", block=False))