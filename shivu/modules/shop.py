import asyncio
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
)
from telegram.ext import (
    CommandHandler, CallbackQueryHandler, ContextTypes
)
from shivu import collection, user_collection, application

# === RARITY COINS ===
RARITY_VALUES = {
    "🟢 Common": 2000000,
    "🔵 Medium": 4000000,
    "🟠 Rare": 8000000,
    "🟡 Legendary": 15000000,
    "🪽 celestial": 20000000,
    "💮 Exclusive": 300000000,
    "🥴 Spacial": 400000000000,
    "💎 Premium": 2000000000000000000,
    "🔮 Limited": 6000000000000000000,
}


# === /store command ===
async def store(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [
            InlineKeyboardButton("🟢 Common", callback_data="shop|🟢 Common|0"),
            InlineKeyboardButton("🔵 Medium", callback_data="shop|🔵 Medium|0"),
        ],
        [
            InlineKeyboardButton("🟠 Rare", callback_data="shop|🟠 Rare|0"),
            InlineKeyboardButton("🟡 Legendary", callback_data="shop|🟡 Legendary|0"),
        ],
        [
            InlineKeyboardButton("🪽 Celestial", callback_data="shop|🪽 celestial|0"),
            InlineKeyboardButton("💮 Exclusive", callback_data="shop|💮 Exclusive|0"),
        ],
        [
            InlineKeyboardButton("🥴 Spacial", callback_data="shop|🥴 Spacial|0"),
        ],
        [
            InlineKeyboardButton("💎 Premium", callback_data="shop|💎 Premium|0"),
            InlineKeyboardButton("🔮 Limited", callback_data="shop|🔮 Limited|0"),
        ],
    ]
    await update.message.reply_text(
        "🛍️ <b>Waifu Store</b>\n\nChoose a rarity to view available waifus.",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="HTML"
    )


# === Handle Rarity Filter ===
async def rarity_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        _, rarity, index_str = query.data.split("|")
        index = int(index_str)
    except Exception:
        return await query.edit_message_text("Invalid data.")

    # Get waifus of selected rarity
    waifus = await collection.find({"rarity": rarity}).to_list(length=100)
    if not waifus:
        return await query.edit_message_text(f"No waifus found for {rarity} rarity.")

    if index >= len(waifus):
        index = 0

    waifu = waifus[index]
    price = RARITY_VALUES.get(rarity, 0)
    caption = (
        f"<b>{waifu['name']}</b>\n"
        f"🎌 <b>Anime:</b> {waifu.get('anime_name', 'Unknown')}\n"
        f"💠 <b>Rarity:</b> {rarity}\n"
        f"💰 <b>Price:</b> Ŧ{price:,}\n"
        f"🆔 <b>ID:</b> <code>{waifu['id']}</code>"
    )

    next_index = (index + 1) % len(waifus)
    buttons = [
        [
            InlineKeyboardButton("⬅️ Prev", callback_data=f"shop|{rarity}|{(index - 1) % len(waifus)}"),
            InlineKeyboardButton("➡️ Next", callback_data=f"shop|{rarity}|{next_index}")
        ],
        [InlineKeyboardButton("💸 Buy", callback_data=f"buy|{waifu['id']}|{price}")],
        [InlineKeyboardButton("🏬 Back to Rarities", callback_data="back_to_store")]
    ]

    if query.message.photo:
        await query.edit_message_media(
            media=InputMediaPhoto(waifu.get("image_url", ""), caption=caption, parse_mode="HTML"),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        await query.edit_message_text(caption, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


# === Confirm Purchase ===
async def confirm_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        _, char_id, price_str = query.data.split("|")
        price = int(price_str)
    except Exception:
        return await query.edit_message_text("Invalid purchase data.")

    waifu = await collection.find_one({"id": char_id})
    if not waifu:
        return await query.edit_message_text("Waifu not found.")

    buttons = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_buy|{char_id}|{price}"),
            InlineKeyboardButton("❌ Cancel", callback_data="back_to_store")
        ]
    ]
    caption = (
        f"Are you sure you want to buy <b>{waifu['name']}</b> "
        f"for Ŧ{price:,} coins?"
    )
    await query.edit_message_caption(caption, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


# === Handle Confirmation ===
async def handle_confirm_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        _, char_id, price_str = query.data.split("|")
        price = int(price_str)
    except Exception:
        return await query.edit_message_text("Invalid purchase confirmation.")

    waifu = await collection.find_one({"id": char_id})
    if not waifu:
        return await query.edit_message_text("Waifu not found.")

    user = await user_collection.find_one({"id": user_id})
    if not user or user.get("balance", 0) < price:
        return await query.edit_message_text("❌ You don't have enough coins!")

    # Deduct balance and add waifu
    await user_collection.update_one(
        {"id": user_id},
        {"$inc": {"balance": -price}, "$push": {"characters": waifu}}
    )

    await query.edit_message_caption(
        f"✅ Successfully purchased <b>{waifu['name']}</b> for Ŧ{price:,} coins!",
        parse_mode="HTML",
        reply_markup=None
    )


# === Go Back to Rarity Menu ===
async def back_to_store(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await store(update, context)


# === Register Handlers ===
application.add_handler(CommandHandler("store", store, block=False))
application.add_handler(CallbackQueryHandler(rarity_view, pattern=r"^shop\|"))
application.add_handler(CallbackQueryHandler(confirm_buy, pattern=r"^buy\|"))
application.add_handler(CallbackQueryHandler(handle_confirm_buy, pattern=r"^confirm_buy\|"))
application.add_handler(CallbackQueryHandler(back_to_store, pattern=r"^back_to_store$"))