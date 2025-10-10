import random
import datetime
from pymongo import MongoClient
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
from shivu import application
from shivu.modules.database.balance import get_balance, update_balance

# Connect to MongoDB
mongo_url = "mongodb+srv://tiwarireeta004:peqxLEd36RAg7ors@cluster0.furypd3.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(mongo_url)
db = client["waifu_shop"]
collection = db["waifus"]

# --- Rarity Price Mapping (Base values) ---
RARITY_PRICES = {
    "🟢 Common": (200_000, 500_000),
    "🔵 Medium": (600_000, 1_000_000),
    "🟠 Rare": (1_000_000, 3_000_000),
    "🟡 Legendary": (5_000_000, 10_000_000),
    "💮 Exclusive": (15_000_000, 30_000_000),
    "🪽 Celestial": (50_000_000, 100_000_000),
    "🥴 Special": (150_000_000, 250_000_000),
    "💎 Premium": (500_000_000, 1_000_000_000),
    "🔮 Limited": (1_000_000_000, 2_000_000_000),
    "❄️ Winter": (5_000_000, 15_000_000),
    "🎃 Halloween": (10_000_000, 25_000_000),
}

# --- Auto Seasonal Rarity Activation ---
def get_active_rarity():
    month = datetime.datetime.now().month
    # Winter: Dec-Feb
    if month in [12, 1, 2]:
        return "❄️ Winter"
    # Halloween: Oct
    elif month == 10:
        return "🎃 Halloween"
    return None


# --- Helper Functions ---
def format_price(price: int):
    return f"💰 <b>Price:</b> Ŧ{price:,} Gold"

def build_caption(waifu, price):
    name = waifu.get("name", "Unknown")
    anime = waifu.get("anime", "Unknown")
    rarity = waifu.get("rarity", "Unknown")
    wid = waifu.get("id", waifu.get("_id", "N/A"))
    event = waifu.get("event", "")
    caption = (
        f"<b>{name}</b>\n"
        f"🎌 <b>Anime:</b> {anime}\n"
        f"💠 <b>Rarity:</b> {rarity}\n"
        f"{f'🎉 <b>Event:</b> {event}\\n' if event else ''}"
        f"🆔 <b>ID:</b> <code>{wid}</code>\n"
        f"{format_price(price)}\n\n"
        "Use buttons below to navigate or buy this waifu."
    )
    return caption


# --- Command: /store ---
async def store(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = {"rarity": {"$exists": True}}
    waifus = list(collection.find(query))
    if not waifus:
        await update.message.reply_text("❌ No waifus available in the store.")
        return

    # Pick a random rarity or seasonal event
    active_event = get_active_rarity()
    if active_event:
        waifus = [w for w in waifus if w.get("rarity") == active_event] or waifus

    context.user_data["waifus"] = waifus
    context.user_data["index"] = 0

    await show_waifu(update, context)


async def show_waifu(update, context):
    index = context.user_data.get("index", 0)
    waifus = context.user_data.get("waifus", [])
    if not waifus:
        return

    waifu = waifus[index]
    rarity = waifu.get("rarity", "Unknown")
    price = random.randint(*RARITY_PRICES.get(rarity, (100000, 200000)))

    caption = build_caption(waifu, price)
    image = waifu.get("image_url", "")

    keyboard = [
        [
            InlineKeyboardButton("⬅️ Back", callback_data="prev_waifu"),
            InlineKeyboardButton("➡️ Next", callback_data="next_waifu"),
        ],
        [
            InlineKeyboardButton("💰 Buy", callback_data=f"buy_{waifu['_id']}_{price}"),
        ],
        [
            InlineKeyboardButton("🎯 Filter by Rarity", callback_data="filter_rarity"),
        ],
    ]

    if update.message:
        await update.message.reply_photo(photo=image, caption=caption, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        query = update.callback_query
        await query.edit_message_media(
            InputMediaPhoto(media=image, caption=caption, parse_mode="HTML"),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


# --- Navigation Buttons ---
async def callback_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    waifus = context.user_data.get("waifus", [])
    index = context.user_data.get("index", 0)

    if data == "next_waifu":
        context.user_data["index"] = (index + 1) % len(waifus)
        await show_waifu(update, context)
    elif data == "prev_waifu":
        context.user_data["index"] = (index - 1) % len(waifus)
        await show_waifu(update, context)
    elif data == "filter_rarity":
        buttons = [
            [InlineKeyboardButton(r, callback_data=f"rarity_{r}")]
            for r in RARITY_PRICES.keys()
        ]
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("rarity_"):
        rarity = data.split("rarity_")[1]
        waifus = list(collection.find({"rarity": rarity}))
        if not waifus:
            await query.edit_message_caption(f"No waifus found for {rarity}")
            return
        context.user_data["waifus"] = waifus
        context.user_data["index"] = 0
        await show_waifu(update, context)
    elif data.startswith("buy_"):
        _, wid, price = data.split("_")
        price = int(price)
        user_id = update.effective_user.id

        balance = await get_balance(user_id)
        if balance < price:
            await query.edit_message_caption("❌ Not enough gold!")
            return

        await update_balance(user_id, -price)
        waifu = collection.find_one({"_id": wid})
        if not waifu:
            await query.edit_message_caption("❌ Waifu not found.")
            return

        await query.edit_message_caption(f"✅ Purchased {waifu['name']} for Ŧ{price:,} gold!")


# Register Handlers
application.add_handler(CommandHandler("store", store))
application.add_handler(CallbackQueryHandler(callback_buttons))