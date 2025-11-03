from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from shivu import shivuu
import os
import time

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

@shivuu.on_message(filters.command("rename"))
async def rename_file(client: Client, message: Message):
    """
    Rename files up to 2GB
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
        f"<blockquote>\n{sc('processing')}\n{sc('downloading file...')}\n</blockquote>",
        parse_mode=ParseMode.HTML
    )
    
    try:
        start_time = time.time()
        
        # Download the file
        downloaded_file = await replied.download(
            file_name=new_filename,
            progress=lambda current, total: None  # You can add progress callback here
        )
        
        download_time = time.time() - start_time
        
        # Update status
        await status_msg.edit_text(
            f"<blockquote>\n{sc('uploading')}\n{sc('uploading renamed file...')}\n</blockquote>",
            parse_mode=ParseMode.HTML
        )
        
        # Get file caption
        caption = replied.caption if replied.caption else f"<b>{sc('renamed by bot')}</b>"
        
        # Upload the renamed file
        upload_start = time.time()
        
        if replied.document:
            new_msg = await message.reply_document(
                document=downloaded_file,
                caption=caption,
                parse_mode=ParseMode.HTML,
                progress=lambda current, total: None
            )
        elif replied.video:
            new_msg = await message.reply_video(
                video=downloaded_file,
                caption=caption,
                parse_mode=ParseMode.HTML,
                progress=lambda current, total: None
            )
        elif replied.audio:
            new_msg = await message.reply_audio(
                audio=downloaded_file,
                caption=caption,
                parse_mode=ParseMode.HTML,
                progress=lambda current, total: None
            )
        elif replied.animation:
            new_msg = await message.reply_animation(
                animation=downloaded_file,
                caption=caption,
                parse_mode=ParseMode.HTML,
                progress=lambda current, total: None
            )
        else:  # photo
            new_msg = await message.reply_photo(
                photo=downloaded_file,
                caption=caption,
                parse_mode=ParseMode.HTML
            )
        
        upload_time = time.time() - upload_start
        total_time = time.time() - start_time
        
        # Delete status message
        await status_msg.delete()
        
        # Send success message
        await message.reply_text(
            f"<blockquote expandable>\n"
            f"{sc('rename complete')}\n\n"
            f"<b>{sc('details')}</b>\n"
            f"{sc('filename')}: <code>{new_filename}</code>\n"
            f"{sc('size')}: <code>{format_size(file_size)}</code>\n"
            f"{sc('download time')}: <code>{download_time:.2f}s</code>\n"
            f"{sc('upload time')}: <code>{upload_time:.2f}s</code>\n"
            f"{sc('total time')}: <code>{total_time:.2f}s</code>\n"
            f"</blockquote>",
            parse_mode=ParseMode.HTML
        )
        
        # Clean up downloaded file
        try:
            os.remove(downloaded_file)
        except:
            pass
    
    except Exception as e:
        print(f"Rename error: {e}")
        import traceback
        traceback.print_exc()
        
        await status_msg.edit_text(
            f"<blockquote>\n"
            f"{sc('error occurred')}\n"
            f"{sc('details')}: <code>{str(e)}</code>\n"
            f"</blockquote>",
            parse_mode=ParseMode.HTML
        )
        
        # Clean up if file exists
        try:
            if 'downloaded_file' in locals() and os.path.exists(downloaded_file):
                os.remove(downloaded_file)
        except:
            pass


@shivuu.on_message(filters.command("renamehelp"))
async def rename_help(client: Client, message: Message):
    """Show rename command help"""
    await message.reply_text(
        f"<blockquote expandable>\n"
        f"{sc('file renamer help')}\n\n"
        f"<b>{sc('command')}</b>\n"
        f"<code>/rename newname.ext</code>\n\n"
        f"<b>{sc('how to use')}</b>\n"
        f"1. {sc('upload or forward a file')}\n"
        f"2. {sc('reply to that file')}\n"
        f"3. {sc('type')} <code>/rename newname.ext</code>\n"
        f"4. {sc('bot will download and upload with new name')}\n\n"
        f"<b>{sc('supported files')}</b>\n"
        f"• {sc('documents')} (.pdf, .zip, .apk, {sc('etc')})\n"
        f"• {sc('videos')} (.mp4, .mkv, .avi, {sc('etc')})\n"
        f"• {sc('audio')} (.mp3, .flac, .wav, {sc('etc')})\n"
        f"• {sc('photos')} (.jpg, .png, {sc('etc')})\n"
        f"• {sc('animations')} (.gif, {sc('etc')})\n\n"
        f"<b>{sc('limitations')}</b>\n"
        f"• {sc('max file size')}: <code>2 GB</code>\n"
        f"• {sc('processing time depends on file size')}\n\n"
        f"<b>{sc('examples')}</b>\n"
        f"<code>/rename movie.mp4</code>\n"
        f"<code>/rename document.pdf</code>\n"
        f"<code>/rename song.mp3</code>\n"
        f"<code>/rename MyApp_v2.0.apk</code>\n"
        f"</blockquote>",
        parse_mode=ParseMode.HTML
    )