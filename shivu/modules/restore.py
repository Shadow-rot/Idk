from datetime import datetime
from html import escape
import traceback
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from shivu import application, collection, LOGGER

# Log chat (optional)
LOG_CHAT_ID = -1003071132623  # you can keep or remove this

OWNER_ID = 8420981179

async def restore_chr(update: Update, context: CallbackContext) -> None:
    """Restore a removed character back to circulation (Owner only)."""
    user = update.effective_user
    user_id = user.id

    # ✅ Check owner permissions
    if user_id != OWNER_ID:
        await update.message.reply_text(
            "⚠️ You are not authorized to use this command."
        )
        return

    try:
        # ✅ Ensure character ID is provided
        if len(context.args) < 1:
            await update.message.reply_text(
                "<b>Usage:</b> <code>/restore_chr [character_id]</code>",
                parse_mode="HTML",
            )
            return

        char_id = context.args[0].strip()
        char_data = await collection.find_one({"id": char_id})

        # ✅ Check if character exists in DB
        if not char_data:
            await update.message.reply_text(
                f"❌ No character found with ID <code>{escape(char_id)}</code>.",
                parse_mode="HTML",
            )
            return

        # ✅ Check if it’s actually removed
        if not char_data.get("removed", False):
            await update.message.reply_text(
                f"⚠️ Character <b>{escape(char_data.get('name', 'Unknown'))}</b> "
                f"is already active in circulation.",
                parse_mode="HTML",
            )
            return

        # ✅ Restore the character
        await collection.update_one(
            {"id": char_id},
            {"$set": {"removed": False, "restored_at": datetime.utcnow()}},
        )

        # ✅ Confirmation message
        await update.message.reply_text(
            f"✅ Successfully restored <b>{escape(char_data.get('name', 'Unknown'))}</b> "
            f"(<code>{escape(char_id)}</code>) back into circulation.",
            parse_mode="HTML",
        )

        # Optional log message
        if LOG_CHAT_ID:
            await context.bot.send_message(
                LOG_CHAT_ID,
                f"♻️ Character <b>{escape(char_data.get('name', 'Unknown'))}</b> "
                f"(<code>{escape(char_id)}</code>) was restored by <b>{escape(user.first_name)}</b>.",
                parse_mode="HTML",
            )

    except Exception as e:
        LOGGER.error(f"Error in /restore_chr: {e}")
        LOGGER.error(traceback.format_exc())
        await update.message.reply_text(
            "⚠️ An unexpected error occurred while restoring the character."
        )


# ✅ Register the command handler
def register_restore_chr():
    application.add_handler(CommandHandler("restore_chr", restore_chr))


register_restore_chr()