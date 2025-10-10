import random
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler

from shivu import application, db, user_collection

# Define rarity multipliers for price generation
RARITY_MULTIPLIER = {
    "🟢 Common": 1,
    "🟣 Rare": 2,
    "🟡 Legendary": 5,
    "💮 Special Edition": 7,
    "🔮 Premium Edition": 10,
    "🎗️ Supreme": 15
}

# Event mapping
EVENT_MAPPING = {
    1: {"name": "Summer", "sign": "🏖"},
    2: {"name": "Kimono", "sign": "👘"},
    3: {"name": "Winter", "sign": "☃️"},
    4: {"name": "Valentine", "sign": "💞"},
    5: {"name": "School", "sign": "🎒"},
    6: {"name": "Halloween", "sign": "🎃"},
    7: {"name": "Game", "sign": "🎮"},
    8: {"name": "Tuxedo", "sign": "🎩"},
    9: {"name": "Duo", "sign": "👥"},
    10: {"name": "Made", "sign": "🧹"},
    11: {"name": "Monsoon", "sign": "☔"},
    12: {"name": "Bunny", "sign": "🐰"},
    13: {"name": "Group", "sign": "🤝🏻"},
    14: {"name": "Saree", "sign": "🥻"},
    15: {"name": "Christmas", "sign": "🎄"},
    16: {"name": "Lord", "sign": "👑"},
    17: None  # no event
}

def generate_price(rarity: str) -> int:
    """Generate random price based on rarity"""
    base = 500
    multiplier = RARITY_MULTIPLIER.get(rarity, 1)
    return random.randint(base * multiplier, base * multiplier * 2)

def build_caption(waifu: dict, price: int) -> str:
    """Create HTML caption for the waifu"""
    wid = waifu.get("id", waifu.get("_id"))
    name = waifu.get("name", "Unknown")
    anime = waifu.get("anime", "Unknown")
    rarity = waifu.get("rarity", "Unknown")
    event = waifu.get("event")
    
    event_text = ""
    if isinstance(event, dict) and event.get("name"):
        event_text = f"{event.get('sign', '')} {event.get('name')}"
    
    caption = (
    f"<b>{name}</b>\n"
    f"🎌 <b>Anime:</b> {anime}\n"
    f"💠 <b>Rarity:</b> {rarity}\n"
    + (f"🎉 <b>Event:</b> {event_text}\n" if event_text else "")
    + f"🆔 <b>ID:</b> <code>{wid}</code>\n"
    f"💰 <b>Price:</b> {price} Gold\n\n"
    "Tap <b>Buy → Confirm</b> to purchase. Use /bal to check your balance."
)
    return caption

async def store(update: Update, context: CallbackContext):
    """Show waifus in the store"""
    user_id = update.effective_user.id
    characters = db.characters

    # Determine current month for seasonal events
    month = datetime.utcnow().month
    current_event = None
    if month == 12:
        current_event = 15  # Christmas
    elif month == 10:
        current_event = 6   # Halloween
    elif month == 1 or month == 2:
        current_event = 3   # Winter
    # You can expand with other months/events

    # Query waifus; prioritize seasonal event waifus
    query = {}
    if current_event:
        query["event.name"] = EVENT_MAPPING[current_event]["name"]

    waifus = await characters.find(query).to_list(length=20)
    if not waifus:
        waifus = await characters.find({}).to_list(length=20)  # fallback if no seasonal waifus

    for waifu in waifus:
        price = waifu.get("price") or generate_price(waifu.get("rarity"))
        caption = build_caption(waifu, price)
        buttons = [
            [
                InlineKeyboardButton("💳 Buy", callback_data=f"buy_{waifu['id']}"),
                InlineKeyboardButton("ℹ Info", callback_data=f"info_{waifu['id']}")
            ]
        ]
        markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_photo(
            photo=waifu["img_url"],
            caption=caption,
            parse_mode="HTML",
            reply_markup=markup
        )

async def buy_callback(update: Update, context: CallbackContext):
    """Handle Buy button"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("buy_"):
        waifu_id = data.split("_")[1]
        waifu = await db.characters.find_one({"id": waifu_id})
        if not waifu:
            await query.edit_message_caption("❌ Waifu not found.")
            return

        price = waifu.get("price") or generate_price(waifu.get("rarity"))
        user_data = await user_collection.find_one({"id": user_id})
        balance = user_data.get("balance", 0)

        if balance < price:
            await query.edit_message_caption("❌ You do not have enough Gold. Use /roll or /claim to earn more.")
            return

        # Deduct gold and give waifu
        await user_collection.update_one(
            {"id": user_id},
            {"$inc": {"balance": -price}, "$push": {"characters": waifu}},
            upsert=True
        )
        await query.edit_message_caption(f"✅ You successfully bought {waifu['name']} for {price} Gold!")

# Handlers
application.add_handler(CommandHandler("store", store, block=False))
application.add_handler(CallbackQueryHandler(buy_callback, pattern=r"^buy_"))