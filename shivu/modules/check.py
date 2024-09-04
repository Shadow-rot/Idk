import urllib.request
import os
from pymongo import ReturnDocument
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, sudo_users, collection, db, CHARA_CHANNEL_ID, user_collection
from shivu import shivuu as bot
from pyrogram import Client, filters, types as t

async def check_character(update: Update, context: CallbackContext) -> None:
    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text('Incorrect format. Please use: /s slave_id')
            return
        character_id = args[0]
        character = await collection.find_one({'id': character_id})
        if character:
            global_count = await user_collection.count_documents({'characters.id': character['id']})
            response_message = (
                f"<b>OwO! Check out this Slave !!</b>\n\n"
                f"{character['id']}: <b>{character['name']}</b>\n"
                f"<b>{character['anime']}</b>\n"
                f"(𝙍𝘼𝙍𝙄𝙏𝙔: {character['rarity']})"
            )
            if '👘' in character['name']:
                    caption += "\n\n👘𝑲𝒊𝒎𝒐𝒏𝒐👘 "
                elif '☃️' in character['name']:
                    caption += "\n\n☃️𝑾𝒊𝒏𝒕𝒆𝒓☃️"
                elif '🐰' in character['name']:
                    caption += "\n\n🐰𝑩𝒖𝒏𝒏𝒚🐰"
                elif '🎮' in character['name']:
                    caption += "\n\n 🎮𝑮𝒂𝒎𝒆🎮 "
                elif '🎄' in character['name']:
                    caption += "\n\n🎄𝑪𝒓𝒊𝒔𝒕𝒎𝒂𝒔🎄"
                elif '🎃' in character['name']:
                    caption += "\n\n🎃𝑯𝒆𝒍𝒍𝒐𝒘𝒆𝒆𝒏🎃"
                elif '🏖️' in character['name']:
                    caption += "\n\n🏖️𝑺𝒖𝒎𝒎𝒆𝒓🏖️ "
                elif '🧹' in character['name']:
                    caption += "\n\n🧹𝑴𝒂𝒅𝒆🧹"
                elif '🥻' in character['name']:
                    caption += "\n\n🥻𝑺𝒂𝒓𝒆𝒆🥻"
                elif ''☔ in character['name']:
                    caption += "\n\n☔𝑴𝒐𝒏𝒔𝒐𝒐𝒏☔"
                elif '🎒' in character['name']:
                    caption += "\n\n🎒𝑺𝒄𝒉𝒐𝒐𝒍🎒"
                elif '🎩' in character['name']:
                    caption += "\n\n🎩𝑻𝒖𝒙𝒆𝒅𝒐🎩"
                elif '👥' in character['name']:
                    caption += "\n\n👥𝐃𝐮𝐨👥"
                elif '🤝🏻' in character['name']:
                    caption += "\n\n🤝🏻𝐆𝐫𝐨𝐮𝐩🤝🏻"
                elif '👑' in character['name']:
                    caption += "\n\👑𝑳𝒐𝒓𝒅👑n"
                elif '💞' in character['name']:
                    caption += "\n\n💞𝑽𝒂𝒍𝒆𝒏𝒕𝒊𝒏𝒆💞"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Globally Grabbed", callback_data=f"slaves_{character['id']}_{global_count}")]
            ])

            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=character['img_url'],
                caption=response_message,
                parse_mode='HTML',
                reply_markup=keyboard
            )
        else:
            await update.message.reply_text('Wrong id.')

    except Exception as e:
        await update.message.reply_text(f'Error: {str(e)}')
        
async def handle_callback_query(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    data = query.data.split('_')
    if data[0] == 'slaves':
        character_id = data[1]
        global_count = data[2]
        await query.answer(f"⚡️ Globally Slaved : {global_count}x.", show_alert=True)

CHECK_HANDLER = CommandHandler('s', check_character, block=False)
application.add_handler(CallbackQueryHandler(handle_callback_query, pattern='slaves_', block=False))
application.add_handler(CHECK_HANDLER)

@bot.on_message(filters.command(["ani"]))
async def find(_, message: t.Message):
    if len(message.command) < 2:
        return await message.reply_text("Please provide the anime name.", quote=True)

    anime_name = " ".join(message.command[1:])
    characters = await collection.find({'anime': anime_name}).to_list(length=None)
    
    if not characters:
        return await message.reply_text(f"No slave found from the anime {anime_name}.", quote=True)

    seen_names = set()
    captions = []
    for char in characters:
        if char['name'] not in seen_names:
            captions.append(f"Name: {char['name']}\n")
            seen_names.add(char['name'])

    response = "\n".join(captions)
    await message.reply_text(f"Characters from {anime_name}:\n\n{response}", quote=True)

from pyrogram import Client, filters
from shivu import user_collection
from shivu import shivuu as app

OWNER_ID = 7011990425  # Replace with the actual owner ID

async def get_users_by_character(character_id):
    try:
        cursor = user_collection.find(
            {'characters.id': character_id}, 
            {'_id': 0, 'id': 1, 'name': 1, 'username': 1, 'characters.$': 1}
        )
        users = await cursor.to_list(length=None)
        return users
    except Exception as e:
        print("Failed to get users by character:", e)
        return []

@app.on_message(filters.command(["ik"]) & filters.user(OWNER_ID))
async def find_users(_, message):
    if len(message.command) < 2:
        await message.reply_text("Please provide the character ID.", quote=True)
        return

    character_id = message.command[1]
    users = await get_users_by_character(character_id)

    if users:
        response = ""
        for user in users:
            user_id = user['id']
            name = user.get('first_name', 'N/A')
            username = user.get('username', 'N/A')
            character = user['characters'][0]
            character_name = character.get('name', 'N/A')
            response += f"{name} [`{user_id}`]\n\n"
        await message.reply_text(f"Users with character ID {character_id}:\n\n{response}", quote=True)
    else:
        await message.reply_text(f"No users found with character ID: {character_id}", quote=True)
