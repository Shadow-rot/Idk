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
        await update.message.reply_text("⛔️ 𝖸𝗈𝗎 𝖽𝗈𝗇'𝗍 𝗁𝖺𝗏𝖾 𝗉𝖾𝗋𝗆𝗂𝗌𝗌𝗂𝗈𝗇 𝗍𝗈 𝗎𝗌𝖾 𝗍𝗁𝗂𝗌 𝖼𝗈𝗆𝗆𝖺𝗇𝖽.")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ 𝖴𝗌𝖺𝗀𝖾: /addshop <character_id> <price>")
        return
    
    try:
        char_id = context.args[0]
        price = int(context.args[1])
        
        if price <= 0:
            await update.message.reply_text("⚠️ 𝖯𝗋𝗂𝖼𝖾 𝗆𝗎𝗌𝗍 𝖻𝖾 𝗀𝗋𝖾𝖺𝗍𝖾𝗋 𝗍𝗁𝖺𝗇 0.")
            return
        
        character = await characters_collection.find_one({"id": char_id})
        if not character:
            await update.message.reply_text(f"⚠️ 𝖢𝗁𝖺𝗋𝖺𝖼𝗍𝖾𝗋 𝗐𝗂𝗍𝗁 𝖨𝖣 {char_id} 𝗇𝗈𝗍 𝖿𝗈𝗎𝗇𝖽 𝗂𝗇 𝖽𝖺𝗍𝖺𝖻𝖺𝗌𝖾.")
            return
        
        existing = await shop_collection.find_one({"id": char_id})
        if existing:
            await update.message.reply_text(f"⚠️ 𝖢𝗁𝖺𝗋𝖺𝖼𝗍𝖾𝗋 <b>{character['name']}</b> 𝗂𝗌 𝖺𝗅𝗋𝖾𝖺𝖽𝗒 𝗂𝗇 𝗍𝗁𝖾 𝗌𝗁𝗈𝗉.", parse_mode="HTML")
            return
        
        shop_item = {
            "id": char_id,
            "price": price,
            "added_by": user_id,
            "added_at": datetime.utcnow()
        }
        
        await shop_collection.insert_one(shop_item)
        await update.message.reply_text(
            f"✨ 𝖲𝗎𝖼𝖼𝖾𝗌𝗌𝖿𝗎𝗅𝗅𝗒 𝖺𝖽𝖽𝖾𝖽 <b>{character['name']}</b> 𝗍𝗈 𝗌𝗁𝗈𝗉!\n"
            f"💎 𝖯𝗋𝗂𝖼𝖾: {price} 𝖦𝗈𝗅𝖽",
            parse_mode="HTML"
        )
    
    except ValueError:
        await update.message.reply_text("⚠️ 𝖨𝗇𝗏𝖺𝗅𝗂𝖽 𝗉𝗋𝗂𝖼𝖾. 𝖯𝗅𝖾𝖺𝗌𝖾 𝗉𝗋𝗈𝗏𝗂𝖽𝖾 𝖺 𝗏𝖺𝗅𝗂𝖽 𝗇𝗎𝗆𝖻𝖾𝗋.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ 𝖤𝗋𝗋𝗈𝗋: {str(e)}")

async def rmshop(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    if not await is_sudo_user(user_id):
        await update.message.reply_text("⛔️ 𝖸𝗈𝗎 𝖽𝗈𝗇'𝗍 𝗁𝖺𝗏𝖾 𝗉𝖾𝗋𝗆𝗂𝗌𝗌𝗂𝗈𝗇 𝗍𝗈 𝗎𝗌𝖾 𝗍𝗁𝗂𝗌 𝖼𝗈𝗆𝗆𝖺𝗇𝖽.")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("⚠️ 𝖴𝗌𝖺𝗀𝖾: /rmshop <character_id>")
        return
    
    try:
        char_id = context.args[0]
        
        shop_item = await shop_collection.find_one({"id": char_id})
        if not shop_item:
            await update.message.reply_text(f"⚠️ 𝖢𝗁𝖺𝗋𝖺𝖼𝗍𝖾𝗋 𝗐𝗂𝗍𝗁 𝖨𝖣 {char_id} 𝗂𝗌 𝗇𝗈𝗍 𝗂𝗇 𝗍𝗁𝖾 𝗌𝗁𝗈𝗉.")
            return
        
        character = await characters_collection.find_one({"id": char_id})
        char_name = character['name'] if character else char_id
        
        await shop_collection.delete_one({"id": char_id})
        await update.message.reply_text(f"✨ 𝖲𝗎𝖼𝖼𝖾𝗌𝗌𝖿𝗎𝗅𝗅𝗒 𝗋𝖾𝗆𝗈𝗏𝖾𝖽 <b>{char_name}</b> 𝖿𝗋𝗈𝗆 𝗌𝗁𝗈𝗉!", parse_mode="HTML")
    
    except Exception as e:
        await update.message.reply_text(f"⚠️ 𝖤𝗋𝗋𝗈𝗋: {str(e)}")

def build_caption(waifu: dict, shop_item: dict, page: int, total: int) -> tuple:
    wid = waifu.get("id", waifu.get("_id"))
    name = waifu.get("name", "Unknown")
    anime = waifu.get("anime", "Unknown")
    rarity = waifu.get("rarity", "Unknown")
    price = shop_item.get("price", 0)
    img_url = waifu.get("img_url", "")

    caption = (
        f"╭─━━━━━━━━━━━━━━━─╮\n"
        f"│  🏪 𝗖𝗛𝗔𝗥𝗔𝗖𝗧𝗘𝗥 𝗦𝗛𝗢𝗣  │\n"
        f"╰─━━━━━━━━━━━━━━━─╯\n\n"
        f"✨ <b>{name}</b>\n\n"
        f"🎭 𝗔𝗻𝗶𝗺𝗲: <code>{anime}</code>\n"
        f"💫 𝗥𝗮𝗿𝗶𝘁𝘆: {rarity}\n"
        f"🔖 𝗜𝗗: <code>{wid}</code>\n"
        f"💎 𝗣𝗿𝗶𝗰𝗲: <b>{price}</b> 𝖦𝗈𝗅𝖽\n\n"
        f"📖 𝗣𝗮𝗴𝗲: {page}/{total}\n\n"
        f"𝖳𝖺𝗉 <b>𝗕𝘂𝘆</b> 𝗍𝗈 𝗉𝗎𝗋𝖼𝗁𝖺𝗌𝖾 𝗍𝗁𝗂𝗌 𝖼𝗁𝖺𝗋𝖺𝖼𝗍𝖾𝗋!"
    )
    return caption, img_url

async def store(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    shop_items = await shop_collection.find({}).to_list(length=None)
    
    if not shop_items:
        await update.message.reply_text("🏪 𝖳𝗁𝖾 𝗌𝗁𝗈𝗉 𝗂𝗌 𝖼𝗎𝗋𝗋𝖾𝗇𝗍𝗅𝗒 𝖾𝗆𝗉𝗍𝗒. 𝖢𝗁𝖾𝖼𝗄 𝖻𝖺𝖼𝗄 𝗅𝖺𝗍𝖾𝗋!")
        return
    
    page = 0
    total_pages = len(shop_items)
    
    context.user_data['shop_items'] = [item['id'] for item in shop_items]
    context.user_data['shop_page'] = page
    
    char_id = shop_items[page]['id']
    character = await characters_collection.find_one({"id": char_id})
    
    if not character:
        await update.message.reply_text("⚠️ 𝖤𝗋𝗋𝗈𝗋 𝗅𝗈𝖺𝖽𝗂𝗇𝗀 𝗌𝗁𝗈𝗉 𝖼𝗁𝖺𝗋𝖺𝖼𝗍𝖾𝗋.")
        return
    
    caption, img_url = build_caption(character, shop_items[page], page + 1, total_pages)
    
    buttons = []
    nav_buttons = []
    
    if total_pages > 1:
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("◀️ 𝗣𝗿𝗲𝘃", callback_data=f"shop_page_{page-1}"))
        nav_buttons.append(InlineKeyboardButton("🔄 𝗥𝗲𝗳𝗿𝗲𝘀𝗵", callback_data="shop_refresh"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("𝗡𝗲𝘅𝘁 ▶️", callback_data=f"shop_page_{page+1}"))
    else:
        nav_buttons.append(InlineKeyboardButton("🔄 𝗥𝗲𝗳𝗿𝗲𝘀𝗵", callback_data="shop_refresh"))
    
    buttons.append([InlineKeyboardButton("💳 𝗕𝘂𝘆", callback_data=f"shop_buy_{char_id}")])
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
    
    if data.startswith("shop_page_"):
        page = int(data.split("_")[2])
        shop_items_ids = context.user_data.get('shop_items', [])
        
        if not shop_items_ids or page >= len(shop_items_ids):
            await query.answer("⚠️ 𝖨𝗇𝗏𝖺𝗅𝗂𝖽 𝗉𝖺𝗀𝖾.", show_alert=True)
            return
        
        context.user_data['shop_page'] = page
        char_id = shop_items_ids[page]
        
        character = await characters_collection.find_one({"id": char_id})
        shop_item = await shop_collection.find_one({"id": char_id})
        
        if not character or not shop_item:
            await query.answer("⚠️ 𝖢𝗁𝖺𝗋𝖺𝖼𝗍𝖾𝗋 𝗇𝗈𝗍 𝖿𝗈𝗎𝗇𝖽.", show_alert=True)
            return
        
        caption, img_url = build_caption(character, shop_item, page + 1, len(shop_items_ids))
        
        buttons = []
        nav_buttons = []
        
        if len(shop_items_ids) > 1:
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("◀️ 𝗣𝗿𝗲𝘃", callback_data=f"shop_page_{page-1}"))
            nav_buttons.append(InlineKeyboardButton("🔄 𝗥𝗲𝗳𝗿𝗲𝘀𝗵", callback_data="shop_refresh"))
            if page < len(shop_items_ids) - 1:
                nav_buttons.append(InlineKeyboardButton("𝗡𝗲𝘅𝘁 ▶️", callback_data=f"shop_page_{page+1}"))
        else:
            nav_buttons.append(InlineKeyboardButton("🔄 𝗥𝗲𝗳𝗿𝗲𝘀𝗵", callback_data="shop_refresh"))
        
        buttons.append([InlineKeyboardButton("💳 𝗕𝘂𝘆", callback_data=f"shop_buy_{char_id}")])
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
    
    elif data == "shop_refresh":
        shop_items = await shop_collection.find({}).to_list(length=None)
        
        if not shop_items:
            await query.edit_message_caption("🏪 𝖳𝗁𝖾 𝗌𝗁𝗈𝗉 𝗂𝗌 𝖼𝗎𝗋𝗋𝖾𝗇𝗍𝗅𝗒 𝖾𝗆𝗉𝗍𝗒. 𝖢𝗁𝖾𝖼𝗄 𝖻𝖺𝖼𝗄 𝗅𝖺𝗍𝖾𝗋!")
            return
        
        page = 0
        context.user_data['shop_items'] = [item['id'] for item in shop_items]
        context.user_data['shop_page'] = page
        
        char_id = shop_items[page]['id']
        character = await characters_collection.find_one({"id": char_id})
        
        if not character:
            await query.answer("⚠️ 𝖤𝗋𝗋𝗈𝗋 𝗅𝗈𝖺𝖽𝗂𝗇𝗀 𝗌𝗁𝗈𝗉.", show_alert=True)
            return
        
        caption, img_url = build_caption(character, shop_items[page], page + 1, len(shop_items))
        
        buttons = []
        nav_buttons = []
        
        if len(shop_items) > 1:
            nav_buttons.append(InlineKeyboardButton("🔄 𝗥𝗲𝗳𝗿𝗲𝘀𝗵", callback_data="shop_refresh"))
            nav_buttons.append(InlineKeyboardButton("𝗡𝗲𝘅𝘁 ▶️", callback_data=f"shop_page_{page+1}"))
        else:
            nav_buttons.append(InlineKeyboardButton("🔄 𝗥𝗲𝗳𝗿𝗲𝘀𝗵", callback_data="shop_refresh"))
        
        buttons.append([InlineKeyboardButton("💳 𝗕𝘂𝘆", callback_data=f"shop_buy_{char_id}")])
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
        await query.answer("🔄 𝗦𝗵𝗼𝗽 𝗿𝗲𝗳𝗿𝗲𝘀𝗵𝗲𝗱!", show_alert=False)
    
    elif data.startswith("shop_buy_"):
        char_id = data.split("_", 2)[2]
        
        shop_item = await shop_collection.find_one({"id": char_id})
        if not shop_item:
            await query.answer("⚠️ 𝖳𝗁𝗂𝗌 𝗂𝗍𝖾𝗆 𝗂𝗌 𝗇𝗈 𝗅𝗈𝗇𝗀𝖾𝗋 𝖺𝗏𝖺𝗂𝗅𝖺𝖻𝗅𝖾.", show_alert=True)
            return
        
        character = await characters_collection.find_one({"id": char_id})
        if not character:
            await query.answer("⚠️ 𝖢𝗁𝖺𝗋𝖺𝖼𝗍𝖾𝗋 𝗇𝗈𝗍 𝖿𝗈𝗎𝗇𝖽.", show_alert=True)
            return
        
        price = shop_item.get("price", 0)
        
        buttons = [
            [
                InlineKeyboardButton("✅ 𝗖𝗼𝗻𝗳𝗶𝗿𝗺", callback_data=f"shop_confirm_{char_id}"),
                InlineKeyboardButton("❌ 𝗖𝗮𝗻𝗰𝗲𝗹", callback_data="shop_cancel")
            ]
        ]
        markup = InlineKeyboardMarkup(buttons)
        
        await query.edit_message_caption(
            caption=f"╭─━━━━━━━━━━━━━━━─╮\n"
                    f"│  💳 𝗖𝗢𝗡𝗙𝗜𝗥𝗠 𝗣𝗨𝗥𝗖𝗛𝗔𝗦𝗘  │\n"
                    f"╰─━━━━━━━━━━━━━━━─╯\n\n"
                    f"✨ <b>{character['name']}</b>\n"
                    f"💎 𝗣𝗿𝗶𝗰𝗲: <b>{price}</b> 𝖦𝗈𝗅𝖽\n\n"
                    f"𝖠𝗋𝖾 𝗒𝗈𝗎 𝗌𝗎𝗋𝖾 𝗒𝗈𝗎 𝗐𝖺𝗇𝗍 𝗍𝗈 𝖻𝗎𝗒 𝗍𝗁𝗂𝗌 𝖼𝗁𝖺𝗋𝖺𝖼𝗍𝖾𝗋?",
            parse_mode="HTML",
            reply_markup=markup
        )
    
    elif data.startswith("shop_confirm_"):
        char_id = data.split("_", 2)[2]
        
        shop_item = await shop_collection.find_one({"id": char_id})
        if not shop_item:
            await query.answer("⚠️ 𝖳𝗁𝗂𝗌 𝗂𝗍𝖾𝗆 𝗂𝗌 𝗇𝗈 𝗅𝗈𝗇𝗀𝖾𝗋 𝖺𝗏𝖺𝗂𝗅𝖺𝖻𝗅𝖾.", show_alert=True)
            return
        
        character = await characters_collection.find_one({"id": char_id})
        if not character:
            await query.answer("⚠️ 𝖢𝗁𝖺𝗋𝖺𝖼𝗍𝖾𝗋 𝗇𝗈𝗍 𝖿𝗈𝗎𝗇𝖽.", show_alert=True)
            return
        
        price = shop_item.get("price", 0)
        
        user_data = await user_collection.find_one({"id": user_id})
        balance = user_data.get("balance", 0) if user_data else 0
        
        if balance < price:
            await query.answer("⚠️ 𝖸𝗈𝗎 𝖽𝗈𝗇'𝗍 𝗁𝖺𝗏𝖾 𝖾𝗇𝗈𝗎𝗀𝗁 𝖦𝗈𝗅𝖽!", show_alert=True)
            await query.edit_message_caption(
                caption=f"╭─━━━━━━━━━━━━━━━━━─╮\n"
                        f"│  ⚠️ 𝗜𝗡𝗦𝗨𝗙𝗙𝗜𝗖𝗜𝗘𝗡𝗧 𝗕𝗔𝗟𝗔𝗡𝗖𝗘  │\n"
                        f"╰─━━━━━━━━━━━━━━━━━─╯\n\n"
                        f"𝖸𝗈𝗎 𝗇𝖾𝖾𝖽 <b>{price}</b> 𝖦𝗈𝗅𝖽 𝖻𝗎𝗍 𝗈𝗇𝗅𝗒 𝗁𝖺𝗏𝖾 <b>{balance}</b> 𝖦𝗈𝗅𝖽.\n"
                        f"𝖴𝗌𝖾 /bal 𝗍𝗈 𝖼𝗁𝖾𝖼𝗄 𝗒𝗈𝗎𝗋 𝖻𝖺𝗅𝖺𝗇𝖼𝖾.",
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
        
        await query.edit_message_caption(
            caption=f"╭─━━━━━━━━━━━━━━━━─╮\n"
                    f"│  ✨ 𝗣𝗨𝗥𝗖𝗛𝗔𝗦𝗘 𝗦𝗨𝗖𝗖𝗘𝗦𝗦!  │\n"
                    f"╰─━━━━━━━━━━━━━━━━─╯\n\n"
                    f"𝖸𝗈𝗎 𝖻𝗈𝗎𝗀𝗁𝗍 <b>{character['name']}</b> 𝖿𝗈𝗋 <b>{price}</b> 𝖦𝗈𝗅𝖽!\n"
                    f"𝖳𝗁𝖾 𝖼𝗁𝖺𝗋𝖺𝖼𝗍𝖾𝗋 𝗁𝖺𝗌 𝖻𝖾𝖾𝗇 𝖺𝖽𝖽𝖾𝖽 𝗍𝗈 𝗒𝗈𝗎𝗋 𝗁𝖺𝗋𝖾𝗆.\n\n"
                    f"💰 𝗥𝗲𝗺𝗮𝗶𝗻𝗶𝗻𝗴 𝗕𝗮𝗹𝗮𝗻𝗰𝗲: <b>{balance - price}</b> 𝖦𝗈𝗅𝖽",
            parse_mode="HTML"
        )
        await query.answer("✨ 𝗣𝘂𝗿𝗰𝗵𝗮𝘀𝗲 𝘀𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹!", show_alert=False)
    
    elif data == "shop_cancel":
        page = context.user_data.get('shop_page', 0)
        shop_items_ids = context.user_data.get('shop_items', [])
        
        if not shop_items_ids:
            await query.answer("⚠️ 𝖲𝖾𝗌𝗌𝗂𝗈𝗇 𝖾𝗑𝗉𝗂𝗋𝖾𝖽. 𝖯𝗅𝖾𝖺𝗌𝖾 𝗎𝗌𝖾 /store 𝖺𝗀𝖺𝗂𝗇.", show_alert=True)
            return
        
        char_id = shop_items_ids[page]
        character = await characters_collection.find_one({"id": char_id})
        shop_item = await shop_collection.find_one({"id": char_id})
        
        if not character or not shop_item:
            await query.answer("⚠️ 𝖤𝗋𝗋𝗈𝗋 𝗅𝗈𝖺𝖽𝗂𝗇𝗀 𝗌𝗁𝗈𝗉.", show_alert=True)
            return
        
        caption, img_url = build_caption(character, shop_item, page + 1, len(shop_items_ids))
        
        buttons = []
        nav_buttons = []
        
        if len(shop_items_ids) > 1:
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("◀️ 𝗣𝗿𝗲𝘃", callback_data=f"shop_page_{page-1}"))
            nav_buttons.append(InlineKeyboardButton("🔄 𝗥𝗲𝗳𝗿𝗲𝘀𝗵", callback_data="shop_refresh"))
            if page < len(shop_items_ids) - 1:
                nav_buttons.append(InlineKeyboardButton("𝗡𝗲𝘅𝘁 ▶️", callback_data=f"shop_page_{page+1}"))
        else:
            nav_buttons.append(InlineKeyboardButton("🔄 𝗥𝗲𝗳𝗿𝗲𝘀𝗵", callback_data="shop_refresh"))
        
        buttons.append([InlineKeyboardButton("💳 𝗕𝘂𝘆", callback_data=f"shop_buy_{char_id}")])
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
        await query.answer("𝗣𝘂𝗿𝗰𝗵𝗮𝘀𝗲 𝗰𝗮𝗻𝗰𝗲𝗹𝗹𝗲𝗱.", show_alert=False)

application.add_handler(CommandHandler("store", store, block=False))
application.add_handler(CommandHandler("addshop", addshop, block=False))
application.add_handler(CommandHandler("rmshop", rmshop, block=False))
application.add_handler(CallbackQueryHandler(shop_callback, pattern=r"^shop_", block=False))