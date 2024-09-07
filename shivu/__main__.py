import importlib
import time
import random
import re
import asyncio
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, filters, Application, CallbackQueryHandler

from shivu import collection, top_global_groups_collection, group_user_totals_collection, user_collection, user_totals_collection, shivuu 
from shivu import LOGGER, set_on_data, set_off_data
from shivu.modules import ALL_MODULES

locks = {}
message_counters = {}
spam_counters = {}
last_characters = {}
sent_characters = {}
first_correct_guesses = {}
message_counts = {}

for module_name in ALL_MODULES:
    importlib.import_module("shivu.modules." + module_name)

last_user = {}
warned_users = {}
ran_away_count = {}
archived_characters = {}

def escape_markdown(text):
    escape_chars = r'\*_`\\~>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)

async def ran_away(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    if chat_id in last_characters:
        character_data = last_characters[chat_id]
        character_name = character_data['name']
        ran_away_count[chat_id] = ran_away_count.get(chat_id, 0) + 1
        
        if ran_away_count[chat_id] > 15:
            if chat_id not in first_correct_guesses:
                message_text = f"Ohh No!! [{character_name}] Has Been Ran Away From Your Chat Store His/Her Name For Next Time"
                await context.bot.send_message(chat_id=chat_id, text=message_text)
            del ran_away_count[chat_id]
            del last_characters[chat_id]

async def message_counter(update: Update, context: CallbackContext) -> None:
    chat_id = str(update.effective_chat.id)
    user = update.effective_user
    if user is None or user.is_bot:
        return  # Skip if the effective user is None or a bot
    user_id = user.id

    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()
    async with locks[chat_id]:
        chat_frequency = await user_totals_collection.find_one({'chat_id': chat_id})
        message_frequency = chat_frequency.get('message_frequency', 100) if chat_frequency else 100

        if chat_id in last_user and last_user[chat_id]['user_id'] == user_id:
            last_user[chat_id]['count'] += 1
            if last_user[chat_id]['count'] >= 10:
                if user_id in warned_users and time.time() - warned_users[user_id] < 600:
                    return
                await update.message.reply_text(f"ᴅᴏɴ'ᴛ 𝗌ᴘᴀᴍ {update.effective_user.first_name}...\n *ʏᴏᴜʀ ᴍᴇꜱꜱᴀɢᴇꜱ ᴡɪʟʟ ʙᴇ ɪɢɴᴏʀᴇᴅ ғᴏʀ 𝟷𝟶 ᴍɪɴᴜᴛᴇs.. ....!!*", parse_mode="Markdown")
                warned_users[user_id] = time.time()
                return
        else:
            last_user[chat_id] = {'user_id': user_id, 'count': 1}

        message_counts[chat_id] = message_counts.get(chat_id, 0) + 1

        if message_counts[chat_id] % message_frequency == 0:
            await send_image(update, context)
            message_counts[chat_id] = 0

async def send_image(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    all_characters = list(await collection.find({}).to_list(length=None))
    
    if chat_id not in sent_characters:
        sent_characters[chat_id] = []

    rarity_percentages = {
        "🟢 Common": 50,
        "🟣 Rare": 30,
        "🟡 Legendary": 10,
        "💮 Special Edition": 0.5,
        "🔮 Premium Edition": 0.2,
        "🎗️ Supreme": 0.1,
    }

    weighted_characters = [
        c for c in all_characters if 'rarity' in c and rarity_active.get(c['rarity'], False)
        for _ in range(int(100 * rarity_percentages.get(c['rarity'], 0)))
    ]

    if not weighted_characters:
        await update.message.reply_text('No active characters available to send.')
        return

    character = random.choice(weighted_characters)
    sent_characters[chat_id].append(character['id'])
    last_characters[chat_id] = character

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"""ᴀ ɴᴇᴡ ( {character['rarity']} ) ꜱʟᴀᴠᴇ ʜᴀꜱ ᴀᴘᴘᴇᴀʀᴇᴅ!\nᴜsᴇ /slave [ɴᴀᴍᴇ] ᴀɴᴅ ᴀᴅᴅ ɪɴ ʏᴏᴜʀ ʜᴀʀᴇᴍ!""",
        parse_mode='Markdown'
    )

async def guess(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if chat_id not in last_characters:
        return
    if chat_id in first_correct_guesses:
        await update.message.reply_text(f'❌ 𝘼𝙡𝙧𝙚𝙖𝙙𝙮 𝘽𝙚𝙘𝙤𝙢𝙚 𝙎𝙤𝙢𝙚𝙤𝙣𝙚 𝙎𝙇𝘼𝙑𝙀..')
        return

    guess = ' '.join(context.args).lower() if context.args else ''
    if "()" in guess or "&" in guess.lower():
        await update.message.reply_text("𝙉𝙖𝙝𝙝 𝙔𝙤𝙪 𝘾𝙖𝙣'𝙩 𝙪𝙨𝙚 𝙏𝙝𝙞𝙨 𝙏𝙮𝙥𝙚𝙨 𝙤𝙛 𝙬𝙤𝙧𝙙𝙨 ❌️")
        return

    name_parts = last_characters[chat_id]['name'].lower().split()
if sorted(name_parts) == sorted(guess.split()) or any(part == guess for part in name_parts):
    first_correct_guesses[chat_id] = user_id
    # Handle user data updates and character additions

    keyboard = [[InlineKeyboardButton(f"🪼 ʜᴀʀᴇᴍ", switch_inline_query_current_chat=f"collection.{user_id}")]]
    await update.message.reply_text(
        f'<b><a href="tg://user?id={user_id}">{escape(update.effective_user.first_name)}</a></b> Congratulations 🎊 You grabbed a new Waifu !!✅\n\n'
        f'🎀 𝙉𝙖𝙢𝙚: <code>{last_characters[chat_id]["name"]}</code> \n'
        f'⚡ 𝘼𝙣𝙞𝙢𝙚: <code>{last_characters[chat_id]["anime"]}</code> \n'
        f'{last_characters[chat_id]["rarity"][0]} 𝙍𝙖𝙧𝙞𝙩𝙮: <code>{last_characters[chat_id]["rarity"][2:]}</code>\n\n'
        f'✧⁠ Character successfully added in your harem',
        parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard)
    )
    else:
        await update.message.reply_text('𝙋𝙡𝙚𝙖𝙨𝙚 𝙒𝙧𝙞𝙩𝙚 𝘾𝙤𝙧𝙧𝙚𝙘𝙩 𝙉𝙖𝙢𝙚... ❌️')

async def fav(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text('𝙋𝙡𝙚𝙖𝙨𝙚 𝙥𝙧𝙤𝙫𝙞𝙙𝙚 𝙒𝘼𝙄𝙁𝙐 𝙞𝙙...')
        return

    character_id = context.args[0]
    user = await user_collection.find_one({'id': user_id})
    if not user:
        await update.message.reply_text('𝙔𝙤𝙪 𝙝𝙖𝙫𝙚 𝙣𝙤𝙩 𝙂𝙤𝙩 𝘼𝙣𝙮 𝙒𝘼𝙄𝙁𝙐 𝙮𝙚𝙩...')
        return

    character = next((c for c in user['characters'] if c['id'] == character_id), None)
    if not character:
        await update.message.reply_text('𝙏𝙝𝙞𝙨 𝙒𝘼𝙄𝙁𝙐 𝙞𝙨 𝙉𝙤𝙩 𝙄𝙣 𝙮𝙤𝙪𝙧 𝙒𝘼𝙄𝙁𝙐 𝙡𝙞𝙨𝙩')
        return

    buttons = [
        [InlineKeyboardButton("Yes", callback_data=f"yes_{character_id}"), 
         InlineKeyboardButton("No", callback_data=f"no_{character_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    await update.message.reply_photo(
        photo=character["img_url"],
        caption=f"<b>Do you want to make this waifu your favorite..!</b>\n↬ <code>{character['name']}</code> <code>({character['anime']})</code>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def handle_yes(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    character_id = query.data.split('_')[1]

    await user_collection.update_one({'id': user_id}, {'$set': {'favorites': [character_id]}})
    await query.edit_message_caption(caption="Waifu marked as favorite!")

async def handle_no(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer("Okay, no worries!")
    await query.edit_message_caption(caption="Action canceled.")

def main() -> None:
    """Run bot."""
    application.add_handler(CommandHandler(["grab"], guess, block=False))
    application.add_handler(CommandHandler('fav', fav))
    application.add_handler(CallbackQueryHandler(handle_yes, pattern="yes_*"))
    application.add_handler(CallbackQueryHandler(handle_no, pattern="no_*"))
    application.add_handler(CommandHandler('set_on', set_on, block=False))
    application.add_handler(CommandHandler('set_off', set_off, block=False))
    application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    shivuu.start()
    LOGGER.info("Bot started")
    main()