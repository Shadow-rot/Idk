# plugins/store.py
import urllib.request
from pymongo import ReturnDocument
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from shivu.modules.database.sudo import is_user_sudo
from shivu import application, collection, db, CHARA_CHANNEL_ID, SUPPORT_CHAT, sudo_users

import random
from datetime import datetime

# -----------------------
# Configuration / Maps
# -----------------------

# Rarity names used in your upload code and DB
RARITY_BY_NUMBER = {
    1: "🟢 Common",
    2: "🟣 Rare",
    3: "🟡 Legendary",
    4: "💮 Special Edition",
    5: "🔮 Premium Edition",
    6: "🎗️ Supreme",
}

# Event mapping (same as your upload module style)
EVENT_MAPPING = {
    1: {"name": "𝒔𝒖𝒎𝒎𝒆𝒓", "sign": "🏖"},
    2: {"name": "𝑲𝒊𝒎𝒐𝒏𝒐", "sign": "👘"},
    3: {"name": "𝑾𝒊𝒏𝒕𝒆𝒓", "sign": "☃️"},
    4: {"name": "𝑽𝒂𝒍𝒆𝒏𝒕𝒊𝒏𝒆", "sign": "💞"},
    5: {"name": "𝑺𝒄𝒉𝒐𝒐𝒍", "sign": "🎒"},
    6: {"name": "𝑯𝒂𝒍𝒍𝒐𝒘𝒆𝒆𝒏", "sign": "🎃"},
    7: {"name": "𝑮𝒂𝒎𝒆", "sign": "🎮"},
    8: {"name": "𝑻𝒖𝒙𝒆𝒅𝒐", "sign": "🎩"},
    9: {"name": "𝐃𝐮𝐨", "sign": "👥"},
    10: {"name": "𝑴𝒂𝒅𝒆", "sign": "🧹"},
    11: {"name": "𝑴𝒐𝒏𝒔𝒐𝒐𝒏", "sign": "☔"},
    12: {"name": "𝑩𝒖𝒏𝒏𝒚", "sign": "🐰"},
    13: {"name": "𝐆𝐫𝐨𝐮𝐩", "sign": "🤝🏻"},
    14: {"name": "𝑺𝒂𝒓𝒆𝒆", "sign": "🥻"},
    15: {"name": "𝑪𝒓𝒊𝒔𝒕𝒎𝒂𝒔", "sign": "🎄"},
    16: {"name": "𝑳𝒐𝒓𝒅", "sign": "👑"},
    17: None
}

# Rarity-to-random-price ranges (gold coins). Tune as you like.
PRICE_RANGES = {
    "🟢 Common": (100, 300),
    "🟣 Rare": (400, 800),
    "🟡 Legendary": (1000, 2000),
    "💮 Special Edition": (2000, 4000),
    "🔮 Premium Edition": (4000, 8000),
    "🎗️ Supreme": (8000, 15000),
    # fallback
    "default": (150, 500),
}

# Auto-activate event rarities by month (real-time)
# Map event "name" (string) to months (list). If a rarity has event with given name -> active in those months.
EVENT_MONTH_ACTIVATION = {
    "𝑯𝒂𝒍𝒍𝒐𝒘𝒆𝒆𝒏": [10],                  # October
    "𝑾𝒊𝒏𝒕𝒆𝒓": [12, 1],                      # Dec & Jan
    "𝒔𝒖𝒎𝒎𝒆𝒓": [6, 7, 8],                   # June-July-Aug
    "𝑽𝒂𝒍𝒆𝒏𝒕𝒊𝒏𝒆": [2],                     # February
    "𝑪𝒓𝒊𝒔𝒕𝒎𝒂𝒔": [12],                     # December
    # Add more mappings if you need them (e.g., Kimono -> certain month)
}

# for convenience: user_collection (balance storage) — try to import from shivu if present
# Many of your earlier modules use `user_collection` variable; if not present, fallback to `db.users`
try:
    user_collection = getattr(__import__("shivu", fromlist=["user_collection"]), "user_collection")
except Exception:
    # fallback if shivu doesn't expose user_collection; assume users are in `db.users`
    user_collection = db.users

# -----------------------
# Helper functions
# -----------------------
def now_month():
    return datetime.utcnow().month

def is_event_active_for_waifu(waifu_doc: dict) -> bool:
    """Return True if waifu is available now based on its event field.
       If waifu['event'] is None or event not mapped, treat as always active."""
    event = waifu_doc.get("event")
    if not event:
        return True
    # event may be stored as dict like {"name": "...", "sign": "🏖"}
    name = event.get("name") if isinstance(event, dict) else event
    if not name:
        return True
    months = EVENT_MONTH_ACTIVATION.get(name)
    if not months:
        return True
    return now_month() in months

def generate_price_for_rarity(rarity_name: str) -> int:
    rng = PRICE_RANGES.get(rarity_name, PRICE_RANGES["default"])
    return random.randint(rng[0], rng[1])

def fmt_price(n: int) -> str:
    return f"💰 {n:,} Gold"

def waifu_caption(waifu: dict, price: int) -> str:
    wid = waifu.get("id", waifu.get("_id"))
    name = waifu.get("name", "Unknown")
    anime = waifu.get("anime", waifu.get("anime_name", "Unknown"))
    rarity = waifu.get("rarity", "Unknown")
    event = waifu.get("event")
    event_text = ""
    if isinstance(event, dict) and event.get("name"):
        event_text = f"{event.get('sign', '')} {event.get('name')}"
    elif isinstance(event, str):
        event_text = event
    caption = (
        f"<b>{name}</b>\n"
        f"🎌 <b>Anime:</b> {anime}\n"
        f"💠 <b>Rarity:</b> {rarity}\n"
        f"{('🎉 <b>Event:</b> ' + event_text + '\\n') if event_text else ''}"
        f"🆔 <b>ID:</b> <code>{wid}</code>\n"
        f"{fmt_price(price)}\n\n"
        "Tap Buy → Confirm to purchase. Use /bal to check your gold balance."
    )
    return caption

# -----------------------
# Core Handlers
# -----------------------

async def store_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show rarity menu (auto-hides rarities with event not active)."""
    # Build list of all rarities present in DB distinct; fallback to default list
    try:
        # get distinct rarities from collection if possible
        rarities = await collection.distinct("rarity")
        if not rarities:
            rarities = list(RARITY_BY_NUMBER.values())
    except Exception:
        rarities = list(RARITY_BY_NUMBER.values())

    buttons = []
    row = []
    for r in rarities:
        # check at least one waifu of that rarity is active now
        has_active = await collection.find_one({"rarity": r})
        if not has_active:
            continue
        # quick availability check: if any waifu in that rarity passes is_event_active_for_waifu
        cursor = collection.find({"rarity": r})
        try:
            waifus = await cursor.to_list(length=100)
        except Exception:
            waifus = list(cursor)
        active_found = any(is_event_active_for_waifu(w) for w in waifus)
        if not active_found:
            # skip rarity that's not active currently
            continue

        row.append(InlineKeyboardButton(r, callback_data=f"store:rarity:{r}:0"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("🔎 Show all waifus", callback_data="store:all:0")])
    buttons.append([InlineKeyboardButton("💡 How to earn gold", callback_data="store:tips")])
    # add quick links
    buttons.append([
        InlineKeyboardButton("📦 My Waifus", callback_data="store:my:0"),
        InlineKeyboardButton("🔄 Refresh", callback_data="store:refresh")
    ])

    text = (
        "<b>🏪 Waifu Store</b>\n\n"
        "Select a rarity to browse available waifus. Rarities for special events appear automatically during their event months.\n\n"
        "Tip: If you don't have enough gold, press 'How to earn gold' for ways to earn (roll, claim, leaderboard)."
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))


async def rarity_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show a waifu of the selected rarity; navigation via index."""
    query = update.callback_query
    await query.answer()
    # callback format: store:rarity:<rarity_name>:<index>
    try:
        _, action, rarity_name, idx_str = query.data.split(":", 3)
        idx = int(idx_str)
    except Exception:
        return await query.edit_message_text("Invalid data format.")

    # fetch all waifus for rarity and filter by event activation
    cursor = collection.find({"rarity": rarity_name})
    try:
        waifus = await cursor.to_list(length=1000)
    except Exception:
        waifus = list(cursor)

    waifus = [w for w in waifus if is_event_active_for_waifu(w)]
    if not waifus:
        return await query.edit_message_text(f"No active waifus currently for {rarity_name}.")

    idx %= len(waifus)
    waifu = waifus[idx]
    price = generate_price_for_rarity(rarity_name)

    caption = waifu_caption(waifu, price)

    buttons = [
        [
            InlineKeyboardButton("⬅️ Prev", callback_data=f"store:rarity:{rarity_name}:{(idx - 1) % len(waifus)}"),
            InlineKeyboardButton("➡️ Next", callback_data=f"store:rarity:{rarity_name}:{(idx + 1) % len(waifus)}"),
        ],
        [
            InlineKeyboardButton("💸 Buy", callback_data=f"store:buy:{waifu.get('id')}:{price}"),
            InlineKeyboardButton("🔍 Details", callback_data=f"store:details:{waifu.get('id')}:{price}")
        ],
        [
            InlineKeyboardButton("🏬 Back", callback_data="store:back"),
            InlineKeyboardButton("🔎 All", callback_data="store:all:0")
        ]
    ]

    image = waifu.get("img_url") or waifu.get("image_url") or waifu.get("image")
    # Try to edit message media if the current message has a photo; otherwise edit text or send new
    try:
        if image:
            await query.edit_message_media(
                media=InputMediaPhoto(media=image, caption=caption, parse_mode="HTML"),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        else:
            await query.edit_message_text(caption, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        # fallback: send new message so user definitely sees it
        await query.message.reply_text(caption, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))


async def all_waifus_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Paginated compact list view of all waifus (5 per page)."""
    query = update.callback_query
    await query.answer()
    try:
        _, action, page_str = query.data.split(":", 2)
        page = int(page_str)
    except Exception:
        page = 0

    per_page = 5
    cursor = collection.find({})
    try:
        waifus = await cursor.to_list(length=1000)
    except Exception:
        waifus = list(cursor)

    if not waifus:
        return await query.edit_message_text("No waifus available in the store.")

    total_pages = (len(waifus) + per_page - 1) // per_page
    page %= total_pages
    start = page * per_page
    block = waifus[start:start + per_page]

    text = f"<b>All Waifus — page {page+1}/{total_pages}</b>\n\n"
    for w in block:
        wid = w.get("id", w.get("_id"))
        text += f"• <b>{w.get('name','Unknown')}</b> — {w.get('rarity','?')} — {fmt_price(generate_price_for_rarity(w.get('rarity','')))}\n  ID: <code>{wid}</code>\n"

    buttons = [
        [
            InlineKeyboardButton("⬅️ Prev", callback_data=f"store:all:{(page - 1) % total_pages}"),
            InlineKeyboardButton("➡️ Next", callback_data=f"store:all:{(page + 1) % total_pages}")
        ],
        [InlineKeyboardButton("🏬 Back", callback_data="store:back")]
    ]

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))


async def details_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show extended details for a waifu (bigger info)."""
    query = update.callback_query
    await query.answer()
    try:
        _, action, waifu_id, price_str = query.data.split(":", 3)
        price = int(price_str)
    except Exception:
        return await query.edit_message_text("Invalid request data.")

    waifu = await collection.find_one({"id": waifu_id}) or await collection.find_one({"_id": waifu_id})
    if not waifu:
        return await query.edit_message_text("Waifu not found.")

    caption = waifu_caption(waifu, price)
    # add more info if available
    extra = ""
    if waifu.get("description"):
        extra += f"\n\n{waifu['description']}"
    caption = caption + extra

    buttons = [
        [InlineKeyboardButton("💸 Buy", callback_data=f"store:buy:{waifu_id}:{price}")],
        [InlineKeyboardButton("🏬 Back", callback_data="store:back")]
    ]

    image = waifu.get("img_url")
    try:
        if image:
            await query.edit_message_media(
                media=InputMediaPhoto(media=image, caption=caption, parse_mode="HTML"),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        else:
            await query.edit_message_text(caption, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        await query.message.reply_text(caption, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))


async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show confirm/cancel UI for buying."""
    query = update.callback_query
    await query.answer()
    try:
        _, action, waifu_id, price_str = query.data.split(":", 3)
        price = int(price_str)
    except Exception:
        return await query.edit_message_text("Invalid buy data.")

    waifu = await collection.find_one({"id": waifu_id}) or await collection.find_one({"_id": waifu_id})
    if not waifu:
        return await query.edit_message_text("Waifu no longer available.")

    caption = (
        f"Confirm purchase:\n\n"
        f"<b>{waifu.get('name','Unknown')}</b>\n"
        f"{fmt_price(price)}\n\n"
        "Press ✅ to confirm or ❌ to cancel."
    )
    buttons = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"store:confirm:{waifu_id}:{price}"),
            InlineKeyboardButton("❌ Cancel", callback_data="store:back")
        ]
    ]
    # try to edit caption of media message; else send new
    try:
        await query.edit_message_caption(caption, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        await query.message.reply_text(caption, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))


async def confirm_purchase_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Atomically deduct balance and add waifu to user's characters array."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    try:
        _, action, waifu_id, price_str = query.data.split(":", 3)
        price = int(price_str)
    except Exception:
        return await query.edit_message_text("Invalid confirmation data.")

    waifu = await collection.find_one({"id": waifu_id}) or await collection.find_one({"_id": waifu_id})
    if not waifu:
        return await query.edit_message_text("Waifu not found or removed.")

    # Atomic check: user must have at least `price` in "balance" field
    # Using find_one_and_update with filter to ensure balance >= price
    filter_q = {"id": user_id, "balance": {"$gte": price}}
    update_q = {"$inc": {"balance": -price}, "$push": {"characters": waifu}}
    try:
        updated = await user_collection.find_one_and_update(
            filter_q,
            update_q,
            return_document=ReturnDocument.AFTER
        )
    except Exception:
        updated = None

    if not updated:
        # either user not registered or insufficient balance
        tips = (
            "❌ <b>Not enough gold!</b>\n\n"
            "Ways to earn gold:\n"
            "• /roll — gamble and win (risky)\n"
            "• /claim — daily reward\n"
            "• Play mini-games the bot provides\n"
            "• Climb /Tophunters leaderboard\n\n"
            "Try again when you have enough gold."
        )
        return await query.edit_message_text(tips, parse_mode="HTML")

    # success
    await query.edit_message_text(
        f"✅ Purchase complete! You bought <b>{waifu.get('name','Unknown')}</b> for {fmt_price(price)}",
        parse_mode="HTML"
    )


async def mywaifus_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List user's owned waifus + optionally show first image."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({"id": user_id})
    chars = user.get("characters") if user else None
    if not chars:
        return await update.message.reply_text("You don't own any waifus yet. Visit /store to buy one!")

    text = "<b>Your Waifus</b>\n\n"
    for i, c in enumerate(chars, 1):
        name = c.get("name", "Unknown")
        rarity = c.get("rarity", "Unknown")
        wid = c.get("id", c.get("_id"))
        text += f"{i}. <b>{name}</b> — {rarity} — ID: <code>{wid}</code>\n"
    # show first waifu image if available
    first_img = chars[0].get("img_url")
    if first_img:
        await update.message.reply_photo(photo=first_img, caption=text, parse_mode="HTML")
    else:
        await update.message.reply_text(text, parse_mode="HTML")


async def tips_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show earning tips for users low on gold."""
    query = update.callback_query
    await query.answer()
    text = (
        "<b>How to earn Gold</b>\n\n"
        "• /claim — claim your daily reward.\n"
        "• /roll <amount> ODD/EVEN — gamble using dice (risky but rewarding).\n"
        "• Compete in leaderboards and community events.\n"
        "• Participate in giveaways or bot events.\n\n"
        "Good luck, hunter!"
    )
    await query.edit_message_text(text, parse_mode="HTML")


async def back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # re-open the store menu
    # We reuse store_command but that expects a Message; pass through the update object
    class Dummy:
        message = query.message
    # call store_command by sending a new message
    await store_command(update, context)


# -----------------------
# Register handlers
# -----------------------
application.add_handler(CommandHandler("store", store_command, block=False))
application.add_handler(CommandHandler("mywaifus", mywaifus_command, block=False))

application.add_handler(CallbackQueryHandler(rarity_callback, pattern=r"^store:rarity:"))
application.add_handler(CallbackQueryHandler(all_waifus_callback, pattern=r"^store:all:"))
application.add_handler(CallbackQueryHandler(details_callback, pattern=r"^store:details:"))
application.add_handler(CallbackQueryHandler(buy_callback, pattern=r"^store:buy:"))
application.add_handler(CallbackQueryHandler(confirm_purchase_callback, pattern=r"^store:confirm:"))
application.add_handler(CallbackQueryHandler(tips_callback, pattern=r"^store:tips$"))
application.add_handler(CallbackQueryHandler(back_callback, pattern=r"^store:back$"))
application.add_handler(CallbackQueryHandler(lambda u, c: None, pattern=r"^store:my:"))  # placeholder if needed

# End of store module