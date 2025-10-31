import traceback
from datetime import datetime
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from shivu import application, collection, LOGGER

OWNER_ID = 5147822244


async def restore_chr(update: Update, context: CallbackContext) -> None:
    """Restore a removed character back to circulation (Owner only)"""
    user_id = update.effective_user.id

    if user_id != OWNER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Usage: /restore_chr character_id")
        return

    char_id = context.args[0].strip()

    try:
        char_data = await collection.find_one({"id": char_id})

        if not char_data:
            await update.message.reply_text(f"No character found with ID {char_id}.")
            return

        if not char_data.get("removed", False):
            await update.message.reply_text(
                f"Character {char_data.get('name', 'Unknown')} is already active in circulation."
            )
            return

        await collection.update_one(
            {"id": char_id},
            {"$set": {"removed": False, "restored_at": datetime.utcnow()}}
        )

        await update.message.reply_text(
            f"Successfully restored {char_data.get('name', 'Unknown')} ({char_id}) back into circulation."
        )

        LOGGER.info(f"[RESTORE CHR] Character {char_id} restored by {user_id}")

    except Exception as e:
        LOGGER.error(f"[RESTORE CHR ERROR] {e}\n{traceback.format_exc()}")
        await update.message.reply_text("An unexpected error occurred while restoring the character.")


application.add_handler(CommandHandler("restore_chr", restore_chr, block=False))