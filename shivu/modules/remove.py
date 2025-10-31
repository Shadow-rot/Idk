import traceback
from datetime import datetime
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from shivu import application, collection, LOGGER

OWNER_ID = 5147822244


async def remove_chr(update: Update, context: CallbackContext) -> None:
    """Remove character from circulation (Owner only)"""
    user_id = update.effective_user.id

    if user_id != OWNER_ID:
        await update.message.reply_text("This command is only for owner!")
        return

    if not context.args:
        await update.message.reply_text("Usage: /remove_chr character_id")
        return

    character_id = str(context.args[0])

    try:
        character = await collection.find_one({'id': character_id})

        if not character:
            await update.message.reply_text(f"Character with ID {character_id} not found!")
            return

        await collection.update_one(
            {'id': character_id},
            {'$set': {'removed': True, 'removed_at': datetime.now()}}
        )

        rarity = character.get('rarity', 'Common')
        if isinstance(rarity, str):
            rarity_parts = rarity.split(' ', 1)
            rarity_text = rarity_parts[1] if len(rarity_parts) > 1 else 'Common'
        else:
            rarity_text = 'Common'

        await update.message.reply_text(
            f"Character removed!\n\n"
            f"Name: {character.get('name', 'Unknown')}\n"
            f"ID: {character_id}\n"
            f"Rarity: {rarity_text}\n\n"
            f"This character will no longer spawn in groups."
        )

        LOGGER.info(f"[REMOVE CHR] Character {character_id} removed by {user_id}")

    except Exception as e:
        LOGGER.error(f"[REMOVE CHR ERROR] {e}\n{traceback.format_exc()}")
        await update.message.reply_text(f"Error: {str(e)}")


application.add_handler(CommandHandler('remove_chr', remove_chr, block=False))