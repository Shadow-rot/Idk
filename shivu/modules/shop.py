import random
from pymongo import MongoClient
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
)
from telegram.ext import (
    CommandHandler, CallbackQueryHandler, ContextTypes
)
from shivu import application, user_collection

# ===================== DB CONNECTION ===================== #
MONGO_URI = "mongodb+srv://Epic2:w85NP8dEHmQxA5s7@cluster0.tttvsf9.mongodb.net/?retryWrites=true&w=majority"
DB_NAME = "GRABBING_YOUR_WAIFU"
COLLECTION_NAME = "users"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
waifu_collection = db["waifus"]

# ===================== RARITY & EVENT MAP ===================== #
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

# Random price generator based on rarity tier
def random_price(rarity: str) -> int:
    base = {
        "🟢 Common": random.randint(20000, 80000),
        "🟣 Rare": random.randint(100000, 300000),
        "🟡 Legendary": random.randint(500000, 1500000),
        "💮 Special Edition": random.randint(2000000, 5000000),
        "🔮 Premium Edition": random.randint(8000000, 20000000),
        "🎗️ Supreme": random.randint(30000000, 70000000),
    }
    return base.get(rarity, random.randint(10000, 50000))


# ===================== MAIN COMMAND ===================== #
async def store(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [
            InlineKeyboardButton("🟢 Common", callback_data="store_rarity|🟢 Common|0"),
            InlineKeyboardButton("🟣 Rare", callback_data="store_rarity|🟣 Rare|0"),
        ],
        [
            InlineKeyboardButton("🟡 Legendary", callback_data="store_rarity|🟡 Legendary|0"),
            InlineKeyboardButton("💮 Special Edition", callback_data="store_rarity|💮 Special Edition|0"),
        ],
        [
            InlineKeyboardButton("🔮 Premium Edition", callback_data="store_rarity|🔮 Premium Edition|0"),
            InlineKeyboardButton("🎗️ Supreme", callback_data="store_rarity|🎗️ Supreme|0"),
        ],
    ]

    text = (
        "🏪 <b>Welcome to the Waifu Store!</b>\n\n"
        "Select a rarity to browse beautiful waifus 💫\n\n"
        "💰 Earn Gold Coins by:\n"
        "• Playing /roll 🎲\n"
        "• Claiming /claim daily reward 💎\n"
        "• Competing in /Tophunters leaderboard 🏆\n\n"
        "Use your balance wisely, hunter!"
    )

    await update.message.reply_text(
        text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons)
    )


# ===================== SHOW WAIFUS BY RARITY ===================== #
async def rarity_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        _, rarity, index_str = query.data.split("|")
        index = int(index_str)
    except Exception:
        return await query.edit_message_text("❌ Invalid data.")

    waifus = list(waifu_collection.find({"rarity": rarity}))
    if not waifus:
        return await query.edit_message_text(f"No waifus found for {rarity} rarity.")

    waifu = waifus[index % len(waifus)]
    price = random_price(rarity)

    caption = (
        f"<b>{waifu.get('name', 'Unknown')}</b>\n"
        f"🎌 <b>Anime:</b> {waifu.get('anime_name', 'Unknown')}\n"
        f"💠 <b>Rarity:</b> {rarity}\n"
        f"🎉 <b>Event:</b> {waifu.get('event', 'None')}\n"
        f"💰 <b>Price:</b> Ŧ{price:,}\n"
        f"🆔 <b>ID:</b> <code>{waifu.get('id')}</code>"
    )

    buttons = [
        [
            InlineKeyboardButton("⬅️ Prev", callback_data=f"store_rarity|{rarity}|{(index - 1) % len(waifus)}"),
            InlineKeyboardButton("➡️ Next", callback_data=f"store_rarity|{rarity}|{(index + 1) % len(waifus)}"),
        ],
        [InlineKeyboardButton("💸 Buy", callback_data=f"buy|{waifu['id']}|{price}")],
        [InlineKeyboardButton("🏬 Back", callback_data="store_back")]
    ]

    image = waifu.get("image_url", "")
    if query.message.photo:
        await query.edit_message_media(
            InputMediaPhoto(image, caption=caption, parse_mode="HTML"),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        await query.edit_message_text(
            caption, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons)
        )


# ===================== BUY & CONFIRM ===================== #
async def buy_waifu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        _, waifu_id, price_str = query.data.split("|")
        price = int(price_str)
    except Exception:
        return await query.edit_message_text("❌ Invalid purchase data.")

    waifu = waifu_collection.find_one({"id": waifu_id})
    if not waifu:
        return await query.edit_message_text("Waifu not found.")

    buttons = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_buy|{waifu_id}|{price}"),
            InlineKeyboardButton("❌ Cancel", callback_data="store_back")
        ]
    ]
    await query.edit_message_caption(
        caption=(
            f"Are you sure you want to buy <b>{waifu['name']}</b> "
            f"for Ŧ{price:,} Gold Coins?"
        ),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def confirm_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        _, waifu_id, price_str = query.data.split("|")
        price = int(price_str)
    except Exception:
        return await query.edit_message_text("Invalid confirmation data.")

    waifu = waifu_collection.find_one({"id": waifu_id})
    if not waifu:
        return await query.edit_message_text("Waifu not found.")

    user = await user_collection.find_one({"id": user_id})
    if not user:
        return await query.edit_message_text("You are not registered yet. Earn coins first!")

    balance = user.get("balance", 0)
    if balance < price:
        tips = (
            "❌ <b>Not enough Gold Coins!</b>\n\n"
            "You can earn more by:\n"
            "🎲 Using /roll to gamble coins\n"
            "💎 Claiming daily with /claim\n"
            "🏦 Checking your funds with /bal\n"
            "🏆 Competing in /Tophunters leaderboard!"
        )
        return await query.edit_message_caption(tips, parse_mode="HTML")

    await user_collection.update_one(
        {"id": user_id},
        {"$inc": {"balance": -price}, "$push": {"characters": waifu}}
    )

    await query.edit_message_caption(
        f"✅ You successfully purchased <b>{waifu['name']}</b> for Ŧ{price:,} Gold Coins!",
        parse_mode="HTML",
        reply_markup=None
    )


# ===================== BACK BUTTON ===================== #
async def back_to_store(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await store(update, context)


# ===================== HANDLERS ===================== #
application.add_handler(CommandHandler("store", store, block=False))
application.add_handler(CallbackQueryHandler(rarity_view, pattern=r"^store_rarity\|"))
application.add_handler(CallbackQueryHandler(buy_waifu, pattern=r"^buy\|"))
application.add_handler(CallbackQueryHandler(confirm_buy, pattern=r"^confirm_buy\|"))
application.add_handler(CallbackQueryHandler(back_to_store, pattern=r"^store_back$"))