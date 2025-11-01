import os
import sys
import asyncio
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from shivu import application, LOGGER, OWNER_ID
from telegram.error import BadRequest

async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restart the bot - Owner only command"""
    user_id = update.effective_user.id
    
    # Check if user is owner
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ This command is only for the bot owner.")
        return
    
    response = await update.message.reply_text("🔄 **ʀᴇsᴛᴀʀᴛɪɴɢ ʙᴏᴛ...**", parse_mode='Markdown')
    
    try:
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
            "✅ **ʀᴇsᴛᴀʀᴛ ᴘʀᴏᴄᴇss sᴛᴀʀᴛᴇᴅ!**\n\n"
            "⏳ ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ ғᴏʀ ғᴇᴡ sᴇᴄᴏɴᴅs...\n"
            "🔄 ʙᴏᴛ ᴡɪʟʟ ʙᴇ ʙᴀᴄᴋ ᴏɴʟɪɴᴇ sʜᴏʀᴛʟʏ!",
            parse_mode='Markdown'
        )
        
        LOGGER.info("Bot restart initiated by owner")
        
        # Stop the application gracefully
        await application.stop()
        await application.shutdown()
        
        # Restart the process
        os.execl(sys.executable, sys.executable, *sys.argv)
        
    except Exception as e:
        LOGGER.error(f"Error during restart: {e}")
        try:
            await response.edit_text(f"❌ **ᴇʀʀᴏʀ ᴅᴜʀɪɴɢ ʀᴇsᴛᴀʀᴛ:**\n`{str(e)}`", parse_mode='Markdown')
        except:
            pass


async def shutdown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shutdown the bot - Owner only command"""
    user_id = update.effective_user.id
    
    # Check if user is owner
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ This command is only for the bot owner.")
        return
    
    response = await update.message.reply_text("⚠️ **sʜᴜᴛᴛɪɴɢ ᴅᴏᴡɴ ʙᴏᴛ...**", parse_mode='Markdown')
    
    try:
        await response.edit_text(
            "🛑 **ʙᴏᴛ sʜᴜᴛᴅᴏᴡɴ ɪɴɪᴛɪᴀᴛᴇᴅ!**\n\n"
            "👋 ɢᴏᴏᴅʙʏᴇ!",
            parse_mode='Markdown'
        )
        
        LOGGER.info("Bot shutdown initiated by owner")
        
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
        
        # Stop the application
        await application.stop()
        await application.shutdown()
        
        sys.exit(0)
        
    except Exception as e:
        LOGGER.error(f"Error during shutdown: {e}")
        try:
            await response.edit_text(f"❌ **ᴇʀʀᴏʀ ᴅᴜʀɪɴɢ sʜᴜᴛᴅᴏᴡɴ:**\n`{str(e)}`", parse_mode='Markdown')
        except:
            pass