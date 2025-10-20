# modules/spellcast_futuristic.py
import random
import time
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, CallbackContext
from shivu import application, db

# Collections
wizards_collection = db.wizards
duels_collection = db.active_duels
clans_collection = db.clans

# ------------------------
# GAME CONFIG
# ------------------------
BASE_HP = 100
BASE_MANA = 50
MANA_REGEN_PER_TURN = 10
SPELL_COOLDOWN = 3
DUEL_TIMEOUT = 120
DAILY_BONUS_COINS = 50
DAILY_BONUS_XP = 20

# Elemental advantages
ELEMENT_ADVANTAGE = {
    'fire': 'ice',
    'ice': 'lightning',
    'lightning': 'fire',
    'light': 'dark',
    'dark': 'light'
}

# ------------------------
# CINEMATIC GIF LIBRARY
# ------------------------
CINEMATIC_GIFS = {
    'fireball': [
        'https://media.giphy.com/media/xUA7b2mljEC39bwmqc/giphy.gif',
        'https://media.giphy.com/media/l0HlQXlQ3nHyLMvte/giphy.gif'
    ],
    'inferno': [
        'https://media.giphy.com/media/13HgwGsXF0aiGY/giphy.gif',
        'https://media.giphy.com/media/uPnKU86sFa2fm/giphy.gif'
    ],
    'meteor': [
        'https://media.giphy.com/media/mq5y2jHRCAqMo/giphy.gif'
    ],
    'frost': [
        'https://media.giphy.com/media/5nsiFjdgylfK3csZ5T/giphy.gif',
        'https://media.giphy.com/media/l0HlR3kHtkgpnTzRu/giphy.gif'
    ],
    'blizzard': [
        'https://media.giphy.com/media/l0Hlvh1us2dpuNglO/giphy.gif'
    ],
    'glacier': [
        'https://media.giphy.com/media/3oEjI105rmEC22CJFK/giphy.gif'
    ],
    'spark': [
        'https://media.giphy.com/media/l0HlNQ03J5JxX6lva/giphy.gif',
        'https://media.giphy.com/media/26tOZ42Mg6pbTUPHW/giphy.gif'
    ],
    'thunder': [
        'https://media.giphy.com/media/xUA7aZeLE2e0P7Znz2/giphy.gif'
    ],
    'storm': [
        'https://media.giphy.com/media/xUOwGhOrYP0jP6iAy4/giphy.gif'
    ],
    'holy': [
        'https://media.giphy.com/media/VIPdgcooFJHtC/giphy.gif'
    ],
    'shadow': [
        'https://media.giphy.com/media/l0HlNaQ6gWfllcjDO/giphy.gif'
    ],
    'void': [
        'https://media.giphy.com/media/xUOwGhOrYP0jP6iAy4/giphy.gif'
    ],
    'heal': [
        'https://media.giphy.com/media/9rtpurjbqiqZXbBBet/giphy.gif'
    ],
    'shield': [
        'https://media.giphy.com/media/UO5elnTqo4vSg/giphy.gif'
    ],
    'victory': [
        'https://media.giphy.com/media/g9582DNuQppxC/giphy.gif'
    ],
    'duel': [
        'https://media.giphy.com/media/l0HlPystfePnAI3G8/giphy.gif'
    ]
}

def get_gif(key: str) -> str:
    """Get random GIF for a key"""
    gifs = CINEMATIC_GIFS.get(key, CINEMATIC_GIFS.get('spark'))
    return random.choice(gifs)

# ------------------------
# SPELL DATABASE
# ------------------------
SPELLS = {
    # Tier 1
    'fireball': {
        'name': '🔥 ꜰɪʀᴇʙᴀʟʟ',
        'element': 'fire',
        'damage': 20,
        'mana': 10,
        'level_req': 1,
        'crit_chance': 0.15,
        'price': 0,
        'desc': 'ʙᴀꜱɪᴄ ꜰɪʀᴇ ꜱᴘᴇʟʟ',
        'emoji': '🔥'
    },
    'frost': {
        'name': '❄️ ꜰʀᴏꜱᴛ ꜱʜᴀʀᴅ',
        'element': 'ice',
        'damage': 18,
        'mana': 10,
        'level_req': 1,
        'crit_chance': 0.12,
        'price': 0,
        'desc': 'ꜰʀᴇᴇᴢɪɴɢ ᴀᴛᴛᴀᴄᴋ',
        'emoji': '❄️'
    },
    'spark': {
        'name': '⚡ ʟɪɢʜᴛɴɪɴɢ ꜱᴘᴀʀᴋ',
        'element': 'lightning',
        'damage': 22,
        'mana': 12,
        'level_req': 1,
        'crit_chance': 0.20,
        'price': 0,
        'desc': 'Qᴜɪᴄᴋ ᴇʟᴇᴄᴛʀɪᴄ ꜱᴛʀɪᴋᴇ',
        'emoji': '⚡'
    },

    # Tier 2
    'inferno': {
        'name': '🔥 ɪɴꜰᴇʀɴᴏ ʙʟᴀꜱᴛ',
        'element': 'fire',
        'damage': 35,
        'mana': 20,
        'level_req': 5,
        'crit_chance': 0.18,
        'price': 150,
        'desc': 'ᴘᴏᴡᴇʀꜰᴜʟ ꜰɪʀᴇ ᴇxᴘʟᴏꜱɪᴏɴ',
        'emoji': '🔥'
    },
    'blizzard': {
        'name': '❄️ ʙʟɪᴢᴢᴀʀᴅ',
        'element': 'ice',
        'damage': 40,
        'mana': 22,
        'level_req': 5,
        'crit_chance': 0.15,
        'price': 150,
        'desc': 'ꜰʀᴇᴇᴢɪɴɢ ꜱᴛᴏʀᴍ',
        'emoji': '❄️'
    },
    'thunder': {
        'name': '⚡ ᴛʜᴜɴᴅᴇʀ ꜱᴛʀɪᴋᴇ',
        'element': 'lightning',
        'damage': 38,
        'mana': 21,
        'level_req': 5,
        'crit_chance': 0.25,
        'price': 150,
        'desc': 'ᴅᴇᴠᴀꜱᴛᴀᴛɪɴɢ ʟɪɢʜᴛɴɪɴɢ',
        'emoji': '⚡'
    },

    # Tier 3
    'meteor': {
        'name': '☄️ ᴍᴇᴛᴇᴏʀ ꜱʜᴏᴡᴇʀ',
        'element': 'fire',
        'damage': 55,
        'mana': 35,
        'level_req': 10,
        'crit_chance': 0.20,
        'price': 300,
        'desc': 'ᴜʟᴛɪᴍᴀᴛᴇ ꜰɪʀᴇ ᴍᴀɢɪᴄ',
        'emoji': '☄️'
    },
    'glacier': {
        'name': '🧊 ɢʟᴀᴄɪᴇʀ ᴄʀᴀꜱʜ',
        'element': 'ice',
        'damage': 60,
        'mana': 38,
        'level_req': 10,
        'crit_chance': 0.18,
        'price': 300,
        'desc': 'ᴍᴀꜱꜱɪᴠᴇ ɪᴄᴇ ᴀᴛᴛᴀᴄᴋ',
        'emoji': '🧊'
    },
    'storm': {
        'name': '⛈️ ᴅɪᴠɪɴᴇ ꜱᴛᴏʀᴍ',
        'element': 'lightning',
        'damage': 65,
        'mana': 40,
        'level_req': 10,
        'crit_chance': 0.30,
        'price': 300,
        'desc': 'ɢᴏᴅ-ᴛɪᴇʀ ʟɪɢʜᴛɴɪɴɢ',
        'emoji': '⛈️'
    },

    # Special
    'holy': {
        'name': '✨ ʜᴏʟʏ ʟɪɢʜᴛ',
        'element': 'light',
        'damage': 45,
        'mana': 25,
        'level_req': 7,
        'crit_chance': 0.22,
        'price': 200,
        'desc': 'ᴘᴜʀɪꜰʏɪɴɢ ʟɪɢʜᴛ ʙᴇᴀᴍ',
        'emoji': '✨'
    },
    'shadow': {
        'name': '🌑 ꜱʜᴀᴅᴏᴡ ʙᴏʟᴛ',
        'element': 'dark',
        'damage': 50,
        'mana': 28,
        'level_req': 8,
        'crit_chance': 0.25,
        'price': 250,
        'desc': 'ᴅᴀʀᴋ ᴇɴᴇʀɢʏ ʙʟᴀꜱᴛ',
        'emoji': '🌑'
    },
    'void': {
        'name': '🕳️ ᴠᴏɪᴅ ᴅᴇꜱᴛʀᴜᴄᴛɪᴏɴ',
        'element': 'dark',
        'damage': 70,
        'mana': 45,
        'level_req': 15,
        'crit_chance': 0.28,
        'price': 500,
        'desc': 'ꜰᴏʀʙɪᴅᴅᴇɴ ᴅᴀʀᴋ ᴍᴀɢɪᴄ',
        'emoji': '🕳️'
    }
}

# Items
SHOP_ITEMS = {
    'health_potion': {
        'name': '🧪 ʜᴇᴀʟᴛʜ ᴘᴏᴛɪᴏɴ',
        'effect': 'heal',
        'value': 30,
        'price': 50,
        'desc': 'ʀᴇꜱᴛᴏʀᴇꜱ 30 ʜᴘ',
        'emoji': '🧪'
    },
    'mana_potion': {
        'name': '💙 ᴍᴀɴᴀ ᴘᴏᴛɪᴏɴ',
        'effect': 'mana',
        'value': 25,
        'price': 40,
        'desc': 'ʀᴇꜱᴛᴏʀᴇꜱ 25 ᴍᴀɴᴀ',
        'emoji': '💙'
    },
    'elixir': {
        'name': '⚗️ ɢʀᴀɴᴅ ᴇʟɪxɪʀ',
        'effect': 'both',
        'value': 50,
        'price': 100,
        'desc': 'ʀᴇꜱᴛᴏʀᴇꜱ 50 ʜᴘ & ᴍᴀɴᴀ',
        'emoji': '⚗️'
    },
    'shield_charm': {
        'name': '🛡️ ꜱʜɪᴇʟᴅ ᴄʜᴀʀᴍ',
        'effect': 'shield',
        'value': 20,
        'price': 60,
        'desc': 'ʙʟᴏᴄᴋꜱ 20 ᴅᴀᴍᴀɢᴇ',
        'emoji': '🛡️'
    }
}

# ------------------------
# HELPER FUNCTIONS
# ------------------------
async def get_wizard(user_id: int, first_name=None, username=None):
    """Get or create wizard profile"""
    wizard = await wizards_collection.find_one({'user_id': user_id})

    if not wizard:
        wizard = {
            'user_id': user_id,
            'first_name': first_name,
            'username': username,
            'level': 1,
            'xp': 0,
            'hp': BASE_HP,
            'max_hp': BASE_HP,
            'mana': BASE_MANA,
            'max_mana': BASE_MANA,
            'coins': 100,
            'wins': 0,
            'losses': 0,
            'spells': ['fireball', 'frost', 'spark'],
            'inventory': {},
            'last_spell_cast': 0,
            'last_daily': None,
            'clan': None,
            'achievements': [],
            'active_shield': 0
        }
        await wizards_collection.insert_one(wizard)
    else:
        update = {}
        if first_name and wizard.get('first_name') != first_name:
            update['first_name'] = first_name
        if username and wizard.get('username') != username:
            update['username'] = username
        if update:
            await wizards_collection.update_one({'user_id': user_id}, {'$set': update})
            wizard.update(update)

    return wizard

async def update_wizard(user_id: int, update_data: dict):
    """Update wizard data"""
    await wizards_collection.update_one({'user_id': user_id}, {'$set': update_data})

def calculate_damage(base_damage, attacker_level, defender_level, attacker_element, defender_element=None):
    """Calculate final damage"""
    damage = base_damage
    level_diff = attacker_level - defender_level
    damage += level_diff * 2

    if defender_element and ELEMENT_ADVANTAGE.get(attacker_element) == defender_element:
        damage = int(damage * 1.5)

    damage = int(damage * random.uniform(0.9, 1.1))
    return max(1, damage)

def check_level_up(xp: int, current_level: int) -> tuple:
    """Check if wizard levels up"""
    xp_needed = current_level * 100
    if xp >= xp_needed:
        return current_level + 1, True
    return current_level, False

def create_progress_bar(current: int, maximum: int, length: int = 10) -> str:
    """Create visual progress bar"""
    filled = int((current / maximum) * length)
    bar = '▰' * filled + '▱' * (length - filled)
    return bar

# ------------------------
# COMMAND: /starts - MAIN MENU
# ------------------------
async def start_wizard(update: Update, context: CallbackContext):
    """Wizard welcome menu"""
    # Handle both command and callback
    if update.callback_query:
        query = update.callback_query
        user = query.from_user
        is_callback = True
    else:
        user = update.effective_user
        is_callback = False

    wizard = await get_wizard(user.id, user.first_name, user.username)

    hp_bar = create_progress_bar(wizard['hp'], wizard['max_hp'])
    mana_bar = create_progress_bar(wizard['mana'], wizard['max_mana'])

    text = (
        f"✦━━━━━━━━━━━━━━━━━━━━✦\n"
        f"    ✨ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ꜱᴘᴇʟʟᴄᴀꜱᴛ ✨\n"
        f"✦━━━━━━━━━━━━━━━━━━━━✦\n\n"
        f"🔮 <b>ᴡɪᴢᴀʀᴅ ᴘʀᴏꜰɪʟᴇ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 {wizard['first_name']}\n"
        f"⭐ ʟᴇᴠᴇʟ {wizard['level']}\n\n"
        f"❤️ ʜᴘ: {wizard['hp']}/{wizard['max_hp']}\n"
        f"   {hp_bar}\n\n"
        f"💙 ᴍᴀɴᴀ: {wizard['mana']}/{wizard['max_mana']}\n"
        f"   {mana_bar}\n\n"
        f"💰 ᴄᴏɪɴꜱ: {wizard['coins']}\n"
        f"🏆 ᴡɪɴꜱ: {wizard['wins']} | ʟᴏꜱꜱᴇꜱ: {wizard['losses']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚡ ᴜꜱᴇ ʙᴜᴛᴛᴏɴꜱ ʙᴇʟᴏᴡ ᴛᴏ ɴᴀᴠɪɢᴀᴛᴇ"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🪄 ᴊᴏᴜʀɴᴇʏ", callback_data="menu:journey"),
            InlineKeyboardButton("📜 ꜱᴘᴇʟʟꜱ", callback_data="menu:spells")
        ],
        [
            InlineKeyboardButton("💰 ꜱʜᴏᴘ", callback_data="menu:shop"),
            InlineKeyboardButton("🎒 ɪᴛᴇᴍꜱ", callback_data="menu:inventory")
        ],
        [
            InlineKeyboardButton("⚔️ ᴅᴜᴇʟ", callback_data="menu:duel"),
            InlineKeyboardButton("🏆 ʀᴀɴᴋꜱ", callback_data="menu:rank")
        ],
        [
            InlineKeyboardButton("🎁 ᴅᴀɪʟʏ", callback_data="menu:daily"),
            InlineKeyboardButton("👤 ᴘʀᴏꜰɪʟᴇ", callback_data="menu:profile")
        ]
    ])

    if is_callback:
        await query.edit_message_text(
            text=text,
            parse_mode='HTML',
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            text=text,
            parse_mode='HTML',
            reply_markup=keyboard
        )

# ------------------------
# MENU CALLBACK HANDLER
# ------------------------
async def menu_callback(update: Update, context: CallbackContext):
    """Handle menu button clicks"""
    query = update.callback_query
    await query.answer()

    data = query.data.split(':')
    action = data[1] if len(data) > 1 else None

    user_id = query.from_user.id

    # Route to correct function based on action
    if action == "journey":
        await show_journey_menu(query, user_id)
    elif action == "spells":
        await show_spells_menu(query, user_id)
    elif action == "shop":
        await show_shop_menu(query, user_id)
    elif action == "inventory":
        await show_inventory_menu(query, user_id)
    elif action == "duel":
        await show_duel_info(query, user_id)
    elif action == "rank":
        await show_rankings(query)
    elif action == "daily":
        await claim_daily_reward(query, user_id)
    elif action == "profile":
        await show_profile(query, user_id)
    elif action == "main":
        # Back to main menu
        await start_wizard(update, context)

# ------------------------
# SHOW JOURNEY MENU
# ------------------------
async def show_journey_menu(query, user_id: int):
    """Show journey/commands info"""
    text = (
        f"✦━━━━━━━━━━━━━━━━━━━━✦\n"
        f"      🗺️ ʏᴏᴜʀ ᴊᴏᴜʀɴᴇʏ\n"
        f"✦━━━━━━━━━━━━━━━━━━━━✦\n\n"
        f"<b>Qᴜɪᴄᴋ ᴄᴏᴍᴍᴀɴᴅꜱ:</b>\n\n"
        f"⚔️ /cast [spell] - ᴀᴛᴛᴀᴄᴋ ꜱᴏᴍᴇᴏɴᴇ\n"
        f"   <i>ʀᴇᴘʟʏ ᴛᴏ ᴛʜᴇɪʀ ᴍᴇꜱꜱᴀɢᴇ</i>\n\n"
        f"💚 /heal - ʀᴇꜱᴛᴏʀᴇ ʜᴘ\n"
        f"🛡️ /shield - ʙʟᴏᴄᴋ ᴅᴀᴍᴀɢᴇ\n"
        f"🧪 /use [item] - ᴜꜱᴇ ᴘᴏᴛɪᴏɴ\n"
        f"⚔️ /duel - ᴄʜᴀʟʟᴇɴɢᴇ ᴘʟᴀʏᴇʀ\n\n"
        f"💡 <i>ᴛɪᴘ: ʀᴇᴘʟʏ ᴛᴏ ꜱᴏᴍᴇᴏɴᴇ'ꜱ ᴍᴇꜱꜱᴀɢᴇ\n"
        f"   ᴀɴᴅ ᴜꜱᴇ /cast fireball</i>"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="menu:main")]
    ])

    await query.edit_message_text(
        text=text,
        parse_mode='HTML',
        reply_markup=keyboard
    )

# ------------------------
# SHOW DUEL INFO
# ------------------------
async def show_duel_info(query, user_id: int):
    """Show duel information"""
    text = (
        f"✦━━━━━━━━━━━━━━━━━━━━✦\n"
        f"      ⚔️ ᴅᴜᴇʟ ᴀʀᴇɴᴀ\n"
        f"✦━━━━━━━━━━━━━━━━━━━━✦\n\n"
        f"🎯 <b>ʜᴏᴡ ᴛᴏ ᴅᴜᴇʟ:</b>\n\n"
        f"1️⃣ ʀᴇᴘʟʏ ᴛᴏ ꜱᴏᴍᴇᴏɴᴇ'ꜱ ᴍᴇꜱꜱᴀɢᴇ\n"
        f"2️⃣ ᴛʏᴘᴇ /duel\n"
        f"3️⃣ ᴡᴀɪᴛ ꜰᴏʀ ᴛʜᴇᴍ ᴛᴏ ᴀᴄᴄᴇᴘᴛ\n"
        f"4️⃣ ᴛᴀᴋᴇ ᴛᴜʀɴꜱ ᴄᴀꜱᴛɪɴɢ ꜱᴘᴇʟʟꜱ\n\n"
        f"⚡ ᴡɪɴɴᴇʀ ɢᴇᴛꜱ xᴘ & ᴄᴏɪɴꜱ!"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="menu:main")]
    ])

    await query.edit_message_text(
        text=text,
        parse_mode='HTML',
        reply_markup=keyboard
    )

# ------------------------
# SHOW SPELLS MENU
# ------------------------
async def show_spells_menu(query, user_id: int):
    """Show user's spellbook"""
    wizard = await get_wizard(user_id)

    text = (
        f"✦━━━━━━━━━━━━━━━━━━━━✦\n"
        f"      📜 ꜱᴘᴇʟʟʙᴏᴏᴋ\n"
        f"✦━━━━━━━━━━━━━━━━━━━━✦\n\n"
    )

    for spell_key in wizard.get('spells', []):
        spell = SPELLS.get(spell_key)
        if spell:
            text += (
                f"{spell['emoji']} <b>{spell['name']}</b>\n"
                f"   ⚔️ ᴅᴍɢ: {spell['damage']} | 💙 ᴍᴀɴᴀ: {spell['mana']}\n"
                f"   📖 {spell['desc']}\n\n"
            )

    text += f"\n💡 ᴜꜱᴇ: /cast [spell]\n   <i>ʀᴇᴘʟʏ ᴛᴏ ꜱᴏᴍᴇᴏɴᴇ'ꜱ ᴍᴇꜱꜱᴀɢᴇ</i>"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="menu:main")]
    ])

    await query.edit_message_text(
        text=text,
        parse_mode='HTML',
        reply_markup=keyboard
    )

# ------------------------
# SHOW SHOP MENU
# ------------------------
async def show_shop_menu(query, user_id: int):
    """Shop interface"""
    wizard = await get_wizard(user_id)

    text = (
        f"✦━━━━━━━━━━━━━━━━━━━━✦\n"
        f"    💰 ᴍᴀɢɪᴄ ꜱʜᴏᴘ 💰\n"
        f"✦━━━━━━━━━━━━━━━━━━━━━━━━✦\n\n"
        f"💎 ʏᴏᴜʀ ᴄᴏɪɴꜱ: <b>{wizard['coins']}</b>\n\n"
        f"<b>📦 ᴘᴏᴛɪᴏɴꜱ & ɪᴛᴇᴍꜱ:</b>\n"
    )

    buttons = []
    for item_key, item in SHOP_ITEMS.items():
        text += f"{item['emoji']} {item['name']} - {item['price']}💰\n"
        text += f"   {item['desc']}\n\n"
        buttons.append([InlineKeyboardButton(f"{item['emoji']} ʙᴜʏ {item['name'].split()[1]}", callback_data=f"buy:item:{item_key}")])

    text += "\n<b>📜 ᴀᴠᴀɪʟᴀʙʟᴇ ꜱᴘᴇʟʟꜱ:</b>\n"

    for spell_key, spell in SPELLS.items():
        if spell_key not in wizard.get('spells', []) and spell['price'] > 0:
            if wizard['level'] >= spell['level_req']:
                text += f"{spell['emoji']} {spell['name']} - {spell['price']}💰\n"
                text += f"   ⚔️ {spell['damage']} ᴅᴍɢ | ʟᴠʟ {spell['level_req']}\n\n"
                buttons.append([InlineKeyboardButton(f"{spell['emoji']} ʙᴜʏ {spell['name'].split()[1]}", callback_data=f"buy:spell:{spell_key}")])
            else:
                text += f"🔒 {spell['name']} - ʀᴇQᴜɪʀᴇꜱ ʟᴠʟ {spell['level_req']}\n\n"

    buttons.append([InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="menu:main")])
    keyboard = InlineKeyboardMarkup(buttons)

    await query.edit_message_text(
        text=text,
        parse_mode='HTML',
        reply_markup=keyboard
    )

# ------------------------
# BUY CALLBACK
# ------------------------
async def buy_callback(update: Update, context: CallbackContext):
    """Handle purchases"""
    query = update.callback_query
    await query.answer()

    data = query.data.split(':')
    buy_type = data[1]
    item_key = data[2]

    user_id = query.from_user.id
    wizard = await get_wizard(user_id)

    if buy_type == "item":
        item = SHOP_ITEMS.get(item_key)
        if not item:
            await query.answer("❌ ɪᴛᴇᴍ ɴᴏᴛ ꜰᴏᴜɴᴅ!", show_alert=True)
            return

        if wizard['coins'] < item['price']:
            await query.answer(f"💰 ɴᴏᴛ ᴇɴᴏᴜɢʜ ᴄᴏɪɴꜱ! ɴᴇᴇᴅ {item['price']}", show_alert=True)
            return

        inventory = wizard.get('inventory', {})
        inventory[item_key] = inventory.get(item_key, 0) + 1

        await update_wizard(user_id, {
            'coins': wizard['coins'] - item['price'],
            'inventory': inventory
        })

        await query.answer(f"✅ ʙᴏᴜɢʜᴛ {item['name']}!", show_alert=True)

        # Refresh wizard data and show updated shop
        wizard = await get_wizard(user_id)
        await show_shop_menu(query, user_id)

    elif buy_type == "spell":
        spell = SPELLS.get(item_key)
        if not spell:
            await query.answer("❌ ꜱᴘᴇʟʟ ɴᴏᴛ ꜰᴏᴜɴᴅ!", show_alert=True)
            return

        if item_key in wizard.get('spells', []):
            await query.answer("❌ ʏᴏᴜ ᴀʟʀᴇᴀᴅʏ ᴏᴡɴ ᴛʜɪꜱ!", show_alert=True)
            return

        if wizard['level'] < spell['level_req']:
            await query.answer(f"🔒 ʀᴇQᴜɪʀᴇꜱ ʟᴇᴠᴇʟ {spell['level_req']}!", show_alert=True)
            return

        if wizard['coins'] < spell['price']:
            await query.answer(f"💰 ɴᴏᴛ ᴇɴᴏᴜɢʜ ᴄᴏɪɴꜱ! ɴᴇᴇᴅ {spell['price']}", show_alert=True)
            return

        spells = wizard.get('spells', [])
        spells.append(item_key)

        await update_wizard(user_id, {
            'coins': wizard['coins'] - spell['price'],
            'spells': spells
        })

        await query.answer(f"✨ ʟᴇᴀʀɴᴇᴅ {spell['name']}!", show_alert=True)

        # Refresh wizard data and show updated shop
        wizard = await get_wizard(user_id)
        await show_shop_menu(query, user_id)

# ------------------------
# SHOW INVENTORY
# ------------------------
async def show_inventory_menu(query, user_id: int):
    """Show user inventory"""
    wizard = await get_wizard(user_id)
    inventory = wizard.get('inventory', {})

    text = (
        f"✦━━━━━━━━━━━━━━━━━━━━✦\n"
        f"      🎒 ɪɴᴠᴇɴᴛᴏʀʏ\n"
        f"✦━━━━━━━━━━━━━━━━━━━━✦\n\n"
        f"💰 ᴄᴏɪɴꜱ: {wizard['coins']}\n\n"
    )

    buttons = []

    if not inventory or sum(inventory.values()) == 0:
        text += "📦 ʏᴏᴜʀ ɪɴᴠᴇɴᴛᴏʀʏ ɪꜱ ᴇᴍᴘᴛʏ!\n\n"
    else:
        for item_key, count in inventory.items():
            item = SHOP_ITEMS.get(item_key)
            if item and count > 0:
                text += f"{item['emoji']} {item['name']} x{count}\n"
                text += f"   {item['desc']}\n\n"
                buttons.append([InlineKeyboardButton(f"ᴜꜱᴇ {item['emoji']} {item['name'].split()[1]}", callback_data=f"use:{item_key}")])

    text += "💡 ᴄʟɪᴄᴋ ʙᴜᴛᴛᴏɴꜱ ᴛᴏ ᴜꜱᴇ ɪᴛᴇᴍꜱ"

    buttons.append([InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="menu:main")])
    keyboard = InlineKeyboardMarkup(buttons)

    await query.edit_message_text(
        text=text,
        parse_mode='HTML',
        reply_markup=keyboard
    )

# ------------------------
# USE ITEM CALLBACK
# ------------------------
async def use_item_callback(update: Update, context: CallbackContext):
    """Handle item usage"""
    query = update.callback_query
    await query.answer()

    data = query.data.split(':')
    item_key = data[1]

    user_id = query.from_user.id
    wizard = await get_wizard(user_id)
    inventory = wizard.get('inventory', {})

    if item_key not in inventory or inventory[item_key] <= 0:
        await query.answer("❌ ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴛʜᴀᴛ ɪᴛᴇᴍ!", show_alert=True)
        return

    item = SHOP_ITEMS.get(item_key)
    if not item:
        await query.answer("❌ ɪɴᴠᴀʟɪᴅ ɪᴛᴇᴍ!", show_alert=True)
        return

    update_data = {}
    effect_text = ""

    if item['effect'] == 'heal':
        new_hp = min(wizard['max_hp'], wizard['hp'] + item['value'])
        healed = new_hp - wizard['hp']
        update_data['hp'] = new_hp
        effect_text = f"❤️ +{healed} ʜᴘ"

    elif item['effect'] == 'mana':
        new_mana = min(wizard['max_mana'], wizard['mana'] + item['value'])
        restored = new_mana - wizard['mana']
        update_data['mana'] = new_mana
        effect_text = f"💙 +{restored} ᴍᴀɴᴀ"

    elif item['effect'] == 'both':
        new_hp = min(wizard['max_hp'], wizard['hp'] + item['value'])
        new_mana = min(wizard['max_mana'], wizard['mana'] + item['value'])
        healed = new_hp - wizard['hp']
        restored = new_mana - wizard['mana']
        update_data['hp'] = new_hp
        update_data['mana'] = new_mana
        effect_text = f"❤️ +{healed} ʜᴘ | 💙 +{restored} ᴍᴀɴᴀ"

    elif item['effect'] == 'shield':
        update_data['active_shield'] = item['value']
        effect_text = f"🛡️ +{item['value']} ꜱʜɪᴇʟᴅ"

    inventory[item_key] -= 1
    if inventory[item_key] == 0:
        del inventory[item_key]

    update_data['inventory'] = inventory
    await update_wizard(user_id, update_data)

    await query.answer(f"✅ {effect_text}", show_alert=True)

    # Refresh and show updated inventory
    await show_inventory_menu(query, user_id)

# ------------------------
# SHOW RANKINGS
# ------------------------
async def show_rankings(query):
    """Show leaderboard"""
    top_wizards = await wizards_collection.find().sort([('level', -1), ('wins', -1)]).limit(10).to_list(length=10)

    text = (
        f"✦━━━━━━━━━━━━━━━━━━━━✦\n"
        f"      🏆 ʀᴀɴᴋɪɴɢꜱ\n"
        f"✦━━━━━━━━━━━━━━━━━━━━✦\n\n"
    )

    medals = ['🥇', '🥈', '🥉']

    for idx, wiz in enumerate(top_wizards, 1):
        medal = medals[idx-1] if idx <= 3 else f"{idx}."
        name = wiz.get('first_name', 'ᴜɴᴋɴᴏᴡɴ')
        level = wiz.get('level', 1)
        wins = wiz.get('wins', 0)

        text += f"{medal} <b>{name}</b>\n"
        text += f"   ⭐ ʟᴠʟ {level} | 🏆 {wins} ᴡɪɴꜱ\n\n"

    text += "💡 ᴋᴇᴇᴘ ʙᴀᴛᴛʟɪɴɢ ᴛᴏ ᴄʟɪᴍʙ!"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="menu:main")]
    ])

    await query.edit_message_text(
        text=text,
        parse_mode='HTML',
        reply_markup=keyboard
    )

# ------------------------
# CLAIM DAILY REWARD
# ------------------------
async def claim_daily_reward(query, user_id: int):
    """Claim daily reward"""
    wizard = await get_wizard(user_id)

    last_daily = wizard.get('last_daily')
    now = datetime.utcnow()

    if last_daily:
        last_date = datetime.fromisoformat(last_daily)
        if (now - last_date).days < 1:
            time_left = timedelta(days=1) - (now - last_date)
            hours = time_left.seconds // 3600
            minutes = (time_left.seconds % 3600) // 60
            await query.answer(f"⏰ ᴄᴏᴍᴇ ʙᴀᴄᴋ ɪɴ {hours}ʜ {minutes}ᴍ", show_alert=True)
            return

    await update_wizard(user_id, {
        'coins': wizard['coins'] + DAILY_BONUS_COINS,
        'xp': wizard['xp'] + DAILY_BONUS_XP,
        'last_daily': now.isoformat()
    })

    text = (
        f"✦━━━━━━━━━━━━━━━━━━━━✦\n"
        f"    🎁 ᴅᴀɪʟʏ ʀᴇᴡᴀʀᴅ\n"
        f"✦━━━━━━━━━━━━━━━━━━━━✦\n\n"
        f"✅ <b>ʀᴇᴡᴀʀᴅ ᴄʟᴀɪᴍᴇᴅ!</b>\n\n"
        f"💰 +{DAILY_BONUS_COINS} ᴄᴏɪɴꜱ\n"
        f"✨ +{DAILY_BONUS_XP} xᴘ\n\n"
        f"💎 ᴛᴏᴛᴀʟ ᴄᴏɪɴꜱ: {wizard['coins'] + DAILY_BONUS_COINS}\n"
        f"⭐ ᴛᴏᴛᴀʟ xᴘ: {wizard['xp'] + DAILY_BONUS_XP}"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="menu:main")]
    ])

    await query.edit_message_text(
        text=text,
        parse_mode='HTML',
        reply_markup=keyboard
    )

# ------------------------
# SHOW PROFILE
# ------------------------
async def show_profile(query, user_id: int):
    """Show detailed profile"""
    wizard = await get_wizard(user_id)

    total_battles = wizard['wins'] + wizard['losses']
    win_rate = (wizard['wins'] / total_battles * 100) if total_battles > 0 else 0

    xp_needed = wizard['level'] * 100
    xp_progress = (wizard['xp'] / xp_needed * 100) if xp_needed > 0 else 0

    hp_bar = create_progress_bar(wizard['hp'], wizard['max_hp'])
    mana_bar = create_progress_bar(wizard['mana'], wizard['max_mana'])
    xp_bar = create_progress_bar(int(xp_progress), 100)

    text = (
        f"✦━━━━━━━━━━━━━━━━━━━━✦\n"
        f"      👤 ᴘʀᴏꜰɪʟᴇ\n"
        f"✦━━━━━━━━━━━━━━━━━━━━✦\n\n"
        f"🧙 <b>{wizard['first_name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⭐ ʟᴇᴠᴇʟ: <b>{wizard['level']}</b>\n"
        f"✨ xᴘ: {wizard['xp']}/{xp_needed}\n"
        f"   {xp_bar} {xp_progress:.0f}%\n\n"
        f"❤️ ʜᴘ: {wizard['hp']}/{wizard['max_hp']}\n"
        f"   {hp_bar}\n\n"
        f"💙 ᴍᴀɴᴀ: {wizard['mana']}/{wizard['max_mana']}\n"
        f"   {mana_bar}\n\n"
        f"💰 ᴄᴏɪɴꜱ: <b>{wizard['coins']}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚔️ ʙᴀᴛᴛʟᴇꜱ: {total_battles}\n"
        f"🏆 ᴡɪɴꜱ: {wizard['wins']}\n"
        f"💀 ʟᴏꜱꜱᴇꜱ: {wizard['losses']}\n"
        f"📊 ᴡɪɴ ʀᴀᴛᴇ: {win_rate:.1f}%\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📜 ꜱᴘᴇʟʟꜱ: {len(wizard.get('spells', []))}\n"
        f"🎒 ɪᴛᴇᴍꜱ: {sum(wizard.get('inventory', {}).values())}"
    )

    if wizard.get('clan'):
        text += f"\n🏰 ᴄʟᴀɴ: {wizard['clan']}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="menu:main")]
    ])

    await query.edit_message_text(
        text=text,
        parse_mode='HTML',
        reply_markup=keyboard
    )

# ------------------------
# COMMAND: /cast [spell]
# ------------------------
async def cast_spell(update: Update, context: CallbackContext):
    """Cast spell at another user"""
    attacker_id = update.effective_user.id
    attacker = await get_wizard(attacker_id, update.effective_user.first_name, update.effective_user.username)

    # Check cooldown
    time_since_cast = time.time() - attacker.get('last_spell_cast', 0)
    if time_since_cast < SPELL_COOLDOWN:
        await update.message.reply_text(
            f"⏳ ꜱᴘᴇʟʟ ᴄᴏᴏʟᴅᴏᴡɴ! ᴡᴀɪᴛ {SPELL_COOLDOWN - int(time_since_cast)}ꜱ"
        )
        return

    if not context.args:
        await update.message.reply_text(
            "❌ ᴜꜱᴀɢᴇ: /cast [spell]\n"
            "💡 ʀᴇᴘʟʏ ᴛᴏ ꜱᴏᴍᴇᴏɴᴇ'ꜱ ᴍᴇꜱꜱᴀɢᴇ\n"
            "ᴇxᴀᴍᴘʟᴇ: /cast fireball"
        )
        return

    spell_key = context.args[0].lower()

    # Get target
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ ʀᴇᴘʟʏ ᴛᴏ ꜱᴏᴍᴇᴏɴᴇ'ꜱ ᴍᴇꜱꜱᴀɢᴇ ᴛᴏ ᴀᴛᴛᴀᴄᴋ!")
        return

    target_user = update.message.reply_to_message.from_user

    if target_user.id == attacker_id:
        await update.message.reply_text("❌ ʏᴏᴜ ᴄᴀɴ'ᴛ ᴀᴛᴛᴀᴄᴋ ʏᴏᴜʀꜱᴇʟꜰ!")
        return

    # Check spell
    if spell_key not in SPELLS:
        await update.message.reply_text(f"❌ ᴜɴᴋɴᴏᴡɴ ꜱᴘᴇʟʟ! ᴜꜱᴇ /starts ᴛᴏ ꜱᴇᴇ ʏᴏᴜʀ ꜱᴘᴇʟʟꜱ")
        return

    spell = SPELLS[spell_key]

    if spell_key not in attacker.get('spells', []):
        await update.message.reply_text(f"🔒 ʏᴏᴜ ᴅᴏɴ'ᴛ ᴏᴡɴ {spell['name']}!")
        return

    if attacker['level'] < spell['level_req']:
        await update.message.reply_text(f"❌ ʀᴇQᴜɪʀᴇꜱ ʟᴇᴠᴇʟ {spell['level_req']}!")
        return

    if attacker['mana'] < spell['mana']:
        await update.message.reply_text(f"💙 ɴᴏᴛ ᴇɴᴏᴜɢʜ ᴍᴀɴᴀ! ɴᴇᴇᴅ {spell['mana']}")
        return

    # Get defender
    defender = await get_wizard(target_user.id, target_user.first_name, target_user.username)

    # Calculate damage
    damage = calculate_damage(
        spell['damage'],
        attacker['level'],
        defender['level'],
        spell['element']
    )

    # Critical hit
    is_crit = random.random() < spell['crit_chance']
    if is_crit:
        damage = int(damage * 1.5)

    # Apply shield
    shield = defender.get('active_shield', 0)
    shield_text = ""
    if shield > 0:
        blocked = min(shield, damage)
        damage -= blocked
        await update_wizard(target_user.id, {'active_shield': shield - blocked})
        shield_text = f"🛡️ ꜱʜɪᴇʟᴅ ʙʟᴏᴄᴋᴇᴅ {blocked} ᴅᴍɢ!\n"

    # Apply damage
    new_hp = max(0, defender['hp'] - damage)
    await update_wizard(target_user.id, {'hp': new_hp})

    # Deduct mana
    await update_wizard(attacker_id, {
        'mana': attacker['mana'] - spell['mana'],
        'last_spell_cast': time.time()
    })

    # Award XP
    xp_gain = 5
    new_xp = attacker['xp'] + xp_gain
    new_level, leveled_up = check_level_up(new_xp, attacker['level'])

    if leveled_up:
        new_max_hp = BASE_HP + (new_level * 10)
        new_max_mana = BASE_MANA + (new_level * 5)
        await update_wizard(attacker_id, {
            'level': new_level,
            'xp': new_xp,
            'max_hp': new_max_hp,
            'max_mana': new_max_mana
        })
        level_text = f"\n\n✨ <b>ʟᴇᴠᴇʟ ᴜᴘ!</b> ɴᴏᴡ ʟᴇᴠᴇʟ {new_level}!"
    else:
        await update_wizard(attacker_id, {'xp': new_xp})
        level_text = ""

    # Build message
    crit_text = "💥 <b>ᴄʀɪᴛɪᴄᴀʟ ʜɪᴛ!</b>\n" if is_crit else ""

    hp_bar = create_progress_bar(new_hp, defender['max_hp'])

    battle_text = (
        f"✦━━━━━━━━━━━━━━━━━━━━✦\n"
        f"{crit_text}"
        f"🧙 <b>{attacker['first_name']}</b> ᴄᴀꜱᴛ {spell['name']}!\n\n"
        f"{shield_text}"
        f"⚔️ <b>{defender['first_name']}</b> ᴛᴏᴏᴋ <b>{damage}</b> ᴅᴍɢ!\n\n"
        f"❤️ ʜᴘ: {defender['hp']} → {new_hp}\n"
        f"   {hp_bar}\n\n"
        f"✨ +{xp_gain} xᴘ"
        f"{level_text}\n"
        f"✦━━━━━━━━━━━━━━━━━━━━✦"
    )

    # Check defeat
    if new_hp == 0:
        battle_text += f"\n\n💀 <b>{defender['first_name']} ʜᴀꜱ ʙᴇᴇɴ ᴅᴇꜰᴇᴀᴛᴇᴅ!</b>"
        await update_wizard(attacker_id, {'wins': attacker.get('wins', 0) + 1})
        await update_wizard(target_user.id, {
            'losses': defender.get('losses', 0) + 1,
            'hp': defender['max_hp']
        })
        gif = get_gif('victory')
    else:
        gif = get_gif(spell_key)

    # Send with GIF
    try:
        await context.bot.send_animation(
            chat_id=update.effective_chat.id,
            animation=gif,
            caption=battle_text,
            parse_mode='HTML',
            reply_to_message_id=update.message.message_id
        )
    except:
        await update.message.reply_text(battle_text, parse_mode='HTML')

# ------------------------
# COMMAND: /heal
# ------------------------
async def heal_cmd(update: Update, context: CallbackContext):
    """Heal yourself"""
    user_id = update.effective_user.id
    wizard = await get_wizard(user_id, update.effective_user.first_name, update.effective_user.username)

    heal_cost = 15
    heal_amount = 30

    if wizard['mana'] < heal_cost:
        await update.message.reply_text(f"💙 ɴᴏᴛ ᴇɴᴏᴜɢʜ ᴍᴀɴᴀ! ɴᴇᴇᴅ {heal_cost}")
        return

    if wizard['hp'] >= wizard['max_hp']:
        await update.message.reply_text("❤️ ʏᴏᴜ'ʀᴇ ᴀʟʀᴇᴀᴅʏ ᴀᴛ ꜰᴜʟʟ ʜᴘ!")
        return

    new_hp = min(wizard['max_hp'], wizard['hp'] + heal_amount)
    healed = new_hp - wizard['hp']

    await update_wizard(user_id, {
        'hp': new_hp,
        'mana': wizard['mana'] - heal_cost
    })

    hp_bar = create_progress_bar(new_hp, wizard['max_hp'])

    text = (
        f"✦━━━━━━━━━━━━━━━━━━━━✦\n"
        f"💚 <b>{wizard['first_name']}</b> ᴄᴀꜱᴛ ʜᴇᴀʟɪɴɢ ᴍᴀɢɪᴄ!\n\n"
        f"❤️ ʀᴇꜱᴛᴏʀᴇᴅ <b>{healed}</b> ʜᴘ\n\n"
        f"❤️ ʜᴘ: {wizard['hp']} → {new_hp}\n"
        f"   {hp_bar}\n\n"
        f"💙 ᴍᴀɴᴀ: {wizard['mana'] + heal_cost} → {wizard['mana'] - heal_cost}\n"
        f"✦━━━━━━━━━━━━━━━━━━━━✦"
    )

    gif = get_gif('heal')
    
    try:
        await context.bot.send_animation(
            chat_id=update.effective_chat.id,
            animation=gif,
            caption=text,
            parse_mode='HTML'
        )
    except:
        await update.message.reply_text(text, parse_mode='HTML')

# ------------------------
# COMMAND: /shield
# ------------------------
async def shield_cmd(update: Update, context: CallbackContext):
    """Activate shield"""
    user_id = update.effective_user.id
    wizard = await get_wizard(user_id, update.effective_user.first_name, update.effective_user.username)

    shield_cost = 12
    shield_amount = 25

    if wizard['mana'] < shield_cost:
        await update.message.reply_text(f"💙 ɴᴏᴛ ᴇɴᴏᴜɢʜ ᴍᴀɴᴀ! ɴᴇᴇᴅ {shield_cost}")
        return

    await update_wizard(user_id, {
        'active_shield': shield_amount,
        'mana': wizard['mana'] - shield_cost
    })

    text = (
        f"✦━━━━━━━━━━━━━━━━━━━━✦\n"
        f"🛡️ <b>{wizard['first_name']}</b> ꜱᴜᴍᴍᴏɴᴇᴅ ᴀ ꜱʜɪᴇʟᴅ!\n\n"
        f"🛡️ ꜱʜɪᴇʟᴅ: <b>{shield_amount}</b> ᴅᴍɢ ᴀʙꜱᴏʀᴘᴛɪᴏɴ\n\n"
        f"💙 ᴍᴀɴᴀ: {wizard['mana'] + shield_cost} → {wizard['mana'] - shield_cost}\n"
        f"✦━━━━━━━━━━━━━━━━━━━━✦"
    )

    gif = get_gif('shield')
    
    try:
        await context.bot.send_animation(
            chat_id=update.effective_chat.id,
            animation=gif,
            caption=text,
            parse_mode='HTML'
        )
    except:
        await update.message.reply_text(text, parse_mode='HTML')

# ------------------------
# COMMAND: /use [item]
# ------------------------
async def use_cmd(update: Update, context: CallbackContext):
    """Use item from inventory"""
    user_id = update.effective_user.id
    wizard = await get_wizard(user_id, update.effective_user.first_name, update.effective_user.username)

    if not context.args:
        await update.message.reply_text(
            "❌ ᴜꜱᴀɢᴇ: /use [item]\n"
            "ᴇxᴀᴍᴘʟᴇ: /use health_potion\n\n"
            "ᴏʀ ᴜꜱᴇ /starts → ɪɴᴠᴇɴᴛᴏʀʏ ʙᴜᴛᴛᴏɴ"
        )
        return

    item_key = context.args[0].lower()
    inventory = wizard.get('inventory', {})

    if item_key not in inventory or inventory[item_key] <= 0:
        await update.message.reply_text("❌ ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴛʜᴀᴛ ɪᴛᴇᴍ!")
        return

    item = SHOP_ITEMS.get(item_key)
    if not item:
        await update.message.reply_text("❌ ɪɴᴠᴀʟɪᴅ ɪᴛᴇᴍ!")
        return

    update_data = {}
    effect_text = ""

    if item['effect'] == 'heal':
        new_hp = min(wizard['max_hp'], wizard['hp'] + item['value'])
        healed = new_hp - wizard['hp']
        update_data['hp'] = new_hp
        effect_text = f"❤️ ʀᴇꜱᴛᴏʀᴇᴅ <b>{healed}</b> ʜᴘ\n❤️ ʜᴘ: {wizard['hp']} → {new_hp}"
        gif_key = 'heal'

    elif item['effect'] == 'mana':
        new_mana = min(wizard['max_mana'], wizard['mana'] + item['value'])
        restored = new_mana - wizard['mana']
        update_data['mana'] = new_mana
        effect_text = f"💙 ʀᴇꜱᴛᴏʀᴇᴅ <b>{restored}</b> ᴍᴀɴᴀ\n💙 ᴍᴀɴᴀ: {wizard['mana']} → {new_mana}"
        gif_key = 'heal'

    elif item['effect'] == 'both':
        new_hp = min(wizard['max_hp'], wizard['hp'] + item['value'])
        new_mana = min(wizard['max_mana'], wizard['mana'] + item['value'])
        healed = new_hp - wizard['hp']
        restored = new_mana - wizard['mana']
        update_data['hp'] = new_hp
        update_data['mana'] = new_mana
        effect_text = (
            f"❤️ ʀᴇꜱᴛᴏʀᴇᴅ <b>{healed}</b> ʜᴘ\n"
            f"💙 ʀᴇꜱᴛᴏʀᴇᴅ <b>{restored}</b> ᴍᴀɴᴀ\n"
            f"❤️ ʜᴘ: {wizard['hp']} → {new_hp}\n"
            f"💙 ᴍᴀɴᴀ: {wizard['mana']} → {new_mana}"
        )
        gif_key = 'heal'

    elif item['effect'] == 'shield':
        update_data['active_shield'] = item['value']
        effect_text = f"🛡️ ꜱʜɪᴇʟᴅ ᴀᴄᴛɪᴠᴀᴛᴇᴅ: <b>{item['value']}</b> ᴅᴍɢ"
        gif_key = 'shield'

    inventory[item_key] -= 1
    if inventory[item_key] == 0:
        del inventory[item_key]

    update_data['inventory'] = inventory
    await update_wizard(user_id, update_data)

    text = (
        f"✦━━━━━━━━━━━━━━━━━━━━✦\n"
        f"✅ <b>ᴜꜱᴇᴅ {item['name']}</b>\n\n"
        f"{effect_text}\n\n"
        f"📦 ʀᴇᴍᴀɪɴɪɴɢ: {inventory.get(item_key, 0)}x\n"
        f"✦━━━━━━━━━━━━━━━━━━━━✦"
    )

    await update.message.reply_text(text, parse_mode='HTML')

# ------------------------
# COMMAND: /duel
# ------------------------
async def duel_cmd(update: Update, context: CallbackContext):
    """Start duel challenge"""
    challenger_id = update.effective_user.id
    challenger = await get_wizard(challenger_id, update.effective_user.first_name, update.effective_user.username)

    if not update.message.reply_to_message:
        await update.message.reply_text("❌ ʀᴇᴘʟʏ ᴛᴏ ꜱᴏᴍᴇᴏɴᴇ'ꜱ ᴍᴇꜱꜱᴀɢᴇ ᴛᴏ ᴄʜᴀʟʟᴇɴɢᴇ!")
        return

    target_user = update.message.reply_to_message.from_user

    if target_user.id == challenger_id:
        await update.message.reply_text("❌ ʏᴏᴜ ᴄᴀɴ'ᴛ ᴅᴜᴇʟ ʏᴏᴜʀꜱᴇʟꜰ!")
        return

    opponent = await get_wizard(target_user.id, target_user.first_name, target_user.username)

    # Check existing duels
    existing_duel = await duels_collection.find_one({
        '$or': [
            {'challenger_id': challenger_id, 'status': {'$in': ['active', 'pending']}},
            {'opponent_id': challenger_id, 'status': {'$in': ['active', 'pending']}},
            {'challenger_id': opponent['user_id'], 'status': {'$in': ['active', 'pending']}},
            {'opponent_id': opponent['user_id'], 'status': {'$in': ['active', 'pending']}}
        ]
    })

    if existing_duel:
        await update.message.reply_text("⚔️ ᴏɴᴇ ᴏꜰ ʏᴏᴜ ɪꜱ ᴀʟʀᴇᴀᴅʏ ɪɴ ᴀ ᴅᴜᴇʟ!")
        return

    # Create duel
    duel_id = f"{challenger_id}_{opponent['user_id']}_{int(time.time())}"

    duel = {
        'duel_id': duel_id,
        'challenger_id': challenger_id,
        'opponent_id': opponent['user_id'],
        'status': 'pending',
        'created_at': time.time(),
        'chat_id': update.effective_chat.id
    }

    await duels_collection.insert_one(duel)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚔️ ᴀᴄᴄᴇᴘᴛ", callback_data=f"duel:accept:{duel_id}"),
            InlineKeyboardButton("❌ ᴅᴇᴄʟɪɴᴇ", callback_data=f"duel:decline:{duel_id}")
        ]
    ])

    text = (
        f"✦━━━━━━━━━━━━━━━━━━━━✦\n"
        f"    ⚔️ ᴅᴜᴇʟ ᴄʜᴀʟʟᴇɴɢᴇ!\n"
        f"✦━━━━━━━━━━━━━━━━━━━━✦\n\n"
        f"🧙 <b>{challenger['first_name']}</b> (ʟᴠʟ {challenger['level']})\n"
        f"        ᴠꜱ\n"
        f"🧙 <b>{opponent['first_name']}</b> (ʟᴠʟ {opponent['level']})\n\n"
        f"💬 <b>{opponent['first_name']}</b>, ᴅᴏ ʏᴏᴜ ᴀᴄᴄᴇᴘᴛ?"
    )

    gif = get_gif('duel')
    
    try:
        await context.bot.send_animation(
            chat_id=update.effective_chat.id,
            animation=gif,
            caption=text,
            parse_mode='HTML',
            reply_markup=keyboard
        )
    except:
        await update.message.reply_text(text, parse_mode='HTML', reply_markup=keyboard)

    # Auto-expire after 60s
    async def timeout_duel():
        await asyncio.sleep(60)
        duel_check = await duels_collection.find_one({'duel_id': duel_id})
        if duel_check and duel_check['status'] == 'pending':
            await duels_collection.update_one(
                {'duel_id': duel_id},
                {'$set': {'status': 'expired'}}
            )

    asyncio.create_task(timeout_duel())

# ------------------------
# DUEL CALLBACK
# ------------------------
async def duel_callback(update: Update, context: CallbackContext):
    """Handle duel responses"""
    query = update.callback_query
    await query.answer()

    data = query.data.split(':')
    action = data[1]
    duel_id = data[2]

    duel = await duels_collection.find_one({'duel_id': duel_id})

    if not duel or duel['status'] != 'pending':
        await query.answer("❌ ᴅᴜᴇʟ ɴᴏ ʟᴏɴɢᴇʀ ᴠᴀʟɪᴅ", show_alert=True)
        return

    if query.from_user.id != duel['opponent_id']:
        await query.answer("⚠️ ᴛʜɪꜱ ᴅᴜᴇʟ ɪꜱ ɴᴏᴛ ꜰᴏʀ ʏᴏᴜ!", show_alert=True)
        return

    if action == 'decline':
        await duels_collection.update_one(
            {'duel_id': duel_id},
            {'$set': {'status': 'declined'}}
        )

        await query.edit_message_caption(
            caption=query.message.caption + "\n\n❌ <b>ᴅᴜᴇʟ ᴅᴇᴄʟɪɴᴇᴅ</b>",
            parse_mode='HTML'
        )
        return

    if action == 'accept':
        await duels_collection.update_one(
            {'duel_id': duel_id},
            {'$set': {
                'status': 'active',
                'turn': duel['challenger_id'],
                'turn_start': time.time()
            }}
        )

        challenger = await get_wizard(duel['challenger_id'])
        opponent = await get_wizard(duel['opponent_id'])

        hp_bar_c = create_progress_bar(challenger['hp'], challenger['max_hp'])
        hp_bar_o = create_progress_bar(opponent['hp'], opponent['max_hp'])

        text = (
            f"✦━━━━━━━━━━━━━━━━━━━━✦\n"
            f"    ⚔️ ᴅᴜᴇʟ ꜱᴛᴀʀᴛᴇᴅ!\n"
            f"✦━━━━━━━━━━━━━━━━━━━━✦\n\n"
            f"🧙 <b>{challenger['first_name']}</b>\n"
            f"   ❤️ {challenger['hp']}/{challenger['max_hp']}\n"
            f"   {hp_bar_c}\n"
            f"   💙 {challenger['mana']}/{challenger['max_mana']}\n\n"
            f"🧙 <b>{opponent['first_name']}</b>\n"
            f"   ❤️ {opponent['hp']}/{opponent['max_hp']}\n"
            f"   {hp_bar_o}\n"
            f"   💙 {opponent['mana']}/{opponent['max_mana']}\n\n"
            f"🎯 <b>{challenger['first_name']}'ꜱ ᴛᴜʀɴ!</b>\n"
            f"💡 ᴜꜱᴇ: /cast [spell]"
        )

        await query.edit_message_caption(caption=text, parse_mode='HTML')

# ------------------------
# REGISTER HANDLERS
# ------------------------
def register_handlers():
    """Register all command and callback handlers"""
    # Command handlers
    application.add_handler(CommandHandler("starts", start_wizard, block=False))
    application.add_handler(CommandHandler("cast", cast_spell, block=False))
    application.add_handler(CommandHandler("heal", heal_cmd, block=False))
    application.add_handler(CommandHandler("shield", shield_cmd, block=False))
    application.add_handler(CommandHandler("use", use_cmd, block=False))
    application.add_handler(CommandHandler("duel", duel_cmd, block=False))

    # Callback handlers with specific patterns
    application.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^menu:", block=False))
    application.add_handler(CallbackQueryHandler(buy_callback, pattern=r"^buy:", block=False))
    application.add_handler(CallbackQueryHandler(use_item_callback, pattern=r"^use:", block=False))
    application.add_handler(CallbackQueryHandler(duel_callback, pattern=r"^duel:", block=False))

# Call register function
register_handlers()

# End of spellcast_futuristic.py