from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from shivu import shivuu
import os
import time
import asyncio
from pathlib import Path

def sc(text):
    """Small caps converter"""
    m = {'a':'ᴀ','b':'ʙ','c':'ᴄ','d':'ᴅ','e':'ᴇ','f':'ғ','g':'ɢ','h':'ʜ','i':'ɪ','j':'ᴊ','k':'ᴋ','l':'ʟ','m':'ᴍ','n':'ɴ','o':'ᴏ','p':'ᴘ','q':'ǫ','r':'ʀ','s':'s','t':'ᴛ','u':'ᴜ','v':'ᴠ','w':'ᴡ','x':'x','y':'ʏ','z':'ᴢ'}
    return ''.join(m.get(c.lower(), c) for c in text)

def format_size(size_bytes):
    """Format bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def time_formatter(seconds):
    """Format seconds to readable time"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    else:
        return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"

class Progress:
    def __init__(self, message, action):
        self.message = message
        self.action = action
        self.last_update = 0
        self.start_time = time.time()
    
    async def progress_callback(self, current, total):
        now = time.time()
        # Update every 3 seconds to avoid flood
        if now - self.last_update < 3:
            return
        
        self.last_update = now
        percentage = current * 100 / total
        speed = current / (now - self.start_time)
        eta = (total - current) / speed if speed > 0 else 0
        
        try:
            await self.message.edit_text(
                f"<blockquote>\n"
                f"<b>{self.action}</b>\n"
                f"{sc('progress')}: <code>{percentage:.1f}%</code>\n"
                f"{sc('size')}: <code>{format_size(current)}</code> / <code>{format_size(total)}</code>\n"
                f"{sc('speed')}: <code>{format_size(speed)}/s</code>\n"
                f"{sc('eta')}: <code>{time_formatter(eta)}</code>\n"
                f"</blockquote>",
                parse_mode=ParseMode.HTML
            )
        except:
            pass

@shivuu.on_message(filters.command("rename"))
async def rename_file(client: Client, message: Message):
    """
    Rename files up to 2GB with optimized speed
    Usage: Reply to a file with /rename <new_filename>
    """
    
    # Check if replying to a message
    if not message.reply_to_message:
        return await message.reply_text(
            f"<blockquote expandable>\n"
            f"{sc('file renamer')}\n\n"
            f"<b>{sc('usage')}</b>\n"
            f"{sc('reply to a file with')}: <code>/rename newname.ext</code>\n\n"
            f"<b>{sc('supported')}</b>\n"
            f"• {sc('documents')}\n"
            f"• {sc('videos')}\n"
            f"• {sc('audio')}\n"
            f"• {sc('photos')}\n"
            f"• {sc('animations')}\n\n"
            f"<b>{sc('limit')}</b>\n"
            f"{sc('max size')}: <code>2 GB</code>\n"
            f"</blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    replied = message.reply_to_message
    
    # Check if message contains a file
    media = replied.document or replied.video or replied.audio or replied.photo or replied.animation
    
    if not media:
        return await message.reply_text(
            f"<blockquote>\n{sc('please reply to a file')}\n</blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    # Check if new filename is provided
    if len(message.command) < 2:
        return await message.reply_text(
            f"<blockquote>\n{sc('please provide new filename')}\n"
            f"{sc('example')}: <code>/rename newfile.mp4</code>\n</blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    new_filename = message.text.split(None, 1)[1]
    
    # Get file size
    file_size = getattr(media, 'file_size', 0)
    
    # Check file size limit (2GB = 2147483648 bytes)
    if file_size > 2147483648:
        return await message.reply_text(
            f"<blockquote>\n"
            f"{sc('file too large')}\n"
            f"{sc('size')}: <code>{format_size(file_size)}</code>\n"
            f"{sc('limit')}: <code>2 GB</code>\n"
            f"</blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    # Send processing message
    status_msg = await message.reply_text(
        f"<blockquote>\n{sc('starting download...')}\n</blockquote>",
        parse_mode=ParseMode.HTML
    )
    
    downloaded_file = None
    
    try:
        start_time = time.time()
        
        # Create progress tracker for download
        download_progress = Progress(status_msg, sc('downloading'))
        
        # Download with progress
        downloaded_file = await replied.download(
            file_name=new_filename,
            progress=download_progress.progress_callback
        )
        
        download_time = time.time() - start_time
        
        # Update status for upload
        await status_msg.edit_text(
            f"<blockquote>\n{sc('starting upload...')}\n</blockquote>",
            parse_mode=ParseMode.HTML
        )
        
        # Small delay
        await asyncio.sleep(0.3)
        
        # Get original attributes
        caption = replied.caption if replied.caption else None
        
        # Create progress tracker for upload
        upload_progress = Progress(status_msg, sc('uploading'))
        upload_start = time.time()
        
        # Upload based on media type
        if replied.document:
            new_msg = await message.reply_document(
                document=downloaded_file,
                caption=caption,
                file_name=new_filename,
                parse_mode=ParseMode.HTML if caption else None,
                progress=upload_progress.progress_callback
            )
            
        elif replied.video:
            new_msg = await message.reply_video(
                video=downloaded_file,
                caption=caption,
                duration=getattr(media, 'duration', 0),
                width=getattr(media, 'width', 0),
                height=getattr(media, 'height', 0),
                supports_streaming=True,
                file_name=new_filename,
                parse_mode=ParseMode.HTML if caption else None,
                progress=upload_progress.progress_callback
            )
            
        elif replied.audio:
            new_msg = await message.reply_audio(
                audio=downloaded_file,
                caption=caption,
                duration=getattr(media, 'duration', 0),
                performer=getattr(media, 'performer', None),
                title=getattr(media, 'title', None),
                file_name=new_filename,
                parse_mode=ParseMode.HTML if caption else None,
                progress=upload_progress.progress_callback
            )
            
        elif replied.animation:
            new_msg = await message.reply_animation(
                animation=downloaded_file,
                caption=caption,
                file_name=new_filename,
                parse_mode=ParseMode.HTML if caption else None,
                progress=upload_progress.progress_callback
            )
            
        else:  # photo
            new_msg = await message.reply_photo(
                photo=downloaded_file,
                caption=caption,
                parse_mode=ParseMode.HTML if caption else None
            )
        
        upload_time = time.time() - upload_start
        total_time = time.time() - start_time
        
        # Calculate average speed
        avg_speed = file_size / total_time if total_time > 0 else 0
        
        # Delete status message
        await status_msg.delete()
        
        # Send success message
        success_msg = await message.reply_text(
            f"<blockquote expandable>\n"
            f"<b>{sc('rename complete')}</b>\n\n"
            f"{sc('filename')}: <code>{new_filename}</code>\n"
            f"{sc('size')}: <code>{format_size(file_size)}</code>\n"
            f"{sc('download')}: <code>{time_formatter(download_time)}</code>\n"
            f"{sc('upload')}: <code>{time_formatter(upload_time)}</code>\n"
            f"{sc('total')}: <code>{time_formatter(total_time)}</code>\n"
            f"{sc('avg speed')}: <code>{format_size(avg_speed)}/s</code>\n"
            f"</blockquote>",
            parse_mode=ParseMode.HTML
        )
        
        # Auto-delete success message after 30 seconds
        await asyncio.sleep(30)
        try:
            await success_msg.delete()
        except:
            pass
        
    except Exception as e:
        error_msg = str(e)
        print(f"Rename error: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            await status_msg.edit_text(
                f"<blockquote>\n"
                f"<b>{sc('error occurred')}</b>\n"
                f"{sc('details')}: <code>{error_msg[:100]}</code>\n"
                f"</blockquote>",
                parse_mode=ParseMode.HTML
            )
        except:
            await message.reply_text(
                f"<blockquote>\n{sc('an error occurred')}\n</blockquote>",
                parse_mode=ParseMode.HTML
            )
    
    finally:
        # Clean up downloaded file
        if downloaded_file:
            try:
                await asyncio.sleep(1)
                if os.path.exists(downloaded_file):
                    os.remove(downloaded_file)
            except Exception as e:
                print(f"Cleanup error: {e}")


@shivuu.on_message(filters.command("renamehelp"))
async def rename_help(client: Client, message: Message):
    """Show rename command help"""
    await message.reply_text(
        f"<blockquote expandable>\n"
        f"<b>{sc('file renamer help')}</b>\n\n"
        f"<b>{sc('command')}</b>\n"
        f"<code>/rename newname.ext</code>\n\n"
        f"<b>{sc('how to use')}</b>\n"
        f"1. {sc('upload or forward a file')}\n"
        f"2. {sc('reply to that file')}\n"
        f"3. {sc('type')} <code>/rename newname.ext</code>\n"
        f"4. {sc('bot will process with progress')}\n\n"
        f"<b>{sc('features')}</b>\n"
        f"• {sc('real-time progress tracking')}\n"
        f"• {sc('speed and eta display')}\n"
        f"• {sc('preserves media attributes')}\n"
        f"• {sc('optimized for speed')}\n\n"
        f"<b>{sc('supported files')}</b>\n"
        f"• {sc('documents')} (.pdf, .zip, .apk, {sc('etc')})\n"
        f"• {sc('videos')} (.mp4, .mkv, .avi, {sc('etc')})\n"
        f"• {sc('audio')} (.mp3, .flac, .wav, {sc('etc')})\n"
        f"• {sc('photos')} (.jpg, .png, {sc('etc')})\n"
        f"• {sc('animations')} (.gif, {sc('etc')})\n\n"
        f"<b>{sc('limitations')}</b>\n"
        f"• {sc('max file size')}: <code>2 GB</code>\n"
        f"• {sc('speed depends on server and file size')}\n\n"
        f"<b>{sc('examples')}</b>\n"
        f"<code>/rename movie.mp4</code>\n"
        f"<code>/rename document.pdf</code>\n"
        f"<code>/rename song.mp3</code>\n"
        f"<code>/rename MyApp_v2.0.apk</code>\n"
        f"</blockquote>",
        parse_mode=ParseMode.HTML
    )