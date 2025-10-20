# modules/spellcast.py
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
SPELL_COOLDOWN = 3  # seconds between spell casts
DUEL_TIMEOUT = 120  # 2 minutes per turn
DAILY_BONUS_COINS = 50
DAILY_BONUS_XP = 20

# Elemental strengths (damage multipliers)
ELEMENT_ADVANTAGE = {
    'fire': 'ice',      # fire > ice
    'ice': 'lightning', # ice > lightning
    'lightning': 'fire',# lightning > fire
    'light': 'dark',    # light > dark
    'dark': 'light'     # dark > light (neutral)
}

# ------------------------
# GIF/ANIMATION LIBRARY
# ------------------------
SPELL_GIFS = {
    'fireball': [
        'https://media.giphy.com/media/xUA7b2mljEC39bwmqc/giphy.gif',
        'https://media.giphy.com/media/l0HlQXlQ3nHyLMvte/giphy.gif',
        'https://media.giphy.com/media/3oEdv5okG3TzMJ9pQY/giphy.gif'
    ],
    'frost': [
        'https://media.giphy.com/media/5nsiFjdgylfK3csZ5T/giphy.gif',
        'https://media.giphy.com/media/l0HlR3kHtkgpnTzRu/giphy.gif',
        'https://media.giphy.com/media/l0Iy67evoh5s2xXNe/giphy.gif'
    ],
    'spark': [
        'https://media.giphy.com/media/l0HlNQ03J5JxX6lva/giphy.gif',
        'https://media.giphy.com/media/26tOZ42Mg6pbTUPHW/giphy.gif',
        'https://media.giphy.com/media/xUOwGhOrYP0jP6iAy4/giphy.gif'
    ],
    'inferno': [
        'https://media.giphy.com/media/13HgwGsXF0aiGY/giphy.gif',
        'https://media.giphy.com/media/uPnKU86sFa2fm/giphy.gif'
    ],
    'blizzard': [
        'https://media.giphy.com/media/l0Hlvh1us2dpuNglO/giphy.gif',
        'https://media.giphy.com/media/l0HlNZXdJjRlHLV2o/giphy.gif'
    ],
    'thunder': [
        'https://media.giphy.com/media/xUA7aZeLE2e0P7Znz2/giphy.gif',
        'https://media.giphy.com/media/26BRuo6sLetdllPAQ/giphy.gif'
    ],
    'meteor': [
        'https://media.giphy.com/media/mq5y2jHRCAqMo/giphy.gif',
        'https://media.giphy.com/media/l0HlQXlQ3nHyLMvte/giphy.gif'
    ],
    'glacier': [
        'https://media.giphy.com/media/3oEjI105rmEC22CJFK/giphy.gif'
    ],
    'storm': [
        'https://media.giphy.com/media/xUOwGhOrYP0jP6iAy4/giphy.gif',
        'https://media.giphy.com/media/3oEdv22bKD3kPHkRLi/giphy.gif'
    ],
    'holy': [
        'https://media.giphy.com/media/VIPdgcooFJHtC/giphy.gif',
        'https://media.giphy.com/media/3o7btQ0NH6Kl8CxCN2/giphy.gif'
    ],
    'shadow': [
        'https://media.giphy.com/media/l0HlNaQ6gWfllcjDO/giphy.gif',
        'https://media.giphy.com/media/3o6Zt7R02Q62fxgChq/giphy.gif'
    ],
    'void': [
        'https://media.giphy.com/media/xUOwGhOrYP0jP6iAy4/giphy.gif',
        'https://media.giphy.com/media/l0HlGXKvGr1OYBdvO/giphy.gif'
    ],
    'heal': [
        'https://media.giphy.com/media/l0HlGXKvGr1OYBdvO/giphy.gif',
        'https://media.giphy.com/media/9rtpurjbqiqZXbBBet/giphy.gif'
    ],
    'shield': [
        'https://media.giphy.com/media/UO5elnTqo4vSg/giphy.gif',
        'https://media.giphy.com/media/3oEdv5okG3TzMJ9pQY/giphy.gif'
    ],
    'victory': [
        'https://media.giphy.com/media/g9582DNuQppxC/giphy.gif',
        'https://media.giphy.com/media/111ebonMs90YLu/giphy.gif'
    ],
    'defeat': [
        'https://media.giphy.com/media/d2lcHJTG5Tscg/giphy.gif',
        'https://media.giphy.com/media/3oEjHGr1Fhz0kyv8Ig/giphy.gif'
    ],
    'levelup': [
        'https://media.giphy.com/media/g9582DNuQppxC/giphy.gif',
        'https://media.giphy.com/media/LoCDk7fecj2dwCtSB3/giphy.gif'
    ],
    'shop': [
        'https://media.giphy.com/media/l0HlvtIPw42Qwt66c/giphy.gif',
        'https://media.giphy.com/media/xUOwGhOrYP0jP6iAy4/giphy.gif'
    ],
    'duel_start': [
        'https://media.giphy.com/media/l0HlPystfePnAI3G8/giphy.gif',
        'https://media.giphy.com/media/3oEjHLzm4BCF8zfPy0/giphy.gif'
    ]
}

# Fallback GIFs if specific spell not found
DEFAULT_ATTACK_GIF = 'https://media.giphy.com/media/3oEjHLzm4BCF8zfPy0/giphy.gif'
DEFAULT_HEAL_GIF = 'https://media.giphy.com/media/9rtpurjbqiqZXbBBet/giphy.gif'

def get_spell_gif(spell_key: str) -> str:
    """Get random GIF for a spell"""
    gifs = SPELL_GIFS.get(spell_key, [DEFAULT_ATTACK_GIF])
    return random.choice(gifs)

# ------------------------
# SPELL DATABASE
# ------------------------
SPELLS = {
    # Tier 1 - Starting Spells
    'fireball': {
        'name': '🔥 Fireball',
        'element': 'fire',
        'damage': 20,
        'mana': 10,
        'level_req': 1,
        'crit_chance': 0.15,
        'desc': 'Basic fire spell',
        'emoji': '🔥'
    },
    'frost': {
        'name': '❄️ Frost Shard',
        'element': 'ice',
        'damage': 18,
        'mana': 10,
        'level_req': 1,
        'crit_chance': 0.12,
        'desc': 'Freezing attack',
        'emoji': '❄️'
    },
    'spark': {
        'name': '⚡ Lightning Spark',
        'element': 'lightning',
        'damage': 22,
        'mana': 12,
        'level_req': 1,
        'crit_chance': 0.20,
        'desc': 'Quick electric strike',
        'emoji': '⚡'
    },
    
    # Tier 2 - Level 5+
    'inferno': {
        'name': '🔥 Inferno Blast',
        'element': 'fire',
        'damage': 35,
        'mana': 20,
        'level_req': 5,
        'crit_chance': 0.18,
        'desc': 'Powerful fire explosion',
        'emoji': '🔥'
    },
    'blizzard': {
        'name': '❄️ Blizzard',
        'element': 'ice',
        'damage': 40,
        'mana': 22,
        'level_req': 5,
        'crit_chance': 0.15,
        'desc': 'Freezing storm',
        'emoji': '❄️'
    },
    'thunder': {
        'name': '⚡ Thunder Strike',
        'element': 'lightning',
        'damage': 38,
        'mana': 21,
        'level_req': 5,
        'crit_chance': 0.25,
        'desc': 'Devastating lightning',
        'emoji': '⚡'
    },
    
    # Tier 3 - Level 10+
    'meteor': {
        'name': '☄️ Meteor Shower',
        'element': 'fire',
        'damage': 55,
        'mana': 35,
        'level_req': 10,
        'crit_chance': 0.20,
        'desc': 'Ultimate fire magic',
        'emoji': '☄️'
    },
    'glacier': {
        'name': '🧊 Glacier Crash',
        'element': 'ice',
        'damage': 60,
        'mana': 38,
        'level_req': 10,
        'crit_chance': 0.18,
        'desc': 'Massive ice attack',
        'emoji': '🧊'
    },
    'storm': {
        'name': '⛈️ Divine Storm',
        'element': 'lightning',
        'damage': 65,
        'mana': 40,
        'level_req': 10,
        'crit_chance': 0.30,
        'desc': 'God-tier lightning',
        'emoji': '⛈️'
    },
    
    # Special Spells
    'holy': {
        'name': '✨ Holy Light',
        'element': 'light',
        'damage': 45,
        'mana': 25,
        'level_req': 7,
        'crit_chance': 0.22,
        'desc': 'Purifying light beam',
        'emoji': '✨'
    },
    'shadow': {
        'name': '🌑 Shadow Bolt',
        'element': 'dark',
        'damage': 50,
        'mana': 28,
        'level_req': 8,
        'crit_chance': 0.25,
        'desc': 'Dark energy blast',
        'emoji': '🌑'
    },
    'void': {
        'name': '🕳️ Void Destruction',
        'element': 'dark',
        'damage': 70,
        'mana': 45,
        'level_req': 15,
        'crit_chance': 0.28,
        'desc': 'Forbidden dark magic',
        'emoji': '🕳️'
    }
}

# Items/Potions
SHOP_ITEMS = {
    'health_potion': {
        'name': '🧪 Health Potion',
        'effect': 'heal',
        'value': 30,
        'price': 50,
        'desc': 'Restores 30 HP',
        'emoji': '🧪'
    },
    'mana_potion': {
        'name': '💙 Mana Potion',
        'effect': 'mana',
        'value': 25,
        'price': 40,
        'desc': 'Restores 25 mana',
        'emoji': '💙'
    },
    'elixir': {
        'name': '⚗️ Grand Elixir',
        'effect': 'both',
        'value': 50,
        'price': 100,
        'desc': 'Restores 50 HP & Mana',
        'emoji': '⚗️'
    },
    'shield_charm': {
        'name': '🛡️ Shield Charm',
        'effect': 'shield',
        'value': 20,
        'price': 60,
        'desc': 'Blocks 20 damage',
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
    """Calculate final damage with elemental advantage and level scaling"""
    damage = base_damage
    
    # Level scaling
    level_diff = attacker_level - defender_level
    damage += level_diff * 2
    
    # Elemental advantage
    if defender_element and ELEMENT_ADVANTAGE.get(attacker_element) == defender_element:
        damage = int(damage * 1.5)  # 50% bonus
    
    # Random variance
    damage = int(damage * random.uniform(0.9, 1.1))
    
    return max(1, damage)  # Minimum 1 damage

def check_level_up(xp: int, current_level: int) -> tuple:
    """Check if wizard levels up. Returns (new_level, leveled_up)"""
    xp_needed = current_level * 100
    if xp >= xp_needed:
        return current_level + 1, True
    return current_level, False

async def send_animated_message(context: CallbackContext, chat_id: int, text: str, gif_url: str = None, reply_to_message_id: int = None):
    """Send message with GIF animation"""
    try:
        if gif_url:
            # Send GIF with caption
            await context.bot.send_animation(
                chat_id=chat_id,
                animation=gif_url,
                caption=text,
                parse_mode='HTML',
                reply_to_message_id=reply_to_message_id
            )
        else:
            # Text only
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode='HTML',
                reply_to_message_id=reply_to_message_id
            )
    except Exception as e:
        # Fallback to text if GIF fails
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='HTML',
            reply_to_message_id=reply_to_message_id
        )

# ------------------------
# COMMAND: /start (wizard profile)
# ------------------------
async def start_wizard(update: Update, context: CallbackContext):
    """Initialize wizard profile"""
    user = update.effective_user
    wizard = await get_wizard(user.id, user.first_name, user.username)
    
    text = (
        f"🧙‍♂️ <b>Welcome, {wizard['first_name']}!</b>\n\n"
        f"⭐ Level: {wizard['level']}\n"
        f"❤️ HP: {wizard['hp']}/{wizard['max_hp']}\n"
        f"💙 Mana: {wizard['mana']}/{wizard['max_mana']}\n"
        f"💰 Coins: {wizard['coins']}\n"
        f"🏆 Wins: {wizard['wins']} | Losses: {wizard['losses']}\n\n"
        f"📜 <b>Commands:</b>\n"
        f"/cast [spell] @user - Attack someone\n"
        f"/heal - Restore HP (costs mana)\n"
        f"/shield - Block incoming damage\n"
        f"/duel @user - Start turn-based duel\n"
        f"/spells - View your spells\n"
        f"/shop - Buy items & spells\n"
        f"/inventory - View items\n"
        f"/daily - Claim daily reward\n"
        f"/rank - Top wizards leaderboard"
    )
    
    gif = get_spell_gif('duel_start')
    await send_animated_message(context, update.effective_chat.id, text, gif)

# ------------------------
# COMMAND: /cast [spell] @user
# ------------------------
async def cast_spell(update: Update, context: CallbackContext):
    """Cast spell at another user"""
    attacker_id = update.effective_user.id
    attacker = await get_wizard(attacker_id, update.effective_user.first_name, update.effective_user.username)
    
    # Check cooldown
    time_since_cast = time.time() - attacker.get('last_spell_cast', 0)
    if time_since_cast < SPELL_COOLDOWN:
        await update.message.reply_text(
            f"⏳ Spell cooldown! Wait {SPELL_COOLDOWN - int(time_since_cast)} seconds."
        )
        return
    
    # Parse command
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Usage: /cast [spell] @username\nExample: /cast fireball @wizard"
        )
        return
    
    spell_key = context.args[0].lower()
    
    # Get target user
    target_user = None
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif update.message.entities:
        for entity in update.message.entities:
            if entity.type == "mention":
                username = update.message.text[entity.offset:entity.offset + entity.length].replace('@', '')
                # In real bot, you'd need to resolve username to user_id
                await update.message.reply_text("❌ Reply to a message or mention a user in chat!")
                return
    
    if not target_user or target_user.id == attacker_id:
        await update.message.reply_text("❌ Invalid target! Reply to someone's message or mention them.")
        return
    
    # Check spell exists
    if spell_key not in SPELLS:
        await update.message.reply_text(
            f"❌ Unknown spell! Use /spells to see available spells."
        )
        return
    
    spell = SPELLS[spell_key]
    
    # Check if user owns spell
    if spell_key not in attacker.get('spells', []):
        await update.message.reply_text(
            f"🔒 You don't own {spell['name']}! Buy it from /shop"
        )
        return
    
    # Check level requirement
    if attacker['level'] < spell['level_req']:
        await update.message.reply_text(
            f"❌ {spell['name']} requires level {spell['level_req']}!"
        )
        return
    
    # Check mana
    if attacker['mana'] < spell['mana']:
        await update.message.reply_text(
            f"💙 Not enough mana! Need {spell['mana']}, have {attacker['mana']}"
        )
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
    
    # Check critical hit
    is_crit = random.random() < spell['crit_chance']
    if is_crit:
        damage = int(damage * 1.5)
    
    # Apply shield
    shield = defender.get('active_shield', 0)
    if shield > 0:
        blocked = min(shield, damage)
        damage -= blocked
        await update_wizard(target_user.id, {'active_shield': shield - blocked})
        shield_text = f"🛡️ Shield blocked {blocked} damage!\n"
    else:
        shield_text = ""
    
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
        level_text = f"\n\n🎉 <b>LEVEL UP!</b> You're now level {new_level}!"
        level_gif = get_spell_gif('levelup')
    else:
        await update_wizard(attacker_id, {'xp': new_xp})
        level_text = ""
        level_gif = None
    
    # Build message
    crit_text = "💥 <b>CRITICAL HIT!</b>\n" if is_crit else ""
    
    battle_text = (
        f"{crit_text}"
        f"🧙 <b>{attacker['first_name']}</b> cast {spell['name']}!\n\n"
        f"{shield_text}"
        f"⚔️ <b>{defender['first_name']}</b> took <b>{damage}</b> damage!\n"
        f"❤️ HP: {defender['hp']} → {new_hp}\n"
        f"✨ +{xp_gain} XP"
        f"{level_text}"
    )
    
    # Check if defender is defeated
    if new_hp == 0:
        battle_text += f"\n\n💀 <b>{defender['first_name']} has been defeated!</b>"
        await update_wizard(attacker_id, {'wins': attacker.get('wins', 0) + 1})
        await update_wizard(target_user.id, {
            'losses': defender.get('losses', 0) + 1,
            'hp': defender['max_hp']  # Reset HP
        })
        gif = get_spell_gif('victory')
    else:
        gif = level_gif if level_gif else get_spell_gif(spell_key)
    
    await send_animated_message(
        context,
        update.effective_chat.id,
        battle_text,
        gif,
        update.message.message_id
    )

# ------------------------
# COMMAND: /heal
# ------------------------
async def heal_cmd(update: Update, context: CallbackContext):
    """Heal yourself using mana"""
    user_id = update.effective_user.id
    wizard = await get_wizard(user_id, update.effective_user.first_name, update.effective_user.username)
    
    heal_cost = 15  # mana cost
    heal_amount = 30
    
    if wizard['mana'] < heal_cost:
        await update.message.reply_text(
            f"💙 Not enough mana! Need {heal_cost}, have {wizard['mana']}"
        )
        return
    
    if wizard['hp'] >= wizard['max_hp']:
        await update.message.reply_text("❤️ You're already at full HP!")
        return
    
    # Heal
    new_hp = min(wizard['max_hp'], wizard['hp'] + heal_amount)
    healed = new_hp - wizard['hp']
    
    await update_wizard(user_id, {
        'hp': new_hp,
        'mana': wizard['mana'] - heal_cost
    })
    
    text = (
        f"💚 <b>{wizard['first_name']}</b> cast healing magic!\n\n"
        f"❤️ Restored <b>{healed}</b> HP\n"
        f"❤️ HP: {wizard['hp']} → {new_hp}\n"
        f"💙 Mana: {wizard['mana'] + heal_cost} → {wizard['mana'] - heal_cost}"
    )
    
    gif = get_spell_gif('heal')
    await send_animated_message(context, update.effective_chat.id, text, gif)

# ------------------------
# COMMAND: /shield
# ------------------------
async def shield_cmd(update: Update, context: CallbackContext):
    """Activate shield to block damage"""
    user_id = update.effective_user.id
    wizard = await get_wizard(user_id, update.effective_user.first_name, update.effective_user.username)
    
    shield_cost = 12
    shield_amount = 25
    
    if wizard['mana'] < shield_cost:
        await update.message.reply_text(
            f"💙 Not enough mana! Need {shield_cost}, have {wizard['mana']}"
        )
        return
    
    await update_wizard(user_id, {
        'active_shield': shield_amount,
        'mana': wizard['mana'] - shield_cost
    })
    
    text = (
        f"🛡️ <b>{wizard['first_name']}</b> summoned a magical shield!\n\n"
        f"🛡️ Shield: <b>{shield_amount}</b> damage absorption\n"
        f"💙 Mana: {wizard['mana'] + shield_cost} → {wizard['mana'] - shield_cost}"
    )
    
    gif = get_spell_gif('shield')
    await send_animated_message(context, update.effective_chat.id, text, gif)

# ------------------------
# COMMAND: /spells
# ------------------------
async def spells_cmd(update: Update, context: CallbackContext):
    """Show user's spells"""
    user_id = update.effective_user.id
    wizard = await get_wizard(user_id, update.effective_user.first_name, update.effective_user.username)
    
    text = f"📜 <b>{wizard['first_name']}'s Spellbook</b>\n\n"
    
    for spell_key in wizard.get('spells', []):
        spell = SPELLS.get(spell_key)
        if spell:
            text += (
                f"{spell['emoji']} <b>{spell['name']}</b>\n"
                f"   ⚔️ Damage: {spell['damage']} | 💙 Mana: {spell['mana']}\n"
                f"   📖 {spell['desc']}\n\n"
            )
    
    text += f"\n💡 Use: /cast [spell] @user"
    
    await update.message.reply_text(text, parse_mode='HTML')

# ------------------------
# COMMAND: /shop
# ------------------------
async def shop_cmd(update: Update, context: CallbackContext):
    """Show shop with items and spells"""
    user_id = update.effective_user.id
    wizard = await get_wizard(user_id, update.effective_user.first_name, update.effective_user.username)
    
    text = (
        f"🏪 <b>Magic Shop</b>\n"
        f"💰 Your coins: {wizard['coins']}\n\n"
        f"<b>📦 Items:</b>\n"
    )
    
    for item_key, item in SHOP_ITEMS.items():
        text += f"{item['emoji']} {item['name']} - {item['price']} coins\n"
        text += f"   {item['desc']}\n\n"
    
    text += "\n<b>📜 Spells (unlocked by level):</b>\n"
    
    for spell_key, spell in SPELLS.items():
        if spell_key not in wizard.get('spells', []):
            status = "🔒 Locked" if wizard['level'] < spell['level_req'] else "✅ Available"
            price = spell.get('price', 150)
            text += (
                f"{spell['emoji']} {spell['name']} - {price} coins | Lvl {spell['level_req']}\n"
                f"   ⚔️ {spell['damage']} dmg | {status}\n\n"
            )
    
    text += "\n💡 Use: /buy [item/spell]"
    
    gif = get_spell_gif('shop')
    await send_animated_message(context, update.effective_chat.id, text, gif)

# ------------------------
# COMMAND: /buy [item/spell]
# ------------------------
async def buy_cmd(update: Update, context: CallbackContext):
    """Buy items or spells from shop"""
    user_id = update.effective_user.id
    wizard = await get_wizard(user_id, update.effective_user.first_name, update.effective_user.username)
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /buy [item/spell]\nExample: /buy health_potion")
        return
    
    item_key = context.args[0].lower()
    
    # Check if it's an item
    if item_key in SHOP_ITEMS:
        item = SHOP_ITEMS[item_key]
        price = item['price']
        
        if wizard['coins'] < price:
            await update.message.reply_text(
                f"💰 Not enough coins! Need {price}, have {wizard['coins']}"
            )
            return
        
        # Purchase item
        inventory = wizard.get('inventory', {})
        inventory[item_key] = inventory.get(item_key, 0) + 1
        
        await update_wizard(user_id, {
            'coins': wizard['coins'] - price,
            'inventory': inventory
        })
        
        text = (
            f"✅ <b>Purchase successful!</b>\n\n"
            f"{item['emoji']} Bought <b>{item['name']}</b>\n"
            f"💰 Coins: {wizard['coins']} → {wizard['coins'] - price}\n"
            f"📦 Inventory: {inventory[item_key]}x {item['name']}"
        )
        
        gif = get_spell_gif('shop')
        await send_animated_message(context, update.effective_chat.id, text, gif)
        return
    
    # Check if it's a spell
    if item_key in SPELLS:
        spell = SPELLS[item_key]
        price = spell.get('price', 150)
        
        # Check if already owned
        if item_key in wizard.get('spells', []):
            await update.message.reply_text(f"❌ You already own {spell['name']}!")
            return
        
        # Check level requirement
        if wizard['level'] < spell['level_req']:
            await update.message.reply_text(
                f"🔒 {spell['name']} requires level {spell['level_req']}! You're level {wizard['level']}"
            )
            return
        
        if wizard['coins'] < price:
            await update.message.reply_text(
                f"💰 Not enough coins! Need {price}, have {wizard['coins']}"
            )
            return
        
        # Purchase spell
        spells = wizard.get('spells', [])
        spells.append(item_key)
        
        await update_wizard(user_id, {
            'coins': wizard['coins'] - price,
            'spells': spells
        })
        
        text = (
            f"✨ <b>New Spell Learned!</b>\n\n"
            f"{spell['emoji']} <b>{spell['name']}</b>\n"
            f"⚔️ Damage: {spell['damage']}\n"
            f"💙 Mana Cost: {spell['mana']}\n"
            f"📖 {spell['desc']}\n\n"
            f"💰 Coins: {wizard['coins']} → {wizard['coins'] - price}"
        )
        
        gif = get_spell_gif(item_key)
        await send_animated_message(context, update.effective_chat.id, text, gif)
        return
    
    await update.message.reply_text("❌ Item not found! Check /shop for available items.")

# ------------------------
# COMMAND: /inventory
# ------------------------
async def inventory_cmd(update: Update, context: CallbackContext):
    """Show user's inventory"""
    user_id = update.effective_user.id
    wizard = await get_wizard(user_id, update.effective_user.first_name, update.effective_user.username)
    
    inventory = wizard.get('inventory', {})
    
    text = (
        f"🎒 <b>{wizard['first_name']}'s Inventory</b>\n"
        f"💰 Coins: {wizard['coins']}\n\n"
    )
    
    if not inventory:
        text += "📦 Your inventory is empty!\n\n"
    else:
        for item_key, count in inventory.items():
            item = SHOP_ITEMS.get(item_key)
            if item:
                text += f"{item['emoji']} {item['name']} x{count}\n"
        text += "\n"
    
    text += "💡 Use: /use [item]"
    
    await update.message.reply_text(text, parse_mode='HTML')

# ------------------------
# COMMAND: /use [item]
# ------------------------
async def use_cmd(update: Update, context: CallbackContext):
    """Use an item from inventory"""
    user_id = update.effective_user.id
    wizard = await get_wizard(user_id, update.effective_user.first_name, update.effective_user.username)
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /use [item]\nExample: /use health_potion")
        return
    
    item_key = context.args[0].lower()
    inventory = wizard.get('inventory', {})
    
    if item_key not in inventory or inventory[item_key] <= 0:
        await update.message.reply_text("❌ You don't have that item!")
        return
    
    item = SHOP_ITEMS.get(item_key)
    if not item:
        await update.message.reply_text("❌ Invalid item!")
        return
    
    # Apply item effect
    update_data = {}
    effect_text = ""
    
    if item['effect'] == 'heal':
        new_hp = min(wizard['max_hp'], wizard['hp'] + item['value'])
        healed = new_hp - wizard['hp']
        update_data['hp'] = new_hp
        effect_text = f"❤️ Restored <b>{healed}</b> HP\n❤️ HP: {wizard['hp']} → {new_hp}"
        gif_key = 'heal'
    
    elif item['effect'] == 'mana':
        new_mana = min(wizard['max_mana'], wizard['mana'] + item['value'])
        restored = new_mana - wizard['mana']
        update_data['mana'] = new_mana
        effect_text = f"💙 Restored <b>{restored}</b> mana\n💙 Mana: {wizard['mana']} → {new_mana}"
        gif_key = 'heal'
    
    elif item['effect'] == 'both':
        new_hp = min(wizard['max_hp'], wizard['hp'] + item['value'])
        new_mana = min(wizard['max_mana'], wizard['mana'] + item['value'])
        healed = new_hp - wizard['hp']
        restored = new_mana - wizard['mana']
        update_data['hp'] = new_hp
        update_data['mana'] = new_mana
        effect_text = (
            f"❤️ Restored <b>{healed}</b> HP\n"
            f"💙 Restored <b>{restored}</b> mana\n"
            f"❤️ HP: {wizard['hp']} → {new_hp}\n"
            f"💙 Mana: {wizard['mana']} → {new_mana}"
        )
        gif_key = 'heal'
    
    elif item['effect'] == 'shield':
        update_data['active_shield'] = item['value']
        effect_text = f"🛡️ Shield activated: <b>{item['value']}</b> damage absorption"
        gif_key = 'shield'
    
    # Consume item
    inventory[item_key] -= 1
    if inventory[item_key] == 0:
        del inventory[item_key]
    
    update_data['inventory'] = inventory
    await update_wizard(user_id, update_data)
    
    text = (
        f"✅ <b>Used {item['name']}</b>\n\n"
        f"{effect_text}\n\n"
        f"📦 Remaining: {inventory.get(item_key, 0)}x"
    )
    
    gif = get_spell_gif(gif_key)
    await send_animated_message(context, update.effective_chat.id, text, gif)

# ------------------------
# COMMAND: /daily
# ------------------------
async def daily_cmd(update: Update, context: CallbackContext):
    """Claim daily reward"""
    user_id = update.effective_user.id
    wizard = await get_wizard(user_id, update.effective_user.first_name, update.effective_user.username)
    
    last_daily = wizard.get('last_daily')
    now = datetime.utcnow()
    
    if last_daily:
        last_date = datetime.fromisoformat(last_daily)
        if (now - last_date).days < 1:
            time_left = timedelta(days=1) - (now - last_date)
            hours = time_left.seconds // 3600
            minutes = (time_left.seconds % 3600) // 60
            await update.message.reply_text(
                f"⏰ Daily reward already claimed!\n"
                f"Come back in <b>{hours}h {minutes}m</b>",
                parse_mode='HTML'
            )
            return
    
    # Grant daily reward
    await update_wizard(user_id, {
        'coins': wizard['coins'] + DAILY_BONUS_COINS,
        'xp': wizard['xp'] + DAILY_BONUS_XP,
        'last_daily': now.isoformat()
    })
    
    text = (
        f"🎁 <b>Daily Reward Claimed!</b>\n\n"
        f"💰 +{DAILY_BONUS_COINS} coins\n"
        f"✨ +{DAILY_BONUS_XP} XP\n\n"
        f"💰 Total coins: {wizard['coins'] + DAILY_BONUS_COINS}\n"
        f"✨ Total XP: {wizard['xp'] + DAILY_BONUS_XP}"
    )
    
    gif = get_spell_gif('levelup')
    await send_animated_message(context, update.effective_chat.id, text, gif)

# ------------------------
# COMMAND: /rank
# ------------------------
async def rank_cmd(update: Update, context: CallbackContext):
    """Show top wizards leaderboard"""
    # Get top 10 wizards by level and wins
    top_wizards = await wizards_collection.find().sort([('level', -1), ('wins', -1)]).limit(10).to_list(length=10)
    
    text = "🏆 <b>TOP WIZARDS LEADERBOARD</b>\n\n"
    
    medals = ['🥇', '🥈', '🥉']
    
    for idx, wiz in enumerate(top_wizards, 1):
        medal = medals[idx-1] if idx <= 3 else f"{idx}."
        name = wiz.get('first_name', 'Unknown')
        level = wiz.get('level', 1)
        wins = wiz.get('wins', 0)
        
        text += f"{medal} <b>{name}</b> - Lvl {level} | {wins} wins\n"
    
    text += "\n💡 Keep battling to climb the ranks!"
    
    await update.message.reply_text(text, parse_mode='HTML')

# ------------------------
# COMMAND: /duel @user
# ------------------------
async def duel_cmd(update: Update, context: CallbackContext):
    """Start turn-based duel with another user"""
    challenger_id = update.effective_user.id
    challenger = await get_wizard(challenger_id, update.effective_user.first_name, update.effective_user.username)
    
    # Get target
    target_user = None
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    
    if not target_user or target_user.id == challenger_id:
        await update.message.reply_text("❌ Reply to someone's message to challenge them!")
        return
    
    opponent = await get_wizard(target_user.id, target_user.first_name, target_user.username)
    
    # Check if duel already exists
    existing_duel = await duels_collection.find_one({
        '$or': [
            {'challenger_id': challenger_id, 'status': 'active'},
            {'opponent_id': challenger_id, 'status': 'active'},
            {'challenger_id': opponent['user_id'], 'status': 'active'},
            {'opponent_id': opponent['user_id'], 'status': 'active'}
        ]
    })
    
    if existing_duel:
        await update.message.reply_text("⚔️ One of you is already in a duel!")
        return
    
    # Create duel invitation
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
    
    # Create accept/decline buttons
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚔️ Accept", callback_data=f"duel:accept:{duel_id}"),
            InlineKeyboardButton("❌ Decline", callback_data=f"duel:decline:{duel_id}")
        ]
    ])
    
    text = (
        f"⚔️ <b>DUEL CHALLENGE!</b>\n\n"
        f"🧙 <b>{challenger['first_name']}</b> (Lvl {challenger['level']})\n"
        f"      VS\n"
        f"🧙 <b>{opponent['first_name']}</b> (Lvl {opponent['level']})\n\n"
        f"💬 <b>{opponent['first_name']}</b>, do you accept?"
    )
    
    gif = get_spell_gif('duel_start')
    
    msg = await context.bot.send_animation(
        chat_id=update.effective_chat.id,
        animation=gif,
        caption=text,
        parse_mode='HTML',
        reply_markup=keyboard
    )
    
    # Set timeout for acceptance
    async def timeout_duel():
        await asyncio.sleep(60)  # 60 second timeout
        duel_check = await duels_collection.find_one({'duel_id': duel_id})
        if duel_check and duel_check['status'] == 'pending':
            await duels_collection.update_one(
                {'duel_id': duel_id},
                {'$set': {'status': 'expired'}}
            )
            try:
                await msg.edit_caption(
                    caption=f"{text}\n\n⏰ <b>Duel expired - no response</b>",
                    parse_mode='HTML'
                )
            except:
                pass
    
    asyncio.create_task(timeout_duel())

# ------------------------
# CALLBACK: Duel acceptance/decline
# ------------------------
async def duel_callback(update: Update, context: CallbackContext):
    """Handle duel callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split(':')
    action = data[1]
    duel_id = data[2]
    
    duel = await duels_collection.find_one({'duel_id': duel_id})
    
    if not duel or duel['status'] != 'pending':
        await query.edit_message_caption(
            caption=query.message.caption + "\n\n❌ <b>Duel no longer valid</b>",
            parse_mode='HTML'
        )
        return
    
    # Only opponent can respond
    if query.from_user.id != duel['opponent_id']:
        await query.answer("⚠️ This duel is not for you!", show_alert=True)
        return
    
    if action == 'decline':
        await duels_collection.update_one(
            {'duel_id': duel_id},
            {'$set': {'status': 'declined'}}
        )
        
        await query.edit_message_caption(
            caption=query.message.caption + "\n\n❌ <b>Duel declined</b>",
            parse_mode='HTML'
        )
        return
    
    if action == 'accept':
        # Start duel
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
        
        text = (
            f"⚔️ <b>DUEL STARTED!</b>\n\n"
            f"🧙 <b>{challenger['first_name']}</b>\n"
            f"   ❤️ {challenger['hp']}/{challenger['max_hp']} HP\n"
            f"   💙 {challenger['mana']}/{challenger['max_mana']} Mana\n\n"
            f"🧙 <b>{opponent['first_name']}</b>\n"
            f"   ❤️ {opponent['hp']}/{opponent['max_hp']} HP\n"
            f"   💙 {opponent['mana']}/{opponent['max_mana']} Mana\n\n"
            f"🎯 <b>{challenger['first_name']}'s turn!</b>\n"
            f"💡 Use: /cast [spell] in chat"
        )
        
        await query.edit_message_caption(
            caption=text,
            parse_mode='HTML'
        )

# ------------------------
# COMMAND: /profile
# ------------------------
async def profile_cmd(update: Update, context: CallbackContext):
    """Show detailed wizard profile"""
    user_id = update.effective_user.id
    wizard = await get_wizard(user_id, update.effective_user.first_name, update.effective_user.username)
    
    # Calculate win rate
    total_battles = wizard['wins'] + wizard['losses']
    win_rate = (wizard['wins'] / total_battles * 100) if total_battles > 0 else 0
    
    # XP progress
    xp_needed = wizard['level'] * 100
    xp_progress = (wizard['xp'] / xp_needed * 100) if xp_needed > 0 else 0
    
    text = (
        f"🧙‍♂️ <b>{wizard['first_name']}'s Profile</b>\n\n"
        f"⭐ Level: <b>{wizard['level']}</b>\n"
        f"✨ XP: {wizard['xp']}/{xp_needed} ({xp_progress:.1f}%)\n\n"
        f"❤️ HP: {wizard['hp']}/{wizard['max_hp']}\n"
        f"💙 Mana: {wizard['mana']}/{wizard['max_mana']}\n"
        f"💰 Coins: {wizard['coins']}\n\n"
        f"⚔️ Battles: {total_battles}\n"
        f"🏆 Wins: {wizard['wins']}\n"
        f"💀 Losses: {wizard['losses']}\n"
        f"📊 Win Rate: {win_rate:.1f}%\n\n"
        f"📜 Spells Owned: {len(wizard.get('spells', []))}\n"
        f"🎒 Items: {sum(wizard.get('inventory', {}).values())}"
    )
    
    if wizard.get('clan'):
        text += f"\n🏰 Clan: {wizard['clan']}"
    
    await update.message.reply_text(text, parse_mode='HTML')

# ------------------------
# REGISTER HANDLERS
# ------------------------
application.add_handler(CommandHandler("starts", start_wizard, block=False))
application.add_handler(CommandHandler("cast", cast_spell, block=False))
application.add_handler(CommandHandler("heal", heal_cmd, block=False))
application.add_handler(CommandHandler("shield", shield_cmd, block=False))
application.add_handler(CommandHandler("spells", spells_cmd, block=False))
application.add_handler(CommandHandler("sho", shop_cmd, block=False))
application.add_handler(CommandHandler("buy", buy_cmd, block=False))
application.add_handler(CommandHandler("inventory", inventory_cmd, block=False))
application.add_handler(CommandHandler("use", use_cmd, block=False))
application.add_handler(CommandHandler("daily", daily_cmd, block=False))
application.add_handler(CommandHandler("rank", rank_cmd, block=False))
application.add_handler(CommandHandler("duel", duel_cmd, block=False))
application.add_handler(CommandHandler("profile", profile_cmd, block=False))

application.add_handler(CallbackQueryHandler(duel_callback, pattern=r"^duel:", block=False))

# End of spellcast.py