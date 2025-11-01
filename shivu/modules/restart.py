import os
import sys
import asyncio
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from shivu import application, LOGGER
from telegram.error import BadRequest

# Owner ID
OWNER_ID = 5147822244

# We'll access the global dictionaries from the main module at runtime
def get_main_globals():
    """Get references to the global dictionaries from main"""
    import shivu.__main__ as main_module
    return (
        main_module.locks,
        main_module.message_counts,
        main_module.sent_characters,
        main_module.last_characters,
        main_module.first_correct_guesses,
        main_module.last_user,
        main_module.warned_users,
        main_module.spawn_messages,
        main_module.spawn_message_links
    )


async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restart the bot - Owner only command"""
    user_id = update.effective_user.id

    # Check if user is owner
    if user_id != OWNER_ID:
        await update.message.reply_text("This command is only for the bot owner.")
        return

    response = await update.message.reply_text("Restarting bot...")

    try:
        # Get references to global dictionaries
        (locks, message_counts, sent_characters, last_characters,
         first_correct_guesses, last_user, warned_users,
         spawn_messages, spawn_message_links) = get_main_globals()
        
        # Clear all spawn data and locks
        LOGGER.info("Clearing spawn data before restart...")
        locks.clear()
        message_counts.clear()
        sent_characters.clear()
        last_characters.clear()
        first_correct_guesses.clear()
        last_user.clear()
        warned_users.clear()
        spawn_messages.clear()
        spawn_message_links.clear()

        await response.edit_text(
            "Restart process started!\n\n"
            "Please wait for few seconds...\n"
            "Bot will be back online shortly!"
        )

        LOGGER.info("Bot restart initiated by owner")

        # Small delay to ensure message is sent
        await asyncio.sleep(1)

        # Stop the application gracefully
        await application.stop()
        await application.shutdown()

        # Restart the process
        os.execl(sys.executable, sys.executable, *sys.argv)

    except Exception as e:
        LOGGER.error(f"Error during restart: {e}")
        try:
            await response.edit_text(f"Error during restart:\n{str(e)}")
        except:
            pass


async def shutdown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shutdown the bot - Owner only command"""
    user_id = update.effective_user.id

    # Check if user is owner
    if user_id != OWNER_ID:
        await update.message.reply_text("This command is only for the bot owner.")
        return

    response = await update.message.reply_text("Shutting down bot...")

    try:
        await response.edit_text(
            "Bot shutdown initiated!\n\n"
            "Goodbye!"
        )

        LOGGER.info("Bot shutdown initiated by owner")

        # Get references to global dictionaries
        (locks, message_counts, sent_characters, last_characters,
         first_correct_guesses, last_user, warned_users,
         spawn_messages, spawn_message_links) = get_main_globals()

        # Clear all data
        locks.clear()
        message_counts.clear()
        sent_characters.clear()
        last_characters.clear()
        first_correct_guesses.clear()
        last_user.clear()
        warned_users.clear()
        spawn_messages.clear()
        spawn_message_links.clear()

        # Small delay to ensure message is sent
        await asyncio.sleep(1)

        # Stop the application
        await application.stop()
        await application.shutdown()

        sys.exit(0)

    except Exception as e:
        LOGGER.error(f"Error during shutdown: {e}")
        try:
            await response.edit_text(f"Error during shutdown:\n{str(e)}")
        except:
            pass


# Handler registration function
def setup_restart_handlers(app):
    """Setup restart and shutdown command handlers"""
    app.add_handler(CommandHandler("restart", restart_command, block=False))
    app.add_handler(CommandHandler("shutdown", shutdown_command, block=False))
    LOGGER.info("Restart and shutdown handlers registered")