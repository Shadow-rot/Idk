import random
import time
import traceback
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)
from telegram.ext import CommandHandler, CallbackQueryHandler, CallbackContext
from shivu import application, user_collection, user_totals_collection, db, LOGGER

characters_collection = db["anime_characters_lol"]
ps_config_collection = db["ps_config"]
SUDO_USERS = [6737275496, 5147822244]  # Add your admin IDs here

# Rarity configuration with spawn chances and price ranges
RARITY_CONFIG = {
    "🟢 Common": {"chance": 60, "min_price": 10000, "max_price": 20000, "enabled": True},
    "🟣 Rare": {"chance": 25, "min_price": 20000, "max_price": 40000, "enabled": True},
    "🟡 Legendary": {"chance": 10, "min_price": 40000, "max_price": 80000, "enabled": True},
    "💮 Special Edition": {"chance": 4, "min_price": 100000, "max_price": 200000, "enabled": True},
    "💫 Neon": {"chance": 0.8, "min_price": 120000, "max_price": 250000, "enabled": True},
    "🎐 Celestial": {"chance": 0.2, "min_price": 150000, "max_price": 300000, "enabled": True},
}

REFRESH_INTERVAL = 86400  # 24 hours
ITEMS_PER_SESSION = 2
REFRESH_COST = 2000
MAX_DAILY_REFRESHES = 3


async def get_ps_config():
    """Get PS configuration from database"""
    config = await ps_config_collection.find_one({"_id": "ps_settings"})
    if not config:
        # Initialize with default config
        config = {"_id": "ps_settings", "rarities": RARITY_CONFIG.copy()}
        await ps_config_collection.insert_one(config)
    return config.get("rarities", RARITY_CONFIG.copy())


async def update_ps_config(rarities):
    """Update PS configuration in database"""
    await ps_config_collection.update_one(
        {"_id": "ps_settings"},
        {"$set": {"rarities": rarities}},
        upsert=True
    )


def get_character_rarity_info(character):
    """Extract rarity emoji and full display from character data"""
    try:
        char_rarity = character.get('rarity', '🟢 Common')
        
        if isinstance(char_rarity, str):
            if ' ' in char_rarity:
                # Has both emoji and name
                return char_rarity, char_rarity.split(' ')[0]
            else:
                # Just emoji
                emoji = char_rarity
                # Try to find full name in config
                for key in RARITY_CONFIG.keys():
                    if key.startswith(emoji):
                        return key, emoji
                return f"{emoji} Unknown", emoji
        
        return "🟢 Common", "🟢"
    except Exception as e:
        LOGGER.error(f"Error getting character rarity: {e}")
        return "🟢 Common", "🟢"


async def get_weighted_character(config):
    """Get a random character based on rarity weights"""
    try:
        # Get all non-removed characters
        all_chars = await characters_collection.find({"removed": {"$ne": True}}).to_list(length=None)
        
        if not all_chars:
            return None
        
        # Group characters by rarity
        rarity_groups = {}
        for char in all_chars:
            rarity_display, rarity_emoji = get_character_rarity_info(char)
            
            # Check if this rarity is enabled
            rarity_enabled = False
            for config_rarity, settings in config.items():
                if config_rarity.startswith(rarity_emoji) and settings.get('enabled', True):
                    rarity_enabled = True
                    break
            
            if not rarity_enabled:
                continue
            
            if rarity_display not in rarity_groups:
                rarity_groups[rarity_display] = []
            rarity_groups[rarity_display].append(char)
        
        if not rarity_groups:
            LOGGER.warning("No enabled rarities found")
            return None
        
        # Build weighted list based on chances
        weighted_rarities = []
        for rarity, chars in rarity_groups.items():
            # Find matching config
            chance = 0
            for config_rarity, settings in config.items():
                if config_rarity == rarity or config_rarity.startswith(rarity.split(' ')[0]):
                    if settings.get('enabled', True):
                        chance = settings.get('chance', 0)
                    break
            
            if chance > 0:
                # Add rarity multiple times based on chance (multiply by 10 for precision)
                weighted_rarities.extend([rarity] * int(chance * 10))
        
        if not weighted_rarities:
            LOGGER.warning("No weighted rarities available")
            return None
        
        # Select random rarity based on weight
        selected_rarity = random.choice(weighted_rarities)
        
        # Select random character from that rarity
        if selected_rarity in rarity_groups and rarity_groups[selected_rarity]:
            return random.choice(rarity_groups[selected_rarity])
        
        return None
        
    except Exception as e:
        LOGGER.error(f"Error getting weighted character: {e}")
        LOGGER.error(traceback.format_exc())
        return None


def get_price_for_rarity(rarity_display, config):
    """Get random price based on rarity"""
    try:
        rarity_emoji = rarity_display.split(' ')[0]
        
        # Find matching config
        for config_rarity, settings in config.items():
            if config_rarity == rarity_display or config_rarity.startswith(rarity_emoji):
                min_price = settings.get('min_price', 50000)
                max_price = settings.get('max_price', 100000)
                return random.randint(min_price, max_price)
        
        # Fallback
        return random.randint(50000, 100000)
    except Exception as e:
        LOGGER.error(f"Error getting price: {e}")
        return 50000


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
    """Generate new session with weighted random characters"""
    try:
        config = await get_ps_config()
        session = []
        
        for _ in range(ITEMS_PER_SESSION):
            char = await get_weighted_character(config)
            if not char:
                continue
            
            rarity_display, _ = get_character_rarity_info(char)
            price = get_price_for_rarity(rarity_display, config)
            
            session.append({
                "id": char["id"],
                "rarity": rarity_display,
                "price": price,
                "img": char.get("img_url"),
                "purchased": False
            })
        
        if not session:
            LOGGER.warning(f"Failed to generate session for user {user_id}")
            return []
        
        await user_collection.update_one(
            {"id": user_id},
            {"$set": {"ps_session": session, "ps_refresh": time.time()}},
            upsert=True
        )
        
        LOGGER.info(f"Generated store session for user {user_id}: {len(session)} items")
        return session
        
    except Exception as e:
        LOGGER.error(f"Error generating session: {e}")
        LOGGER.error(traceback.format_exc())
        return []


async def ps(update: Update, context: CallbackContext):
    """Main /ps command handler"""
    try:
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
        
        # Check if all purchased
        all_purchased = all(item.get("purchased", False) for item in session)
        if all_purchased:
            time_left = int(REFRESH_INTERVAL - (now - user_data.get("ps_refresh", 0)))
            hours_left = time_left // 3600
            mins_left = (time_left % 3600) // 60
            await update.message.reply_text(
                f"╭──────────────╮\n"
                f"│  sᴛᴏʀᴇ ᴇᴍᴘᴛʏ │\n"
                f"╰──────────────╯\n\n"
                f"ʏᴏᴜ'ᴠᴇ ʙᴏᴜɢʜᴛ ᴀʟʟ ᴀᴠᴀɪʟᴀʙʟᴇ ᴄʜᴀʀᴀᴄᴛᴇʀs!\n\n"
                f"⏰ ᴄᴏᴍᴇ ʙᴀᴄᴋ ɪɴ: {hours_left}ʜ {mins_left}ᴍ"
            )
            return
        
        context.user_data["ps_page"] = 0
        context.user_data["ps_user_id"] = user_id
        await show_ps_page(update.message, context, session, 0, is_new=True)
        
    except Exception as e:
        LOGGER.error(f"Error in ps command: {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text("❌ An error occurred. Please try again.")


async def show_ps_page(message_or_query, context, session, page, is_new=False):
    """Display a specific page of the private store"""
    try:
        user_id = context.user_data.get("ps_user_id")
        user_data = await user_collection.find_one({"id": user_id})
        
        # Find first non-purchased item
        available_items = [i for i, item in enumerate(session) if not item.get("purchased", False)]
        
        if not available_items:
            caption = (
                f"╭──────────────╮\n"
                f"│  sᴛᴏʀᴇ ᴇᴍᴘᴛʏ │\n"
                f"╰──────────────╯\n\n"
                f"ʏᴏᴜ'ᴠᴇ ʙᴏᴜɢʜᴛ ᴀʟʟ ᴀᴠᴀɪʟᴀʙʟᴇ ᴄʜᴀʀᴀᴄᴛᴇʀs!\n\n"
                f"⏰ ᴄᴏᴍᴇ ʙᴀᴄᴋ ᴀғᴛᴇʀ 24 ʜᴏᴜʀs"
            )
            if is_new:
                await message_or_query.reply_text(caption)
            else:
                await message_or_query.edit_message_caption(caption=caption, parse_mode="HTML")
            return
        
        if page >= len(session) or session[page].get("purchased", False):
            page = available_items[0]
        
        total = len(session)
        data = session[page]
        char = await characters_collection.find_one({"id": data["id"]})
        
        if not char:
            if is_new:
                await message_or_query.reply_text("ᴄʜᴀʀᴀᴄᴛᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ.")
            else:
                await message_or_query.answer("ᴄʜᴀʀᴀᴄᴛᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ.", show_alert=True)
            return
        
        caption = make_caption(char, data["rarity"], data["price"], page + 1, total)
        
        # Get refresh info
        today = time.strftime("%Y-%m-%d")
        refresh_data = user_data.get("ps_refresh_data", {})
        daily_refreshes = refresh_data.get(today, 0)
        refreshes_left = MAX_DAILY_REFRESHES - daily_refreshes
        
        # Navigation buttons
        buttons = []
        nav = []
        
        prev_available = [i for i in range(page) if not session[i].get("purchased", False)]
        if prev_available:
            nav.append(InlineKeyboardButton("◀", callback_data=f"ps_page_{prev_available[-1]}"))
        
        # Show refresh with cost and remaining uses
        if refreshes_left > 0:
            nav.append(InlineKeyboardButton(
                f"🔄 ʀᴇғʀᴇsʜ ({REFRESH_COST:,}💰 | {refreshes_left}/3)", 
                callback_data="ps_refresh"
            ))
        else:
            nav.append(InlineKeyboardButton("🔄 ʀᴇғʀᴇsʜ (0/3)", callback_data="ps_refresh_limit"))
        
        next_available = [i for i in range(page + 1, len(session)) if not session[i].get("purchased", False)]
        if next_available:
            nav.append(InlineKeyboardButton("▶", callback_data=f"ps_page_{next_available[0]}"))
        
        if nav:
            buttons.append(nav)
        buttons.append([InlineKeyboardButton("✅ ʙᴜʏ", callback_data=f"ps_buy_{data['id']}_{page}")])
        markup = InlineKeyboardMarkup(buttons)
        
        if is_new:
            await message_or_query.reply_photo(
                photo=data["img"],
                caption=caption,
                parse_mode="HTML",
                reply_markup=markup
            )
        else:
            try:
                media = InputMediaPhoto(media=data["img"], caption=caption, parse_mode="HTML")
                await message_or_query.edit_message_media(media=media, reply_markup=markup)
            except Exception as e:
                LOGGER.error(f"Error editing media: {e}")
                try:
                    await message_or_query.edit_message_caption(
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=markup
                    )
                except Exception as e2:
                    LOGGER.error(f"Error editing caption: {e2}")
                    await message_or_query.answer("ᴇʀʀᴏʀ ᴜᴘᴅᴀᴛɪɴɢ ᴘᴀɢᴇ.", show_alert=True)
    
    except Exception as e:
        LOGGER.error(f"Error showing page: {e}")
        LOGGER.error(traceback.format_exc())


async def ps_callback(update: Update, context: CallbackContext):
    """Handle all private store callbacks"""
    try:
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
            context.user_data["ps_user_id"] = user_id
            await show_ps_page(query, context, session, page, is_new=False)
            return
        
        # Refresh limit reached
        if data == "ps_refresh_limit":
            await query.answer("❌ ᴅᴀɪʟʏ ʀᴇғʀᴇsʜ ʟɪᴍɪᴛ ʀᴇᴀᴄʜᴇᴅ (3/3)", show_alert=True)
            return
        
        # Refresh store
        if data == "ps_refresh":
            balance = user_data.get("balance", 0)
            
            # Check balance
            if balance < REFRESH_COST:
                await query.answer(
                    f"❌ ɴᴏᴛ ᴇɴᴏᴜɢʜ ɢᴏʟᴅ!\nʀᴇǫᴜɪʀᴇᴅ: {REFRESH_COST:,}\nʏᴏᴜʀ ʙᴀʟᴀɴᴄᴇ: {balance:,}",
                    show_alert=True
                )
                return
            
            # Check daily refresh limit
            today = time.strftime("%Y-%m-%d")
            refresh_data = user_data.get("ps_refresh_data", {})
            daily_refreshes = refresh_data.get(today, 0)
            
            if daily_refreshes >= MAX_DAILY_REFRESHES:
                await query.answer("❌ ᴅᴀɪʟʏ ʀᴇғʀᴇsʜ ʟɪᴍɪᴛ ʀᴇᴀᴄʜᴇᴅ (3/3)", show_alert=True)
                return
            
            # Deduct cost and increment refresh count
            refresh_data[today] = daily_refreshes + 1
            
            await user_collection.update_one(
                {"id": user_id},
                {
                    "$inc": {"balance": -REFRESH_COST},
                    "$set": {"ps_refresh_data": refresh_data}
                }
            )
            
            # Generate new session
            new_session = await generate_session(user_id)
            if new_session:
                context.user_data["ps_page"] = 0
                context.user_data["ps_user_id"] = user_id
                await show_ps_page(query, context, new_session, 0, is_new=False)
                remaining = MAX_DAILY_REFRESHES - refresh_data[today]
                await query.answer(
                    f"✅ sᴛᴏʀᴇ ʀᴇғʀᴇsʜᴇᴅ!\n-{REFRESH_COST:,} ɢᴏʟᴅ\nʀᴇғʀᴇsʜᴇs ʟᴇғᴛ: {remaining}/3",
                    show_alert=False
                )
            else:
                await query.answer("Failed to refresh store.", show_alert=True)
            return
        
        # Buy button
        if data.startswith("ps_buy_"):
            parts = data.split("_")
            char_id = parts[2]
            page = int(parts[3]) if len(parts) > 3 else 0
            
            item = next((x for x in session if x["id"] == char_id), None)
            
            if not item:
                await query.answer("ᴄʜᴀʀᴀᴄᴛᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ.", show_alert=True)
                return
            
            if item.get("purchased", False):
                await query.answer("ᴛʜɪs ᴄʜᴀʀᴀᴄᴛᴇʀ ᴀʟʀᴇᴀᴅʏ ᴘᴜʀᴄʜᴀsᴇᴅ.", show_alert=True)
                return
            
            char = await characters_collection.find_one({"id": char_id})
            if not char:
                await query.answer("ᴄʜᴀʀᴀᴄᴛᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ ɪɴ ᴅᴀᴛᴀʙᴀsᴇ.", show_alert=True)
                return
            
            balance = user_data.get("balance", 0)
            caption = (
                f"╭──────────────╮\n"
                f"│  ᴄᴏɴғɪʀᴍ ʙᴜʏ │\n"
                f"╰──────────────╯\n\n"
                f"⋄ ɴᴀᴍᴇ: {char['name'].lower()}\n"
                f"⋄ ʀᴀʀɪᴛʏ: {item['rarity']}\n"
                f"⋄ ᴘʀɪᴄᴇ: {item['price']:,} ɢᴏʟᴅ\n"
                f"⋄ ʏᴏᴜʀ ʙᴀʟᴀɴᴄᴇ: {balance:,} ɢᴏʟᴅ\n\n"
                f"ᴘʀᴇss ᴄᴏɴғɪʀᴍ ᴛᴏ ᴄᴏᴍᴘʟᴇᴛᴇ ᴘᴜʀᴄʜᴀsᴇ."
            )
            buttons = [
                [
                    InlineKeyboardButton("✅ ᴄᴏɴғɪʀᴍ", callback_data=f"ps_confirm_{char_id}_{page}"),
                    InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data=f"ps_cancel_{page}")
                ]
            ]
            
            try:
                media = InputMediaPhoto(media=item["img"], caption=caption, parse_mode="HTML")
                await query.edit_message_media(media=media, reply_markup=InlineKeyboardMarkup(buttons))
            except Exception as e:
                LOGGER.error(f"Error showing confirmation: {e}")
                await query.answer("ᴇʀʀᴏʀ sʜᴏᴡɪɴɢ ᴄᴏɴғɪʀᴍᴀᴛɪᴏɴ.", show_alert=True)
            return
        
        # Confirm purchase
        if data.startswith("ps_confirm_"):
            parts = data.split("_")
            char_id = parts[2]
            page = int(parts[3]) if len(parts) > 3 else 0
            
            item_index = next((i for i, x in enumerate(session) if x["id"] == char_id), None)
            if item_index is None:
                await query.answer("ᴄʜᴀʀᴀᴄᴛᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ.", show_alert=True)
                return
            
            item = session[item_index]
            
            if item.get("purchased", False):
                await query.answer("ᴀʟʀᴇᴀᴅʏ ᴘᴜʀᴄʜᴀsᴇᴅ.", show_alert=True)
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
            
            # Mark as purchased
            session[item_index]["purchased"] = True
            
            # Update user collection and balance
            await user_collection.update_one(
                {"id": user_id},
                {
                    "$inc": {"balance": -item["price"]},
                    "$push": {"characters": char},
                    "$set": {"ps_session": session}
                },
                upsert=True
            )
            
            # Update user totals
            await user_totals_collection.update_one(
                {"id": user_id},
                {"$inc": {"count": 1}},
                upsert=True
            )
            
            # Check if there are more available items
            available_items = [i for i, x in enumerate(session) if not x.get("purchased", False)]
            
            if available_items:
                new_balance = balance - item["price"]
                success_caption = (
                    f"✅ ᴘᴜʀᴄʜᴀsᴇ sᴜᴄᴄᴇssғᴜʟ!\n\n"
                    f"⋄ ʙᴏᴜɢʜᴛ: {char['name'].lower()}\n"
                    f"⋄ ᴘʀɪᴄᴇ: {item['price']:,} ɢᴏʟᴅ\n"
                    f"⋄ ɴᴇᴡ ʙᴀʟᴀɴᴄᴇ: {new_balance:,} ɢᴏʟᴅ\n\n"
                    f"sʜᴏᴡɪɴɢ ɴᴇxᴛ ᴀᴠᴀɪʟᴀʙʟᴇ ᴄʜᴀʀᴀᴄᴛᴇʀ..."
                )
                await query.edit_message_caption(caption=success_caption, parse_mode="HTML")
                await query.answer("ʙᴏᴜɢʜᴛ sᴜᴄᴄᴇssғᴜʟʟʏ!", show_alert=False)
                
                import asyncio
                await asyncio.sleep(2)
                
                # Refresh user data
                user_data = await user_collection.find_one({"id": user_id})
                session = user_data.get("ps_session", [])
                context.user_data["ps_user_id"] = user_id
                
                await show_ps_page(query, context, session, available_items[0], is_new=False)
            else:
                # All items purchased
                new_balance = balance - item["price"]
                final_caption = (
                    f"✅ ᴘᴜʀᴄʜᴀsᴇ sᴜᴄᴄᴇssғᴜʟ!\n\n"
                    f"⋄ ʙᴏᴜɢʜᴛ: {char['name'].lower()}\n"
                    f"⋄ ᴘʀɪᴄᴇ: {item['price']:,} ɢᴏʟᴅ\n"
                    f"⋄ ɴᴇᴡ ʙᴀʟᴀɴᴄᴇ: {new_balance:,} ɢᴏʟᴅ\n\n"
                    f"╭──────────────╮\n"
                    f"│  sᴛᴏʀᴇ ᴇᴍᴘᴛʏ │\n"
                    f"╰──────────────╯\n\n"
                    f"ʏᴏᴜ'ᴠᴇ ʙᴏᴜɢʜᴛ ᴀʟʟ ᴄʜᴀʀᴀᴄᴛᴇʀs!\n"
                    f"⏰ ᴄᴏᴍᴇ ʙᴀᴄᴋ ᴀғᴛᴇʀ 24 ʜᴏᴜʀs"
                )
                await query.edit_message_caption(caption=final_caption, parse_mode="HTML")
                await query.answer("ᴀʟʟ ᴄʜᴀʀᴀᴄᴛᴇʀs ᴘᴜʀᴄʜᴀsᴇᴅ!", show_alert=False)
            return
        
        # Cancel purchase
        if data.startswith("ps_cancel_"):
            parts = data.split("_")
            page = int(parts[2]) if len(parts) > 2 else 0
            context.user_data["ps_user_id"] = user_id
            await show_ps_page(query, context, session, page, is_new=False)
            await query.answer("ᴘᴜʀᴄʜᴀsᴇ ᴄᴀɴᴄᴇʟʟᴇᴅ.", show_alert=False)
            return
    
    except Exception as e:
        LOGGER.error(f"Error in ps_callback: {e}")
        LOGGER.error(traceback.format_exc())
        try:
            await update.callback_query.answer("❌ An error occurred.", show_alert=True)
        except:
            pass


# ==================== ADMIN PANEL ====================

async def pspanel(update: Update, context: CallbackContext):
    """Admin command to configure PS rarity settings"""
    try:
        user_id = update.effective_user.id
        
        if user_id not in SUDO_USERS:
            await update.message.reply_text("❌ ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴘᴇʀᴍɪssɪᴏɴ ᴛᴏ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ.")
            return
        
        await show_panel(update.message, is_new=True)
        
    except Exception as e:
        LOGGER.error(f"Error in pspanel: {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text("❌ An error occurred.")


async def show_panel(message_or_query, is_new=False):
    """Display the PS configuration panel"""
    try:
        config = await get_ps_config()
        
        caption = "╭─────────────────╮\n"
        caption += "│  ᴘs ᴄᴏɴғɪɢ ᴘᴀɴᴇʟ  │\n"
        caption += "╰─────────────────╯\n\n"
        caption += "ᴄᴏɴғɪɢᴜʀᴇ ᴡʜɪᴄʜ ʀᴀʀɪᴛɪᴇs ᴄᴀɴ sᴘᴀᴡɴ ɪɴ ᴘʀɪᴠᴀᴛᴇ sᴛᴏʀᴇ:\n\n"
        
        buttons = []
        
        # Sort rarities by chance (descending)
        sorted_rarities = sorted(config.items(), key=lambda x: x[1].get('chance', 0), reverse=True)
        
        for rarity, settings in sorted_rarities:
            enabled = settings.get('enabled', True)
            chance = settings.get('chance', 0)
            min_price = settings.get('min_price', 0)
            max_price = settings.get('max_price', 0)
            
            status = "✅" if enabled else "❌"
            caption += f"{status} {rarity}\n"
            caption += f"   • ᴄʜᴀɴᴄᴇ: {chance}%\n"
            caption += f"   • ᴘʀɪᴄᴇ: {min_price:,} - {max_price:,}\n\n"
            
            # Create toggle button
            emoji = rarity.split(' ')[0]
            button_text = f"{status} {emoji}"
            callback_data = f"psp_toggle_{emoji}"
            
            buttons.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        buttons.append([InlineKeyboardButton("🔄 ʀᴇғʀᴇsʜ", callback_data="psp_refresh")])
        buttons.append([InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="psp_close")])
        
        markup = InlineKeyboardMarkup(buttons)
        
        if is_new:
            await message_or_query.reply_text(
                caption,
                parse_mode="HTML",
                reply_markup=markup
            )
        else:
            await message_or_query.edit_text(
                caption,
                parse_mode="HTML",
                reply_markup=markup
            )
    
    except Exception as e:
        LOGGER.error(f"Error showing panel: {e}")
        LOGGER.error(traceback.format_exc())


async def pspanel_callback(update: Update, context: CallbackContext):
    """Handle PS panel callbacks"""
    try:
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id not in SUDO_USERS:
            await query.answer("❌ ᴜɴᴀᴜᴛʜᴏʀɪᴢᴇᴅ", show_alert=True)
            return
        
        data = query.data
        
        # Close panel
        if data == "psp_close":
            await query.message.delete()
            await query.answer("ᴘᴀɴᴇʟ ᴄʟᴏsᴇᴅ")
            return
        
        # Refresh panel
        if data == "psp_refresh":
            await show_panel(query.message, is_new=False)
            await query.answer("ᴘᴀɴᴇʟ ʀᴇғʀᴇsʜᴇᴅ")
            return
        
        # Toggle rarity
        if data.startswith("psp_toggle_"):
            emoji = data.split("_")[2]
            config = await get_ps_config()
            
            # Find and toggle the rarity
            toggled = False
            for rarity, settings in config.items():
                if rarity.startswith(emoji):
                    settings['enabled'] = not settings.get('enabled', True)
                    status = "ᴇɴᴀʙʟᴇᴅ" if settings['enabled'] else "ᴅɪsᴀʙʟᴇᴅ"
                    toggled = True
                    break
            
            if toggled:
                await update_ps_config(config)
                await show_panel(query.message, is_new=False)
                await query.answer(f"{emoji} {status}")
            else:
                await query.answer("ʀᴀʀɪᴛʏ ɴᴏᴛ ғᴏᴜɴᴅ", show_alert=True)
            return
    
    except Exception as e:
        LOGGER.error(f"Error in pspanel_callback: {e}")
        LOGGER.error(traceback.format_exc())
        await query.answer("❌ An error occurred", show_alert=True)


# ==================== AUTO-REGISTER HANDLERS ====================
try:
    application.add_handler(CommandHandler("ps", ps, block=False))
    application.add_handler(CommandHandler("pspanel", pspanel, block=False))
    application.add_handler(CallbackQueryHandler(ps_callback, pattern=r"^ps_", block=False))
    application.add_handler(CallbackQueryHandler(pspanel_callback, pattern=r"^psp_", block=False))
    LOGGER.info("✅ Private Store handlers registered successfully")
except Exception as e:
    LOGGER.error(f"❌ Failed to register Private Store handlers: {e}")
    LOGGER.error(traceback.format_exc())