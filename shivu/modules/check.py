import urllib.request
from html import escape
from cachetools import TTLCache
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from pyrogram import filters
from pyrogram import types as t

from shivu import application, sudo_users, collection, db, CHARA_CHANNEL_ID, user_collection
from shivu import shivuu as bot

Cache for frequently accessed characters

character_cache = TTLCache(maxsize=1000, ttl=300)
anime_cache = TTLCache(maxsize=500, ttl=600)

OWNER_ID = 8297659126

==================== UTILITY FUNCTIONS ====================

def to_small_caps(text):
"""Convert text to small caps"""
small_caps_map = {
'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ',
'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ',
's': 's', 't': 'ᴛ', 'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ғ', 'G': 'ɢ', 'H': 'ʜ', 'I': 'ɪ',
'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ', 'O': 'ᴏ', 'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ',
'S': 's', 'T': 'ᴛ', 'U': 'ᴜ', 'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x', 'Y': 'ʏ', 'Z': 'ᴢ',
'0': '0', '1': '1', '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9'
}
return ''.join(small_caps_map.get(c, c) for c in text)

Event emoji mapping

EVENT_EMOJI_MAP = {
'kimono': {'emoji': '👘', 'text': '👘 ᴋɪᴍᴏɴᴏ 👘'},
'winter': {'emoji': '☃️', 'text': '☃️ ᴡɪɴᴛᴇʀ ☃️'},
'bunny': {'emoji': '🐰', 'text': '🐰 ʙᴜɴɴʏ 🐰'},
'game': {'emoji': '🎮', 'text': '🎮 ɢᴀᴍᴇ 🎮'},
'christmas': {'emoji': '🎄', 'text': '🎄 ᴄʜʀɪsᴛᴍᴀs 🎄'},
'halloween': {'emoji': '🎃', 'text': '🎃 ʜᴀʟʟᴏᴡᴇᴇɴ 🎃'},
'summer': {'emoji': '🏖️', 'text': '🏖️ sᴜᴍᴍᴇʀ 🏖️'},
'maid': {'emoji': '🧹', 'text': '🧹 ᴍᴀɪᴅ 🧹'},
'saree': {'emoji': '🥻', 'text': '🥻 sᴀʀᴇᴇ 🥻'},
'monsoon': {'emoji': '☔', 'text': '☔ ᴍᴏɴsᴏᴏɴ ☔'},
'school': {'emoji': '🎒', 'text': '🎒 sᴄʜᴏᴏʟ 🎒'},
'tuxedo': {'emoji': '🎩', 'text': '🎩 ᴛᴜxᴇᴅᴏ 🎩'},
'duo': {'emoji': '👥', 'text': '👥 ᴅᴜᴏ 👥'},
'group': {'emoji': '🤝🏻', 'text': '🤝🏻 ɢʀᴏᴜᴘ 🤝🏻'},
'lord': {'emoji': '👑', 'text': '👑 ʟᴏʀᴅ 👑'},
'valentine': {'emoji': '💞', 'text': '💞 ᴠᴀʟᴇɴᴛɪɴᴇ 💞'}
}

def get_event_text(character):
"""Get event text from character data"""
event = character.get('event')
if event and isinstance(event, dict):
event_name = event.get('name', '').lower()
event_sign = event.get('sign', '')

Try to match with our mapping

for key, value in EVENT_EMOJI_MAP.items():    
    if key in event_name or value['emoji'] == event_sign:    
        return value['text']    
    
# If no match, return raw event data    
if event_name and event_sign:    
    return f"{event_sign} {to_small_caps(event_name)} {event_sign}"

return ""

def get_rarity_color(rarity):
"""Get color tag based on rarity"""
rarity_str = str(rarity).lower()
if '🟢' in rarity_str or 'common' in rarity_str:
return '🟢'
elif '🟣' in rarity_str or 'rare' in rarity_str:
return '🟣'
elif '🟡' in rarity_str or 'legendary' in rarity_str:
return '🟡'
elif '💮' in rarity_str or 'special' in rarity_str:
return '💮'
elif '🔮' in rarity_str or 'premium' in rarity_str:
return '🔮'
elif '🎗️' in rarity_str or 'supreme' in rarity_str:
return '🎗️'
elif '🧜' in rarity_str or 'mermaid' in rarity_str:
return '🧜🏻‍♀️'
return '⚪'

async def get_character_by_id(character_id):
"""Get character with caching"""
if character_id in character_cache:
return character_cache[character_id]

character = await collection.find_one({'id': character_id})
if character:
character_cache[character_id] = character
return character

async def get_global_count(character_id):
"""Get how many times character is grabbed globally"""
try:
count = await user_collection.count_documents({'characters.id': character_id})
return count
except Exception as e:
print(f"Error getting global count: {e}")
return 0

def format_character_card(character, global_count=None, show_share=True):
"""Format character information as anime card"""
char_id = character.get('id', 'Unknown')
char_name = character.get('name', 'Unknown')
char_anime = character.get('anime', 'Unknown')
char_rarity = character.get('rarity', '🟢 Common')

Extract rarity parts

if isinstance(char_rarity, str):
rarity_parts = char_rarity.split(' ', 1)
rarity_emoji = rarity_parts[0] if len(rarity_parts) > 0 else '🟢'
rarity_text = rarity_parts[1] if len(rarity_parts) > 1 else 'Common'
else:
rarity_emoji = '🟢'
rarity_text = 'Common'

Get event

event_text = get_event_text(character)

Build caption

caption = f"""<b>╭━━━━━━━━━━━━━━━━━╮</b>

<b>┃  🎴 {to_small_caps('character card')}  ┃</b>
<b>╰━━━━━━━━━━━━━━━━━╯</b>

<b>🆔 {to_small_caps('id')}</b> <code>{char_id}</code>
<b>✨ {to_small_caps('name')}</b> <code>{escape(char_name)}</code>
<b>📺 {to_small_caps('anime')}</b> <code>{escape(char_anime)}</code>
<b>{rarity_emoji} {to_small_caps('rarity')}</b> <code>{to_small_caps(rarity_text)}</code>"""

if event_text:
caption += f"\n<b>🎪 {to_small_caps('event')}</b> {event_text}"

if global_count is not None:
caption += f"\n\n<b>🌍 {to_small_caps('globally grabbed')}</b> <code>{global_count}x</code>"

Add placeholder lore

caption += f"\n\n<b>━━━━━━━━━━━━━━━━━</b>"
caption += f"\n<i>{to_small_caps('a precious character waiting to join your collection')}</i>"

return caption

==================== /CHECK COMMAND ====================

async def check_character(update: Update, context: CallbackContext) -> None:
"""Check character information by ID"""
try:
args = context.args
if len(args) != 1:
await update.message.reply_text(
f"<b>{to_small_caps('incorrect format')}</b>\n\n"
f"{to_small_caps('usage')} <code>/check character_id</code>\n"
f"{to_small_caps('example')} <code>/check 01</code>",
parse_mode='HTML'
)
return

character_id = args[0]
character = await get_character_by_id(character_id)

if not character:    
    await update.message.reply_text(    
        f"<b>❌ {to_small_caps('character not found')}</b>\n\n"    
        f"{to_small_caps('id')} <code>{character_id}</code> {to_small_caps('does not exist')}",    
        parse_mode='HTML'    
    )    
    return    
    
global_count = await get_global_count(character_id)    
caption = format_character_card(character, global_count)    
    
# Create inline keyboard    
keyboard = [    
    [    
        InlineKeyboardButton(    
            f"🏆 {to_small_caps('top owners')}",     
            callback_data=f"top_owners_{character_id}"    
        ),    
        InlineKeyboardButton(    
            f"📊 {to_small_caps('stats')}",     
            callback_data=f"char_stats_{character_id}"    
        )    
    ],    
    [    
        InlineKeyboardButton(    
            f"🔗 {to_small_caps('share character')}",     
            url=f"https://t.me/share/url?url=Check out this character: /check {character_id}"    
        )    
    ]    
]    
    
await context.bot.send_photo(    
    chat_id=update.effective_chat.id,    
    photo=character['img_url'],    
    caption=caption,    
    parse_mode='HTML',    
    reply_markup=InlineKeyboardMarkup(keyboard)    
)

except Exception as e:
print(f"Error in check_character: {e}")
await update.message.reply_text(
f"<b>❌ {to_small_caps('error')}</b>\n{escape(str(e))}",
parse_mode='HTML'
)

==================== /FINDCHAR COMMAND ====================

async def find_character(update: Update, context: CallbackContext) -> None:
"""Find character by name"""
try:
if not context.args:
await update.message.reply_text(
f"<b>{to_small_caps('usage')}</b> <code>/findchar name</code>\n"
f"{to_small_caps('example')} <code>/findchar naruto</code>",
parse_mode='HTML'
)
return

char_name = ' '.join(context.args)

# Search characters    
characters = await collection.find({    
    'name': {'$regex': char_name, '$options': 'i'}    
}).limit(10).to_list(length=10)    
    
if not characters:    
    await update.message.reply_text(    
        f"<b>❌ {to_small_caps('no characters found with name')}</b> <code>{escape(char_name)}</code>",    
        parse_mode='HTML'    
    )    
    return    
    
# Build response    
response = f"<b>🔍 {to_small_caps('search results for')}</b> <code>{escape(char_name)}</code>\n\n"    
    
for char in characters[:10]:    
    rarity_emoji = get_rarity_color(char.get('rarity', ''))    
    response += (    
        f"{rarity_emoji} <code>{char.get('id', '??')}</code> "    
        f"<b>{escape(char.get('name', 'Unknown'))}</b>\n"    
        f"   ↳ {to_small_caps('from')} <i>{escape(char.get('anime', 'Unknown'))}</i>\n\n"    
    )    
    
if len(characters) == 10:    
    response += f"\n<i>{to_small_caps('showing first 10 results')}</i>"    
    
await update.message.reply_text(response, parse_mode='HTML')

except Exception as e:
print(f"Error in find_character: {e}")
await update.message.reply_text(
f"<b>❌ {to_small_caps('error')}</b> {escape(str(e))}",
parse_mode='HTML'
)

==================== /ANI COMMAND (PYROGRAM) ====================

@bot.on_message(filters.command(["anime"]))
async def find_anime(_, message: t.Message):
"""Find all characters from an anime with pagination"""
try:
if len(message.command) < 2:
return await message.reply_text(
f"<b>{to_small_caps('usage')}</b> <code>/ani anime_name</code>\n"
f"{to_small_caps('example')} <code>/ani naruto</code>",
quote=True
)

anime_name = " ".join(message.command[1:])

# Check cache    
cache_key = f"anime_{anime_name.lower()}"    
if cache_key in anime_cache:    
    characters = anime_cache[cache_key]    
else:    
    characters = await collection.find({    
        'anime': {'$regex': anime_name, '$options': 'i'}    
    }).to_list(length=None)    
    anime_cache[cache_key] = characters    

if not characters:    
    return await message.reply_text(    
        f"<b>❌ {to_small_caps('no characters found from anime')}</b> <code>{escape(anime_name)}</code>",    
        quote=True    
    )    

# Remove duplicates by name    
seen_names = set()    
unique_chars = []    
for char in characters:    
    char_name = char.get('name', '')    
    if char_name and char_name not in seen_names:    
        seen_names.add(char_name)    
        unique_chars.append(char)    

# Build response with pagination    
page_size = 20    
total_chars = len(unique_chars)    
    
response = f"<b>📺 {to_small_caps('characters from')}</b> <code>{escape(anime_name)}</code>\n"    
response += f"<b>{to_small_caps('total found')}</b> <code>{total_chars}</code>\n\n"    

for i, char in enumerate(unique_chars[:page_size], 1):    
    rarity_emoji = get_rarity_color(char.get('rarity', ''))    
    response += (    
        f"{i}. {rarity_emoji} <code>{char.get('id', '??')}</code> "    
        f"<b>{escape(char.get('name', 'Unknown'))}</b>\n"    
    )    

if total_chars > page_size:    
    response += f"\n<i>{to_small_caps('showing first')} {page_size} {to_small_caps('of')} {total_chars}</i>"    

await message.reply_text(response, quote=True)

except Exception as e:
print(f"Error in find_anime: {e}")
await message.reply_text(
f"<b>❌ {to_small_caps('error')}</b> {escape(str(e))}",
quote=True
)

==================== /IK COMMAND (PYROGRAM) ====================

async def get_users_by_character(character_id):
"""Get all users who own a character"""
try:
cursor = user_collection.find(
{'characters.id': character_id},
{
'_id': 0,
'id': 1,
'first_name': 1,
'username': 1,
'characters': 1
}
)
users = await cursor.to_list(length=None)

Count how many times each user has this character

user_data = []    
for user in users:    
    count = sum(1 for c in user.get('characters', []) if c.get('id') == character_id)    
    if count > 0:    
        user_data.append({    
            'id': user.get('id'),    
            'first_name': user.get('first_name', 'Unknown'),    
            'username': user.get('username'),    
            'count': count    
        })    
    
return user_data

except Exception as e:
print(f"Failed to get users by character: {e}")
return []

@bot.on_message(filters.command(["pfind"]))
async def find_users_with_character(_, message: t.Message):
"""Find all users who have a specific character"""
try:
if len(message.command) < 2:
await message.reply_text(
f"<b>{to_small_caps('usage')}</b> <code>/ik character_id</code>",
quote=True
)
return

character_id = message.command[1]

# Get character info    
character = await get_character_by_id(character_id)    
if not character:    
    await message.reply_text(    
        f"<b>❌ {to_small_caps('character not found')}</b> <code>{character_id}</code>",    
        quote=True    
    )    
    return    
    
users = await get_users_by_character(character_id)    

if not users:    
    await message.reply_text(    
        f"<b>{to_small_caps('no users found with character')}</b> <code>{character_id}</code>",    
        quote=True    
    )    
    return    
    
# Sort by count    
users.sort(key=lambda x: x['count'], reverse=True)    
    
response = f"<b>👥 {to_small_caps('users with character')}</b> <code>{character_id}</code>\n"    
response += f"<b>✨ {escape(character.get('name', 'Unknown'))}</b>\n\n"    
    
for i, user in enumerate(users[:50], 1):    
    user_id = user['id']    
    name = user['first_name']    
    username = user.get('username')    
    count = user['count']    
        
    user_link = f"<a href='tg://user?id={user_id}'>{escape(name)}</a>"    
    if username:    
        user_link += f" (@{escape(username)})"    
        
    response += f"{i}. {user_link} <code>x{count}</code>\n"    
    
if len(users) > 50:    
    response += f"\n<i>{to_small_caps('showing top 50 of')} {len(users)}</i>"    
    
await message.reply_text(response, quote=True)

except Exception as e:
print(f"Error in find_users_with_character: {e}")
await message.reply_text(
f"<b>❌ {to_small_caps('error')}</b> {escape(str(e))}",
quote=True
)

==================== CALLBACK HANDLERS ====================

async def handle_top_owners(update: Update, context: CallbackContext) -> None:
"""Show top owners of a character"""
query = update.callback_query
await query.answer()

try:
character_id = query.data.split('_')[2]
users = await get_users_by_character(character_id)

if not users:    
    await query.answer(    
        to_small_caps("no one owns this character yet"),    
        show_alert=True    
    )    
    return    
    
# Sort by count    
users.sort(key=lambda x: x['count'], reverse=True)    
    
# Build message    
response = f"<b>🏆 {to_small_caps('top 10 owners')}</b>\n\n"    
    
for i, user in enumerate(users[:10], 1):    
    user_id = user['id']    
    name = user['first_name']    
    username = user.get('username')    
    count = user['count']    
        
    medal = ""    
    if i == 1:    
        medal = "🥇"    
    elif i == 2:    
        medal = "🥈"    
    elif i == 3:    
        medal = "🥉"    
    else:    
        medal = f"{i}."    
        
    user_link = f"<a href='tg://user?id={user_id}'>{escape(name)}</a>"    
    if username:    
        user_link += f" (@{escape(username)})"    
        
    response += f"{medal} {user_link} <code>x{count}</code>\n"    
    
await query.answer(response[:200], show_alert=True)

except Exception as e:
print(f"Error showing top owners: {e}")
await query.answer(to_small_caps("error loading owners"), show_alert=True)

async def handle_char_stats(update: Update, context: CallbackContext) -> None:
"""Show character statistics"""
query = update.callback_query
await query.answer()

try:
character_id = query.data.split('_')[2]
character = await get_character_by_id(character_id)

if not character:    
    await query.answer(to_small_caps("character not found"), show_alert=True)    
    return    
    
global_count = await get_global_count(character_id)    
users = await get_users_by_character(character_id)    
unique_owners = len(users)    
    
stats = (    
    f"📊 {to_small_caps('statistics')}\n\n"    
    f"🌍 {to_small_caps('total grabbed')} {global_count}\n"    
    f"👥 {to_small_caps('unique owners')} {unique_owners}\n"    
    f"📈 {to_small_caps('avg per user')} {global_count/unique_owners if unique_owners > 0 else 0:.1f}"    
)    
    
await query.answer(stats, show_alert=True)

except Exception as e:
print(f"Error showing stats: {e}")
await query.answer(to_small_caps("error loading stats"), show_alert=True)

==================== HANDLER REGISTRATION ====================

Telegram handlers

application.add_handler(CommandHandler('check', check_character, block=False))
application.add_handler(CommandHandler('find', find_character, block=False))
application.add_handler(CallbackQueryHandler(handle_top_owners, pattern=r'^top_owners_', block=False))
application.add_handler(CallbackQueryHandler(handle_char_stats, pattern=r'^char_stats_', block=False))
