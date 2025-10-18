import importlib
import time
import random
import re
import asyncio
from html import escape
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, filters, Application, CallbackQueryHandler
from shivu import collection, top_global_groups_collection, group_user_totals_collection, user_collection, user_totals_collection, shivuu
from shivu import LOGGER
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

def escape_markdown(text):
    escape_chars = r'\*_`\\~>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)

async def message_counter(update: Update, context: CallbackContext) -> None:
    chat_id = str(update.effective_chat.id)
    user_id = update.effective_user.id
    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()
    lock = locks[chat_id]

    async with lock:
        chat_frequency = await user_totals_collection.find_one({'chat_id': chat_id})
        message_frequency = chat_frequency.get('message_frequency', 100) if chat_frequency else 100

        if chat_id in last_user and last_user[chat_id]['user_id'] == user_id:
            last_user[chat_id]['count'] += 1
            if last_user[chat_id]['count'] >= 10:
                if user_id in warned_users and time.time() - warned_users[user_id] < 600:
                    return
                else:
                    await update.message.reply_html(f"<b>ᴅᴏɴ'ᴛ 𝗌ᴘᴀᴍ</b> {update.effective_user.first_name}...\n<b>ʏᴏᴜʀ ᴍᴇssᴀɢᴇs ᴡɪʟʟ ʙᴇ ɪɢɴᴏʀᴇᴅ ғᴏʀ 𝟷𝟶 ᴍɪɴᴜᴛᴇs...!!</b>")
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

    if len(sent_characters[chat_id]) == len(all_characters):
        sent_characters[chat_id] = []

    # Filter characters to include only those with an 'id'
    available_characters = [c for c in all_characters if 'id' in c and c['id'] not in sent_characters[chat_id]]

    if not available_characters:
        await update.message.reply_html("<b>All characters have been sent. Resetting character list.</b>")
        sent_characters[chat_id] = []
        return

    character = random.choice(available_characters)
    sent_characters[chat_id].append(character['id'])
    last_characters[chat_id] = character

    if chat_id in first_correct_guesses:
        del first_correct_guesses[chat_id]

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=character['img_url'],
        caption=f"""***{character['rarity'][0]} ʟᴏᴏᴋ ᴀ ᴡᴀɪғᴜ ʜᴀꜱ ꜱᴘᴀᴡɴᴇᴅ !! ᴍᴀᴋᴇ ʜᴇʀ ʏᴏᴜʀ'ꜱ ʙʏ ɢɪᴠɪɴɢ  
        /grab 𝚆𝚊𝚒𝚏𝚞 𝚗𝚊𝚖𝚎***""",
        parse_mode='Markdown'
    )

async def guess(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in last_characters:
        return

    if chat_id in first_correct_guesses:
        await update.message.reply_html(f'<b>🚫ᴡᴀɪғᴜ ᴀʟʀᴇᴀᴅʏ ɢʀᴀʙʙᴇᴅ ʙʏ sᴏᴍᴇᴏɴᴇ ᴇʟsᴇ ⚡. ʙᴇᴛᴛᴇʀ ʟᴜᴄᴋ ɴᴇxᴛ ᴛɪᴍᴇ..!!</b>')
        return

    guess = ' '.join(context.args).lower() if context.args else ''
    if "()" in guess or "&" in guess.lower():
        await update.message.reply_html("<b>ɴᴀʜʜ ʏᴏᴜ ᴄᴀɴ'ᴛ ᴜsᴇ ᴛʜɪs ᴛʏᴘᴇs ᴏғ ᴡᴏʀᴅs...❌</b>")
        return

    name_parts = last_characters[chat_id]['name'].lower().split()
    if sorted(name_parts) == sorted(guess.split()) or any(part == guess for part in name_parts):
        first_correct_guesses[chat_id] = user_id
        user = await user_collection.find_one({'id': user_id})

        update_fields = {}
        if user:
            if hasattr(update.effective_user, 'username') and update.effective_user.username != user.get('username'):
                update_fields['username'] = update.effective_user.username
            if update.effective_user.first_name != user.get('first_name'):
                update_fields['first_name'] = update.effective_user.first_name

            if update_fields:
                await user_collection.update_one({'id': user_id}, {'$set': update_fields})
            await user_collection.update_one({'id': user_id}, {'$push': {'characters': last_characters[chat_id]}})
        else:
            await user_collection.insert_one({
                'id': user_id,
                'username': update.effective_user.username,
                'first_name': update.effective_user.first_name,
                'characters': [last_characters[chat_id]],
            })

        group_user_total = await group_user_totals_collection.find_one({'user_id': user_id, 'group_id': chat_id})
        if group_user_total:
            update_fields = {}
            if hasattr(update.effective_user, 'username') and update.effective_user.username != group_user_total.get('username'):
                update_fields['username'] = update.effective_user.username
            if update.effective_user.first_name != group_user_total.get('first_name'):
                update_fields['first_name'] = update.effective_user.first_name

            if update_fields:
                await group_user_totals_collection.update_one({'user_id': user_id, 'group_id': chat_id}, {'$set': update_fields})
            await group_user_totals_collection.update_one({'user_id': user_id, 'group_id': chat_id}, {'$inc': {'count': 1}})
        else:
            await group_user_totals_collection.insert_one({
                'user_id': user_id,
                'group_id': chat_id,
                'username': update.effective_user.username,
                'first_name': update.effective_user.first_name,
                'count': 1,
            })

        group_info = await top_global_groups_collection.find_one({'group_id': chat_id})
        if group_info:
            update_fields = {}
            if update.effective_chat.title != group_info.get('group_name'):
                update_fields['group_name'] = update.effective_chat.title
            if update_fields:
                await top_global_groups_collection.update_one({'group_id': chat_id}, {'$set': update_fields})
            await top_global_groups_collection.update_one({'group_id': chat_id}, {'$inc': {'count': 1}})
        else:
            await top_global_groups_collection.insert_one({
                'group_id': chat_id,
                'group_name': update.effective_chat.title,
                'count': 1,
            })

        keyboard = [[InlineKeyboardButton(f"🪼 ʜᴀʀᴇᴍ", switch_inline_query_current_chat=f"collection.{user_id}")]]
        await update.message.reply_text(
            f'Congratulations 🎊\n<b><a href="tg://user?id={user_id}">{escape(update.effective_user.first_name)}</a></b> You grabbed a new waifu!! ✅️\n\n🎀 𝙉𝙖𝙢𝙚: <code>{last_characters[chat_id]["name"]}</code>\n{last_characters[chat_id]["rarity"][0]} 𝙍𝙖𝙧𝙞𝙩𝙮: <code>{last_characters[chat_id]["rarity"][2:]}</code>\n⚡ 𝘼𝙣𝙞𝙢𝙚: <code>{last_characters[chat_id]["anime"]}</code>\n\n✧⁠ Character successfully added in your harem',
            parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_html('<b>ᴘʟᴇᴀsᴇ ᴡʀɪᴛᴇ ᴀ ᴄᴏʀʀᴇᴄᴛ ɴᴀᴍᴇ..❌</b>')

async def fav(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_html('<b>ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴡᴀɪғᴜ ɪᴅ....!!</b>')
        return
    character_id = context.args[0]

    user = await user_collection.find_one({'id': user_id})
    if not user:
        await update.message.reply_html('<b>ʏᴏᴜ ʜᴀᴠᴇ ɴᴏᴛ ɢᴏᴛ ᴀɴʏ ᴡᴀɪғᴜ ʏᴇᴛ..!</b>')
        return

    character = next((c for c in user['characters'] if c['id'] == character_id), None)
    if not character:
        await update.message.reply_html('<b>ᴛʜɪs ᴡᴀɪғᴜ ɪs ɴᴏᴛ ɪɴ ʏᴏᴜʀ ʜᴀʀᴇᴍ ʟɪsᴛ</b>')
        return

    buttons = [
        [InlineKeyboardButton("🟢 Yes", callback_data=f"yes_{character_id}"), 
         InlineKeyboardButton("🔴 No", callback_data=f"no_{character_id}")]
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
    await query.edit_message_caption(caption="<b>ᴡᴀɪғᴜ ʜᴀs ʙᴇᴇɴ sᴜᴄᴄᴇssғᴜʟʟʏ sᴇᴛ ᴀs ᴀ ғᴀᴠᴏʀɪᴛᴇ!</b>", parse_mode="HTML")

async def handle_no(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer("Okay, no worries!")
    await query.edit_message_caption(caption="canceled.")

def main() -> None:
    """Run bot."""
    application.add_handler(CommandHandler(["grab"], guess, block=False))
    application.add_handler(CommandHandler('fav', fav))
    application.add_handler(CallbackQueryHandler(handle_yes, pattern="yes_*"))
    application.add_handler(CallbackQueryHandler(handle_no, pattern="no_*"))
    application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    shivuu.start()
    LOGGER.info("Bot started")
    main()