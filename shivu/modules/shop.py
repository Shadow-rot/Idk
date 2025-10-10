# plugins/store_module.py
import os
import random
from datetime import datetime, timezone
import urllib.request
from pymongo import MongoClient, ReturnDocument
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from shivu.modules.database.sudo import is_user_sudo
from shivu import application, db, collection, CHARA_CHANNEL_ID, SUPPORT_CHAT, sudo_users

# -----------------------------
# Configuration (edit if needed)
# -----------------------------
# Use the requested Mongo URI for waifus DB/storage
WAIFU_MONGO_URI = "mongodb+srv://tiwarireeta004:peqxLEd36RAg7ors@cluster0.furypd3.mongodb.net/?retryWrites=true&w=majority"
WAIFU_DB_NAME = "GRABBING_YOUR_WAIFU"    # keep or update
WAIFU_COLLECTION_NAME = "waifus"        # documents that store waifu info (image_url, id, name, anime_name, rarity, event_id, ...)

# The 'collection' imported from shivu is assumed to be your user collection.
# If your user collection is named differently, change the variable below.
user_collection = collection  # alias for clarity

# Connect only for waifus data — users remain in shivu's collection
_wclient = MongoClient(WAIFU_MONGO_URI)
waifu_db = _wclient[WAIFU_DB_NAME]
waifu_collection = waifu_db[WAIFU_COLLECTION_NAME]

# Map rarities and events (as requested)
rarity_map = {
    1: "🟢 Common",
    2: "🟣 Rare",
    3: "🟡 Legendary",
    4: "💮 Special Edition",
    5: "🔮 Premium Edition",
    6: "🎗️ Supreme"
}

event_map = {
    1: "🏖️ Summer",
    2: "👘 Kimono",
    3: "☃️ Winter",
    4: "💞 Valentine",
    5: "🎒 School",
    6: "🎃 Halloween",
    7: "🎮 Game",
    8: "🎩 Tuxedo",
    9: "👥 Duo",
    10: "🧹 Made",
    11: "☔ Monsoon",
    12: "🐰 Bunny",
    13: "🤝🏻 Group",
    14: "🥻 Saree",
    15: "🎄 Christmas",
    16: "👑 Lord",
    17: "None"
}

# Price ranges per rarity (you can tweak)
RANDOM_PRICE_RANGES = {
    "🟢 Common": (20_000, 80_000),
    "🟣 Rare": (100_000, 300_000),
    "🟡 Legendary": (500_000, 1_500_000),
    "💮 Special Edition": (2_000_000, 5_000_000),
    "🔮 Premium Edition": (8_000_000, 20_000_000),
    "🎗️ Supreme": (30_000_000, 70_000_000),
    # fallback
    "default": (10_000, 50_000)
}

# -----------------------------
# Event schedule (custom date triggers)
# - Admins can update these date ranges manually in code or via DB (example below).
# - Format: { "rarity_name": {"start": datetime(...), "end": datetime(...)} }
# - All datetimes are UTC. Use timezone-aware datetimes.
# -----------------------------
rarity_events = {
    # example (edit these to your desired start/end datetimes):
    # "🟢 Common": {"start": datetime(2025,1,1,tzinfo=timezone.utc), "end": datetime(2026,1,1,tzinfo=timezone.utc)},
}

# -----------------------------
# Helpers
# -----------------------------
def now_utc():
    return datetime.now(timezone.utc)

def rarity_is_active(rarity_name: str) -> bool:
    """Return True if rarity is active based on rarity_events.
       If the rarity is not in rarity_events, assume active by default."""
    cfg = rarity_events.get(rarity_name)
    if not cfg:
        return True
    start = cfg.get("start")
    end = cfg.get("end")
    current = now_utc()
    if start and current < start:
        return False
    if end and current > end:
        return False
    return True

def generate_price_for_rarity(rarity_name: str) -> int:
    rng = RANDOM_PRICE_RANGES.get(rarity_name, RANDOM_PRICE_RANGES["default"])
    return random.randint(rng[0], rng[1])

def format_price(n: int) -> str:
    return f"Ŧ{n:,}"

def waifu_caption(waifu: dict, price: int) -> str:
    name = waifu.get("name", "Unknown")
    anime = waifu.get("anime_name", "Unknown")
    rarity = waifu.get("rarity", "Unknown")
    event_id = waifu.get("event_id")
    event_name = event_map.get(event_id, waifu.get("event", "None"))
    wid = waifu.get("id", waifu.get("_id"))
    caption = (
        f"<b>{name}</b>\n"
        f"🎌 <b>Anime:</b> {anime}\n"
        f"💠 <b>Rarity:</b> {rarity}\n"
        f"🎉 <b>Event:</b> {event_name}\n"
        f"💰 <b>Price:</b> {format_price(price)}\n"
        f"🆔 <b>ID:</b> <code>{wid}</code>\n\n"
        "Tap Buy → Confirm to purchase. Use /bal to check balance."
    )
    return caption

# -----------------------------
# Handlers
# -----------------------------
async def store_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the rarity buttons (only currently active rarities)."""
    # Build buttons for all rarities that are active
    rows = []
    row = []
    for rid, rname in rarity_map.items():
        if rarity_is_active(rname):
            row.append(InlineKeyboardButton(rname, callback_data=f"store_rarity|{rname}|0"))
        # make rows of 2 buttons
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton("🔎 Show all waifus", callback_data="store_all|0")])
    rows.append([InlineKeyboardButton("💰 How to earn coins", callback_data="store_earn_tips")])

    text = (
        "🏪 <b>Welcome to the Waifu Store</b>\n\n"
        "Select a rarity to browse waifus. Only rarities active for current events/dates are shown.\n\n"
        "Tip: If you don't have enough coins, press 'How to earn coins'."
    )

    await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows))

async def store_rarity_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show waifus of a particular rarity, navigable by index."""
    query = update.callback_query
    await query.answer()
    try:
        _, rarity_name, idx_str = query.data.split("|")
        idx = int(idx_str)
    except Exception:
        return await query.edit_message_text("Invalid data.")

    # Only allow if rarity active
    if not rarity_is_active(rarity_name):
        return await query.edit_message_text(f"Rarity {rarity_name} is not active right now.")

    # Fetch waifus of this rarity from waifu_collection
    waifus_cursor = waifu_collection.find({"rarity": rarity_name})
    waifus = await waifus_cursor.to_list(length=1000) if hasattr(waifus_cursor, "to_list") else list(waifus_cursor)

    if not waifus:
        return await query.edit_message_text(f"No waifus found for {rarity_name}.")

    # normalize index
    idx = idx % len(waifus)
    waifu = waifus[idx]
    price = generate_price_for_rarity(rarity_name)

    caption = waifu_caption(waifu, price)

    buttons = [
        [
            InlineKeyboardButton("⬅️ Prev", callback_data=f"store_rarity|{rarity_name}|{(idx - 1) % len(waifus)}"),
            InlineKeyboardButton("➡️ Next", callback_data=f"store_rarity|{rarity_name}|{(idx + 1) % len(waifus)}"),
        ],
        [InlineKeyboardButton("💸 Buy", callback_data=f"buy|{waifu.get('id')}|{price}")],
        [InlineKeyboardButton("🏬 Back", callback_data="store_back")]
    ]

    image_url = waifu.get("image_url") or waifu.get("image") or None

    # If message already has a photo, edit; otherwise edit text to show photo with caption
    try:
        if image_url:
            # edit message media if possible, otherwise edit text with photo
            await query.edit_message_media(
                media=InputMediaPhoto(media=image_url, caption=caption, parse_mode="HTML"),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        else:
            await query.edit_message_text(caption, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")
    except Exception:
        # fallback: send a new message (some clients don't allow editing media)
        await query.message.reply_text(caption, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def store_all_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show a paginated list of all waifus (compact) — shows 5 per page."""
    query = update.callback_query
    await query.answer()
    try:
        _, page_str = query.data.split("|")
        page = int(page_str)
    except Exception:
        page = 0

    per_page = 5
    cursor = waifu_collection.find({})
    all_waifus = await cursor.to_list(length=1000) if hasattr(cursor, "to_list") else list(cursor)
    if not all_waifus:
        return await query.edit_message_text("No waifus in store.")

    total_pages = (len(all_waifus) + per_page - 1) // per_page
    page = page % total_pages
    start = page * per_page
    end = start + per_page
    items = all_waifus[start:end]

    text = "<b>All Waifus — page {}/{}:</b>\n\n".format(page + 1, total_pages)
    for w in items:
        wid = w.get("id", w.get("_id"))
        text += f"• <b>{w.get('name','Unknown')}</b> — {w.get('rarity','?')} — {format_price(generate_price_for_rarity(w.get('rarity','')))}\n  ID: <code>{wid}</code>\n"

    buttons = [
        [
            InlineKeyboardButton("⬅️ Prev", callback_data=f"store_all|{(page - 1) % total_pages}"),
            InlineKeyboardButton("➡️ Next", callback_data=f"store_all|{(page + 1) % total_pages}"),
        ],
        [InlineKeyboardButton("🏬 Back", callback_data="store_back")],
    ]
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def store_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show confirmation for purchase."""
    query = update.callback_query
    await query.answer()
    try:
        _, waifu_id, price_str = query.data.split("|")
        price = int(price_str)
    except Exception:
        return await query.edit_message_text("Invalid buy data.")

    waifu = waifu_collection.find_one({"id": waifu_id}) or waifu_collection.find_one({"_id": waifu_id})
    if not waifu:
        return await query.edit_message_text("Waifu not found.")

    caption = (
        f"Are you sure you want to buy <b>{waifu.get('name','Unknown')}</b>\n"
        f"Price: {format_price(price)}\n\n"
        "Press Confirm to complete the purchase."
    )

    buttons = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_buy|{waifu_id}|{price}"),
            InlineKeyboardButton("❌ Cancel", callback_data="store_back"),
        ]
    ]

    # try to edit caption of current message (if media), otherwise send new message
    try:
        if waifu.get("image_url"):
            await query.edit_message_caption(caption, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await query.edit_message_text(caption, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        await query.message.reply_text(caption, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def store_confirm_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    try:
        _, waifu_id, price_str = query.data.split("|")
        price = int(price_str)
    except Exception:
        return await query.edit_message_text("Invalid confirm data.")

    waifu = waifu_collection.find_one({"id": waifu_id}) or waifu_collection.find_one({"_id": waifu_id})
    if not waifu:
        return await query.edit_message_text("Waifu not found.")

    # get user document
    user_doc = await user_collection.find_one({"id": user_id})
    if not user_doc:
        return await query.edit_message_text("You are not a registered hunter — earn coins first!")

    balance = int(user_doc.get("balance", 0))
    if balance < price:
        tips = (
            "❌ <b>Not enough Gold Coins!</b>\n\n"
            "Ways to earn coins:\n"
            "• Use /roll to gamble/win coins (risky)\n"
            "• Claim /claim daily reward\n"
            "• Play mini-games the bot provides\n"
            "• Climb /Tophunters leaderboard\n\n"
            "Try again when you have enough coins!"
        )
        return await query.edit_message_text(tips, parse_mode="HTML")

    # Deduct and add waifu to user's characters
    await user_collection.update_one(
        {"id": user_id},
        {
            "$inc": {"balance": -price},
            "$push": {"characters": waifu}
        },
    )

    # Success message
    await query.edit_message_text(
        f"✅ You successfully purchased <b>{waifu.get('name','Unknown')}</b> for {format_price(price)}!",
        parse_mode="HTML",
    )

async def store_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # Re-open store menu
    await store_command(update, context)

async def store_earn_tips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "<b>How to earn Gold Coins</b>\n\n"
        "• /roll <amount> ODD/EVEN — try your luck with dice.\n"
        "• /claim — daily reward.\n"
        "• /Tophunters — compete for leaderboard rewards.\n"
        "• Participate in community events and giveaways.\n\n"
        "Good luck, hunter!"
    )
    await query.edit_message_text(text, parse_mode="HTML")

# A simple /mywaifus command to list user's owned waifus
async def mywaifus_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_doc = await user_collection.find_one({"id": user_id})
    if not user_doc or not user_doc.get("characters"):
        return await update.message.reply_text("You don't own any waifus yet. Visit /store to buy one!")

    chars = user_doc.get("characters", [])
    text = "<b>Your Waifus:</b>\n\n"
    for i, c in enumerate(chars, start=1):
        text += f"{i}. <b>{c.get('name','Unknown')}</b> — {c.get('rarity','?')} — ID: <code>{c.get('id')}</code>\n"
    await update.message.reply_text(text, parse_mode="HTML")

# -----------------------------
# Register handlers
# -----------------------------
application.add_handler(CommandHandler("store", store_command, block=False))
application.add_handler(CommandHandler("mywaifus", mywaifus_command, block=False))

application.add_handler(CallbackQueryHandler(store_rarity_callback, pattern=r"^store_rarity\|"))
application.add_handler(CallbackQueryHandler(store_all_callback, pattern=r"^store_all\|"))
application.add_handler(CallbackQueryHandler(store_buy_callback, pattern=r"^buy\|"))
application.add_handler(CallbackQueryHandler(store_confirm_buy, pattern=r"^confirm_buy\|"))
application.add_handler(CallbackQueryHandler(store_back_callback, pattern=r"^store_back$"))
application.add_handler(CallbackQueryHandler(store_earn_tips, pattern=r"^store_earn_tips$"))

# -----------------------------
# Admin helpers (optional)
# - Admins can add/edit rarity_events dict at runtime by editing code or
#   you can extend this module to provide admin commands to set start/end times.
# -----------------------------