import traceback
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from shivu import application, user_collection, LOGGER

OWNER_ID = 5147822244


async def ckill(update: Update, context: CallbackContext) -> None:
    """Remove user's balance (wallet + bank) to 0 (Owner only)"""
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
            await update.message.reply_text("Invalid user ID!\nUsage: /ckill <user_id> or reply to user")
            return
    else:
        await update.message.reply_text("Usage: /ckill <user_id> or reply to user")
        return

    try:
        user = await user_collection.find_one({'id': target_user_id})

        if not user:
            await update.message.reply_text(f"User not found! ID: {target_user_id}")
            return

        wallet = user.get('balance', 0)
        bank = user.get('bank', 0)
        total = wallet + bank

        if not target_first_name:
            target_first_name = user.get('first_name', 'Unknown')

        result = await user_collection.update_one(
            {'id': target_user_id},
            {'$set': {'balance': 0, 'bank': 0}}
        )

        if result.modified_count > 0:
            await update.message.reply_text(
                f"Balance reset successfully!\n\n"
                f"User: {target_first_name}\n"
                f"ID: {target_user_id}\n\n"
                f"Previous Balance:\n"
                f"Wallet: {wallet:,}\n"
                f"Bank: {bank:,}\n"
                f"Total Removed: {total:,}\n\n"
                f"New Balance: 0"
            )
            LOGGER.info(f"[CKILL] Reset balance for user {target_user_id} - Removed {total} coins")
        else:
            await update.message.reply_text("Failed to update balance!")

    except Exception as e:
        LOGGER.error(f"[CKILL ERROR] {e}\n{traceback.format_exc()}")
        await update.message.reply_text(f"Error: {str(e)}")


application.add_handler(CommandHandler('ckill', ckill, block=False))