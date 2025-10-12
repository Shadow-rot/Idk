import random
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMediaPhoto
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler

from shivu import application, db, user_collection, CHARA_CHANNEL_ID, SUPPORT_CHAT

collection = db['anime_characters_lol']
shop_collection = db['shop']
characters_collection = collection

sudo_users = ["8297659126", "8420981179", "5147822244"]

ITEMS_PER_PAGE = 1

async def is_sudo_user(user_id: int) -> bool:
    return str(user_id) in sudo_users

async def addshop(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    if not await is_sudo_user(user_id):
        await update.message.reply_text("⛔️ You don't have permission to use this command.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Usage: /addshop <character_id> <price> [limit]")
        return

    try:
        char_id = context.args[0]
        price = int(context.args[1])
        limit = None
        if len(context.args) >= 3:
            limit_arg = context.args[2].lower()
            if limit_arg in ["0", "unlimited", "infinity"]:
                limit = None
            else:
                limit = int(context.args[2])
                if limit <= 0:
                    limit = None

        if price <= 0:
            await update.message.reply_text("⚠️ Price must be greater than 0.")
            return

        character = await characters_collection.find_one({"id": char_id})
        if not character:
            await update.message.reply_text(f"⚠️ Character with ID {char_id} not found in database.")
            return

        existing = await shop_collection.find_one({"id": char_id})
        if existing:
            await update.message.reply_text(f"⚠️ Character <b>{character['name']}</b> is already in the shop.", parse_mode="HTML")
            return

        shop_item = {
            "id": char_id,
            "price": price,
            "added_by": user_id,
            "added_at": datetime.utcnow(),
            "limit": limit,  # None or int
            "sold": 0
        }

        await shop_collection.insert_one(shop_item)
        limit_text = "Unlimited" if limit is None else str(limit)
        await update.message.reply_text(
            f"✨ Successfully added <b>{character['name']}</b> to shop!\n"
            f"💎 Price: {price} Gold\n"
            f"🔢 Limit: {limit_text}",
            parse_mode="HTML"
        )

    except ValueError:
        await update.message.reply_text("⚠️ Invalid price or limit. Please provide valid numbers.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

async def rmshop(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    if not await is_sudo_user(user_id):
        await update.message.reply_text("⛔️ You don't have permission to use this command.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("⚠️ Usage: /rmshop <character_id>")
        return

    try:
        char_id = context.args[0]

        shop_item = await shop_collection.find_one({"id": char_id})
        if not shop_item:
            await update.message.reply_text(f"⚠️ Character with ID {char_id} is not in the shop.")
            return

        character = await characters_collection.find_one({"id": char_id})
        char_name = character['name'] if character else char_id

        await shop_collection.delete_one({"id": char_id})
        await update.message.reply_text(f"✨ Successfully removed <b>{char_name}</b> from shop!", parse_mode="HTML")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

def build_caption(waifu: dict, shop_item: dict, page: int, total: int, user_data=None) -> tuple:
    wid = waifu.get("id", waifu.get("_id"))
    name = waifu.get("name", "Unknown")
    anime = waifu.get("anime", "Unknown")
    rarity = waifu.get("rarity", "Unknown")
    price = shop_item.get("price", 0)
    img_url = waifu.get("img_url", "")
    limit = shop_item.get("limit", None)
    sold = shop_item.get("sold", 0)
    limit_text = "Unlimited" if limit is None else f"{sold}/{limit}"

    sold_out = False
    already_bought = False

    # Show "sold out" if limit reached or user already owns
    if limit is not None and sold >= limit:
        sold_out = True

    if user_data:
        user_chars = user_data.get("characters", [])
        # Check if character already bought (by id)
        if any((c.get("id") == wid or c.get("_id") == wid) for c in user_chars):
            already_bought = True

    if sold_out:
        sold_out_text = "\n⚠️ <b>SOLD OUT!</b>"
    elif already_bought:
        sold_out_text = "\n⚠️ <b>ALREADY BOUGHT!</b>"
    else:
        sold_out_text = ""

    caption = (
        f"╭─━━━━━━━━━━━━━━━─╮\n"
        f"│  🏪 𝗖𝗛𝗔𝗥𝗔𝗖𝗧𝗘𝗥 𝗦𝗛𝗢𝗣  │\n"
        f"╰─━━━━━━━━━━━━━━━─╯\n\n"
        f"✨ <b>{name}</b>\n\n"
        f"🎭 𝗔𝗻𝗶𝗺𝗲: <code>{anime}</code>\n"
        f"💫 𝗥𝗮𝗿𝗶𝘁𝘆: {rarity}\n"
        f"🔖 𝗜𝗗: <code>{wid}</code>\n"
        f"💎 𝗣𝗿𝗶𝗰𝗲: <b>{price}</b> Gold\n"
        f"🔢 𝗟𝗶𝗺𝗶𝘁: {limit_text}\n\n"
        f"📖 𝗣𝗮𝗴𝗲: {page}/{total}\n"
        f"{sold_out_text}\n\n"
        f"Tap <b>Buy</b> to purchase this character!"
    )
    # Hide buy button if sold out or already bought
    return caption, img_url, sold_out or already_bought

async def store(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    shop_items = await shop_collection.find({}).to_list(length=None)

    if not shop_items:
        await update.message.reply_text("🏪 The shop is currently empty. Check back later!")
        return

    page = 0
    total_pages = len(shop_items)
    context.user_data['shop_items'] = [item['id'] for item in shop_items]
    context.user_data['shop_page'] = page

    char_id = shop_items[page]['id']
    character = await characters_collection.find_one({"id": char_id})
    user_data = await user_collection.find_one({"id": user_id})
    caption, img_url, sold_out = build_caption(character, shop_items[page], page + 1, total_pages, user_data)

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

    if not sold_out:
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

    context.user_data['shop_message_id'] = msg.message_id
    context.user_data['shop_chat_id'] = update.effective_chat.id

async def shop_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # Helper for rendering shop page
    async def render_shop_page(page):
        shop_items_ids = context.user_data.get('shop_items', [])
        if not shop_items_ids or page >= len(shop_items_ids):
            await query.answer("⚠️ Invalid page.", show_alert=True)
            return

        context.user_data['shop_page'] = page
        char_id = shop_items_ids[page]

        character = await characters_collection.find_one({"id": char_id})
        shop_item = await shop_collection.find_one({"id": char_id})
        user_data = await user_collection.find_one({"id": user_id})

        if not character or not shop_item:
            await query.answer("⚠️ Character not found.", show_alert=True)
            return

        caption, img_url, sold_out = build_caption(character, shop_item, page + 1, len(shop_items_ids), user_data)

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

        if not sold_out:
            buttons.append([InlineKeyboardButton("💳 Buy", callback_data=f"shop_buy_{char_id}")])
        if nav_buttons:
            buttons.append(nav_buttons)

        markup = InlineKeyboardMarkup(buttons)

        try:
            await query.edit_message_media(
                media=InputMediaPhoto(media=img_url, caption=caption, parse_mode="HTML"),
                reply_markup=markup
            )
        except Exception as e:
            try:
                await query.edit_message_caption(
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=markup
                )
            except:
                pass

    if data.startswith("shop_page_"):
        page = int(data.split("_")[2])
        await render_shop_page(page)

    elif data == "shop_refresh":
        shop_items = await shop_collection.find({}).to_list(length=None)

        if not shop_items:
            await query.edit_message_caption("🏪 The shop is currently empty. Check back later!")
            return

        page = 0
        context.user_data['shop_items'] = [item['id'] for item in shop_items]
        context.user_data['shop_page'] = page

        char_id = shop_items[page]['id']
        character = await characters_collection.find_one({"id": char_id})
        shop_item = shop_items[page]
        user_data = await user_collection.find_one({"id": user_id})

        caption, img_url, sold_out = build_caption(character, shop_item, page + 1, len(shop_items), user_data)

        buttons = []
        nav_buttons = []

        if len(shop_items) > 1:
            nav_buttons.append(InlineKeyboardButton("🔄 Refresh", callback_data="shop_refresh"))
            nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"shop_page_{page+1}"))
        else:
            nav_buttons.append(InlineKeyboardButton("🔄 Refresh", callback_data="shop_refresh"))

        if not sold_out:
            buttons.append([InlineKeyboardButton("💳 Buy", callback_data=f"shop_buy_{char_id}")])
        if nav_buttons:
            buttons.append(nav_buttons)

        markup = InlineKeyboardMarkup(buttons)

        try:
            await query.edit_message_media(
                media=InputMediaPhoto(media=img_url, caption=caption, parse_mode="HTML"),
                reply_markup=markup
            )
        except:
            await query.edit_message_caption(
                caption=caption,
                parse_mode="HTML",
                reply_markup=markup
            )
        await query.answer("🔄 Shop refreshed!", show_alert=False)

    elif data.startswith("shop_buy_"):
        char_id = data.split("_", 2)[2]

        shop_item = await shop_collection.find_one({"id": char_id})
        character = await characters_collection.find_one({"id": char_id})
        user_data = await user_collection.find_one({"id": user_id})

        limit = shop_item.get("limit", None)
        sold = shop_item.get("sold", 0)
        user_chars = user_data.get("characters", []) if user_data else []
        already_bought = any((c.get("id") == char_id or c.get("_id") == char_id) for c in user_chars)

        if (limit is not None and sold >= limit) or already_bought:
            await query.answer("⚠️ Sold out or already owned!", show_alert=True)
            await query.edit_message_caption(
                caption="⚠️ <b>SOLD OUT or ALREADY OWNED!</b>",
                parse_mode="HTML"
            )
            return

        price = shop_item.get("price", 0)
        buttons = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"shop_confirm_{char_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data="shop_cancel")
            ]
        ]
        markup = InlineKeyboardMarkup(buttons)

        await query.edit_message_caption(
            caption=f"╭─━━━━━━━━━━━━━━━─╮\n"
                    f"│  💳 CONFIRM PURCHASE  │\n"
                    f"╰─━━━━━━━━━━━━━━━─╯\n\n"
                    f"✨ <b>{character['name']}</b>\n"
                    f"💎 Price: <b>{price}</b> Gold\n\n"
                    f"Are you sure you want to buy this character?",
            parse_mode="HTML",
            reply_markup=markup
        )

    elif data.startswith("shop_confirm_"):
        char_id = data.split("_", 2)[2]

        shop_item = await shop_collection.find_one({"id": char_id})
        character = await characters_collection.find_one({"id": char_id})
        user_data = await user_collection.find_one({"id": user_id})

        limit = shop_item.get("limit", None)
        sold = shop_item.get("sold", 0)
        user_chars = user_data.get("characters", []) if user_data else []
        already_bought = any((c.get("id") == char_id or c.get("_id") == char_id) for c in user_chars)

        if (limit is not None and sold >= limit) or already_bought:
            await query.edit_message_caption(
                caption=f"╭─━━━━━━━━━━━━━━━━━─╮\n"
                        f"│  ⚠️ SOLD OUT │\n"
                        f"╰─━━━━━━━━━━━━━━━━━─╯\n\n"
                        f"This character cannot be bought again.",
                parse_mode="HTML"
            )
            await query.answer("⚠️ Sold out or already owned!", show_alert=True)
            return

        price = shop_item.get("price", 0)
        balance = user_data.get("balance", 0) if user_data else 0

        if balance < price:
            await query.answer("⚠️ Not enough Gold!", show_alert=True)
            await query.edit_message_caption(
                caption=f"╭─━━━━━━━━━━━━━━━━━─╮\n"
                        f"│  ⚠️ INSUFFICIENT BALANCE │\n"
                        f"╰─━━━━━━━━━━━━━━━━━─╯\n\n"
                        f"You need <b>{price}</b> Gold but only have <b>{balance}</b> Gold.\n"
                        f"Use /bal to check your balance.",
                parse_mode="HTML"
            )
            return

        await user_collection.update_one(
            {"id": user_id},
            {
                "$inc": {"balance": -price},
                "$push": {"characters": character}
            },
            upsert=True
        )
        await shop_collection.update_one(
            {"id": char_id},
            {"$inc": {"sold": 1}}
        )

        await query.edit_message_caption(
            caption=f"╭─━━━━━━━━━━━━━━━━─╮\n"
                    f"│  ✨ PURCHASE SUCCESS! │\n"
                    f"╰─━━━━━━━━━━━━━━━━─╯\n\n"
                    f"You bought <b>{character['name']}</b> for <b>{price}</b> Gold!\n"
                    f"The character has been added to your harem.\n\n"
                    f"💰 Remaining Balance: <b>{balance - price}</b> Gold",
            parse_mode="HTML"
        )
        await query.answer("✨ Purchase successful!", show_alert=False)

    elif data == "shop_cancel":
        page = context.user_data.get('shop_page', 0)
        shop_items_ids = context.user_data.get('shop_items', [])

        if not shop_items_ids:
            await query.answer("⚠️ Session expired. Please use /store again.", show_alert=True)
            return

        await render_shop_page(page)
        await query.answer("Purchase cancelled.", show_alert=False)

application.add_handler(CommandHandler("store", store, block=False))
application.add_handler(CommandHandler("addshop", addshop, block=False))
application.add_handler(CommandHandler("rmshop", rmshop, block=False))
application.add_handler(CallbackQueryHandler(shop_callback, pattern=r"^shop_", block=False))