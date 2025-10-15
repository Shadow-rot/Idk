import os
import sys
import asyncio
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, LOGGER, shivuu

# List of authorized user IDs who can restart the bot (add your admin IDs here)
AUTHORIZED_USERS = [YOUR_ADMIN_ID_HERE]  # Replace with actual admin user IDs

async def restart_bot(update: Update, context: CallbackContext):
    """Restart the bot"""
    try:
        user_id = update.effective_user.id
        
        LOGGER.info(f"[RESTART] Command called by user {user_id}")
        
        # Check if user is authorized
        if user_id not in AUTHORIZED_USERS:
            LOGGER.warning(f"[RESTART] Unauthorized restart attempt by user {user_id}")
            await update.message.reply_text(
                "❌ <b>Access Denied!</b>\n\n"
                "You are not authorized to restart the bot.",
                parse_mode='HTML'
            )
            return
        
        # Send restart confirmation
        restart_msg = await update.message.reply_text(
            "🔄 <b>Restarting Bot...</b>\n\n"
            "⏳ Please wait, the bot will be back online shortly.",
            parse_mode='HTML'
        )
        
        LOGGER.info(f"[RESTART] Bot restart initiated by {update.effective_user.first_name} (ID: {user_id})")
        
        # Give time for message to send
        await asyncio.sleep(1)
        
        # Stop the application gracefully
        try:
            await application.stop()
            LOGGER.info("[RESTART] Application stopped successfully")
        except Exception as e:
            LOGGER.error(f"[RESTART] Error stopping application: {e}")
        
        # Stop the shivuu client
        try:
            shivuu.stop()
            LOGGER.info("[RESTART] Shivuu client stopped successfully")
        except Exception as e:
            LOGGER.error(f"[RESTART] Error stopping shivuu client: {e}")
        
        # Restart the process
        LOGGER.info("[RESTART] Restarting process...")
        os.execv(sys.executable, [sys.executable] + sys.argv)
        
    except Exception as e:
        LOGGER.error(f"[RESTART ERROR] Failed to restart bot: {e}")
        try:
            await update.message.reply_text(
                f"❌ <b>Restart Failed!</b>\n\n"
                f"<code>{str(e)}</code>",
                parse_mode='HTML'
            )
        except:
            pass

async def shutdown_bot(update: Update, context: CallbackContext):
    """Shutdown the bot completely"""
    try:
        user_id = update.effective_user.id
        
        LOGGER.info(f"[SHUTDOWN] Command called by user {user_id}")
        
        # Check if user is authorized
        if user_id not in AUTHORIZED_USERS:
            LOGGER.warning(f"[SHUTDOWN] Unauthorized shutdown attempt by user {user_id}")
            await update.message.reply_text(
                "❌ <b>Access Denied!</b>\n\n"
                "You are not authorized to shutdown the bot.",
                parse_mode='HTML'
            )
            return
        
        # Send shutdown confirmation
        await update.message.reply_text(
            "🛑 <b>Shutting Down Bot...</b>\n\n"
            "Goodbye! 👋",
            parse_mode='HTML'
        )
        
        LOGGER.info(f"[SHUTDOWN] Bot shutdown initiated by {update.effective_user.first_name} (ID: {user_id})")
        
        # Give time for message to send
        await asyncio.sleep(1)
        
        # Stop the application gracefully
        try:
            await application.stop()
            LOGGER.info("[SHUTDOWN] Application stopped successfully")
        except Exception as e:
            LOGGER.error(f"[SHUTDOWN] Error stopping application: {e}")
        
        # Stop the shivuu client
        try:
            shivuu.stop()
            LOGGER.info("[SHUTDOWN] Shivuu client stopped successfully")
        except Exception as e:
            LOGGER.error(f"[SHUTDOWN] Error stopping shivuu client: {e}")
        
        # Exit the process
        LOGGER.info("[SHUTDOWN] Exiting process...")
        sys.exit(0)
        
    except Exception as e:
        LOGGER.error(f"[SHUTDOWN ERROR] Failed to shutdown bot: {e}")
        try:
            await update.message.reply_text(
                f"❌ <b>Shutdown Failed!</b>\n\n"
                f"<code>{str(e)}</code>",
                parse_mode='HTML'
            )
        except:
            pass

async def ping_bot(update: Update, context: CallbackContext):
    """Check if bot is responsive"""
    try:
        import time
        start_time = time.time()
        
        # Send initial message
        msg = await update.message.reply_text("🏓 Pinging...")
        
        # Calculate response time
        end_time = time.time()
        ping_time = round((end_time - start_time) * 1000, 2)
        
        # Update message with ping time
        await msg.edit_text(
            f"🏓 <b>Pong!</b>\n\n"
            f"⚡ Response Time: <code>{ping_time}ms</code>\n"
            f"✅ Bot is online and responsive!",
            parse_mode='HTML'
        )
        
        LOGGER.info(f"[PING] Response time: {ping_time}ms")
        
    except Exception as e:
        LOGGER.error(f"[PING ERROR] Failed to ping: {e}")
        try:
            await update.message.reply_text(
                f"❌ <b>Ping Failed!</b>\n\n"
                f"<code>{str(e)}</code>",
                parse_mode='HTML'
            )
        except:
            pass

def register_restart_handlers():
    """Register restart, shutdown, and ping handlers"""
    LOGGER.info("[RESTART] Registering handlers...")
    
    # Add restart command handler
    application.add_handler(CommandHandler("restart", restart_bot, block=False))
    
    # Add shutdown command handler
    application.add_handler(CommandHandler("shutdown", shutdown_bot, block=False))
    
    # Add ping command handler
    application.add_handler(CommandHandler("ping", ping_bot, block=False))
    
    LOGGER.info("[RESTART] Handlers registered successfully")