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

# Import spawn settings from rarity module if available
try:
    from shivu.modules.rarity import spawn_settings_collection, get_spawn_settings
    LOGGER.info("✅ Private Store: Loaded spawn settings from rarity module")
except ImportError:
    spawn_settings_collection = None
    get_spawn_settings = None
    LOGGER.warning("⚠️ Private Store: Rarity module not available, using default config")

# Default rarity configuration (fallback if rarity module not available)
DEFAULT_RARITY_CONFIG = {
    "🟢 Common": {"chance": 60, "min_price": 10000, "max_price": 20000},
    "🟣 Rare": {"chance": 25, "min_price": 20000, "max_price": 40000},
    "🟡 Legendary": {"chance": 10, "min_price": 40000, "max_price": 80000},
    "💮 Special Edition": {"chance": 4, "min_price": 100000, "max_price": 200000},
    "💫 Neon": {"chance": 0.8, "min_price": 120000, "max_price": 250000},
    "🎐 Celestial": {"chance": 0.2, "min_price": 150000, "max_price": 300000},
}

REFRESH_INTERVAL = 86400  # 24 hours
ITEMS_PER_SESSION = 2


async def get_rarity_config():
    """Get rarity configuration - ALWAYS use default config for store"""
    return DEFAULT_RARITY_CONFIG.copy()


def get_character_rarity_display(character):
    """Get the proper rarity display string from character data"""
    try:
        char_rarity = character.get('rarity', '🟢 Common')
        
        # If rarity is already in correct format (emoji + name), return it
        if isinstance(char_rarity, str):
            # Check if it's just emoji or has name
            if ' ' in char_rarity:
                return char_rarity
            else:
                # Just emoji, try to find name
                emoji = char_rarity
                # Map emoji to name from default config
                for key in DEFAULT_RARITY_CONFIG.keys():
                    if key.startswith(emoji):
                        return key
                return f"{emoji} Unknown"
        
        # Fallback
        return "🟢 Common"
    
    except Exception as e:
        LOGGER.error(f"Error getting character rarity display: {e}")
        return "🟢 Common"


def get_price_range_for_character(character):
    """Get price range based on character's actual rarity"""
    try:
        char_rarity = character.get('rarity', '🟢 Common')
        
        # Extract emoji from rarity
        if isinstance(char_rarity, str) and ' ' in char_rarity:
            rarity_emoji = char_rarity.split(' ')[0]
        else:
            rarity_emoji = char_rarity
        
        # Price ranges based on rarity emoji
        price_ranges = {
            '🟢': (10000, 20000),      # Common
            '🟣': (20000, 40000),      # Rare
            '🟡': (40000, 80000),      # Legendary
            '💮': (100000, 200000),    # Special Edition
            '💫': (120000, 250000),    # Neon
            '✨': (80000, 150000),     # Manga
            '🎭': (90000, 180000),     # Cosplay
            '🎐': (150000, 300000),    # Celestial
            '🔮': (200000, 400000),    # Premium Edition
            '💋': (180000, 350000),    # Erotic
            '🌤': (100000, 200000),    # Summer
            '☃️': (100000, 200000),    # Winter
            '☔️': (90000, 180000),     # Monsoon
            '💝': (150000, 300000),    # Valentine
            '🎃': (150000, 300000),    # Halloween
            '🎄': (150000, 300000),    # Christmas
            '🏵': (500000, 1000000),   # Mythic
            '🎗': (400000, 800000),    # Special Events
            '🎥': (300000, 600000),    # AMV
            '👼': (250000, 500000),    # Tiny
        }
        
        return price_ranges.get(rarity_emoji, (50000, 100000))
    
    except Exception as e:
        LOGGER.error(f"Error getting price range: {e}")
        return (50000, 100000)


async def is_character_allowed(character):
    """Check if character is allowed based on spawn settings"""
    try:
        if character.get('removed', False):
            return False
        
        if get_spawn_settings:
            settings = await get_spawn_settings()
            rarities = settings.get('rarities', {})
            
            char_rarity = character.get('rarity', '🟢 Common')
            
            # Extract emoji from rarity
            if isinstance(char_rarity, str) and ' ' in char_rarity:
                rarity_emoji = char_rarity.split(' ')[0]
            else:
                rarity_emoji = char_rarity
            
            # Check if rarity is enabled
            if rarity_emoji in rarities:
                if not rarities[rarity_emoji].get('enabled', True):
                    return False
        
        return True
    
    except Exception as e:
        LOGGER.error(f"Error checking character: {e}")
        return True


async def random_character():
    """Get a random character from database"""
    try:
        # Get all characters
        all_chars = await characters_collection.find({}).to_list(length=None)
        
        if not all_chars:
            return None
        
        # Filter out removed characters
        available_chars = [c for c in all_chars if not c.get('removed', False)]
        
        if not available_chars:
            LOGGER.warning("No available characters found for store")
            return None
        
        # Return random character
        return random.choice(available_chars)
    
    except Exception as e:
        LOGGER.error(f"Error getting random character: {e}")
        return None


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
    """Generate new session with random characters"""
    try:
        session = []
        
        for _ in range(ITEMS_PER_SESSION):
            char = await random_character()
            if not char:
                continue
            
            # Get character's actual rarity display
            rarity_display = get_character_rarity_display(char)
            
            # Get price range based on character's actual rarity
            min_price, max_price = get_price_range_for_character(char)
            price = random.randint(min_price, max_price)
            
            session.append({
                "id": char["id"],
                "rarity": rarity_display,  # Use character's actual rarity
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
        
        LOGGER.info(f"Generated new store session for user {user_id} with {len(session)} items")
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
        # Find first non-purchased item
        available_items = [i for i, item in enumerate(session) if not item.get("purchased", False)]

        if not available_items:
            # All items purchased
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

        # Set page to first available item if current page is purchased
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

        # Navigation buttons
        buttons = []
        nav = []

        # Find previous available item
        prev_available = [i for i in range(page) if not session[i].get("purchased", False)]
        if prev_available:
            nav.append(InlineKeyboardButton("◀", callback_data=f"ps_page_{prev_available[-1]}"))

        nav.append(InlineKeyboardButton("🔄 ʀᴇғʀᴇsʜ", callback_data="ps_refresh"))

        # Find next available item
        next_available = [i for i in range(page + 1, len(session)) if not session[i].get("purchased", False)]
        if next_available:
            nav.append(InlineKeyboardButton("▶", callback_data=f"ps_page_{next_available[0]}"))

        if nav:
            buttons.append(nav)
        buttons.append([InlineKeyboardButton("✅ ʙᴜʏ", callback_data=f"ps_buy_{data['id']}_{page}")])
        markup = InlineKeyboardMarkup(buttons)

        if is_new:
            # Initial /ps command - send new message
            await message_or_query.reply_photo(
                photo=data["img"],
                caption=caption,
                parse_mode="HTML",
                reply_markup=markup
            )
        else:
            # CallbackQuery update - edit same message
            try:
                # Try to edit the media (image + caption)
                media = InputMediaPhoto(media=data["img"], caption=caption, parse_mode="HTML")
                await message_or_query.edit_message_media(media=media, reply_markup=markup)
            except Exception as e:
                LOGGER.error(f"Error editing media: {e}")
                # If media edit fails, just try to update caption
                try:
                    await message_or_query.edit_message_caption(
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=markup
                    )
                except Exception as e2:
                    LOGGER.error(f"Error editing caption: {e2}")
                    # If all else fails, answer the callback
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
            await show_ps_page(query, context, session, page, is_new=False)
            return

        # Refresh store
        if data == "ps_refresh":
            new_session = await generate_session(user_id)
            if new_session:
                context.user_data["ps_page"] = 0
                await show_ps_page(query, context, new_session, 0, is_new=False)
                await query.answer("sᴛᴏʀᴇ ʀᴇғʀᴇsʜᴇᴅ!", show_alert=False)
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
                # Show next available character
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


# ==================== AUTO-REGISTER HANDLERS ====================
# Handlers register automatically when module is imported
try:
    application.add_handler(CommandHandler("ps", ps, block=False))
    application.add_handler(CallbackQueryHandler(ps_callback, pattern=r"^ps_", block=False))
    LOGGER.info("✅ Private Store handlers registered automatically")
except Exception as e:
    LOGGER.error(f"❌ Failed to register Private Store handlers: {e}")
    LOGGER.error(traceback.format_exc())