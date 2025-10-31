import traceback
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from shivu import application, user_collection, LOGGER

OWNER_ID = 8420981179


async def kill(update: Update, context: CallbackContext) -> None:
    """Remove all characters from user's collection (Owner only)"""
    user_id = update.effective_user.id

    if user_id != OWNER_ID:
        await update.message.reply_text("This command is only for owner!")
        return

    target_user_id = None
    target_first_name = None

    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id
        target_first_name = update.message.reply_to_message.from_user.first_name
    elif context.args:
        try:
            target_user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Invalid user ID!\nUsage: /kill <user_id> or reply to user")
            return
    else:
        await update.message.reply_text("Usage: /kill <user_id> or reply to user")
        return

    try:
        user = await user_collection.find_one({'id': target_user_id})

        if not user:
            await update.message.reply_text(f"User not found! ID: {target_user_id}")
            return

        characters = user.get('characters', [])
        character_count = len(characters)

        if not target_first_name:
            target_first_name = user.get('first_name', 'Unknown')

        if character_count == 0:
            await update.message.reply_text(f"User has no characters!\n\nUser: {target_first_name}\nID: {target_user_id}")
            return

        character_details = []
        for i, char in enumerate(characters[:10]):
            char_name = char.get('name', 'Unknown')
            char_anime = char.get('anime', 'Unknown')
            char_id = char.get('id', 'N/A')
            character_details.append(f"{i+1}. {char_name} ({char_anime}) - ID: {char_id}")

        result = await user_collection.update_one(
            {'id': target_user_id},
            {'$set': {'characters': []}}
        )

        if result.modified_count > 0:
            char_list = "\n".join(character_details[:10])
            if character_count > 10:
                char_list += f"\n... and {character_count - 10} more"

            await update.message.reply_text(
                f"Characters wiped successfully!\n\n"
                f"User: {target_first_name}\n"
                f"ID: {target_user_id}\n\n"
                f"Removed: {character_count} characters\n\n"
                f"Top 10 removed characters:\n{char_list}\n\n"
                f"All characters have been removed from collection."
            )
            LOGGER.info(f"[KILL] Removed {character_count} characters from user {target_user_id}")
        else:
            await update.message.reply_text("Failed to remove characters!")

    except Exception as e:
        LOGGER.error(f"[KILL ERROR] {e}\n{traceback.format_exc()}")
        await update.message.reply_text(f"Error: {str(e)}")


application.add_handler(CommandHandler('kill', kill, block=False))