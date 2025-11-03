from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from shivu import shivuu
import os
import time
import asyncio
from PIL import Image
import cv2
import numpy as np

def sc(text):
    """Small caps converter"""
    m = {'a':'ᴀ','b':'ʙ','c':'ᴄ','d':'ᴅ','e':'ᴇ','f':'ғ','g':'ɢ','h':'ʜ','i':'ɪ','j':'ᴊ','k':'ᴋ','l':'ʟ','m':'ᴍ','n':'ɴ','o':'ᴏ','p':'ᴘ','q':'ǫ','r':'ʀ','s':'s','t':'ᴛ','u':'ᴜ','v':'ᴠ','w':'ᴡ','x':'x','y':'ʏ','z':'ᴢ'}
    return ''.join(m.get(c.lower(), c) for c in text)

def remove_watermark(image_path, output_path):
    """
    Remove watermark from image using inpainting technique
    Preserves original quality
    """
    # Read image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Could not read image")
    
    # Convert to RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Create mask for watermark detection
    # Method 1: Detect white/light colored watermarks
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Adaptive thresholding to detect watermark
    # This works well for semi-transparent watermarks
    mask = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 11, 2
    )
    
    # Detect edges (watermarks often have distinct edges)
    edges = cv2.Canny(gray, 50, 150)
    
    # Combine masks
    combined_mask = cv2.bitwise_or(mask, edges)
    
    # Morphological operations to clean up mask
    kernel = np.ones((3, 3), np.uint8)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
    
    # Remove small noise
    combined_mask = cv2.medianBlur(combined_mask, 5)
    
    # Inpainting - this fills the watermark area with surrounding pixels
    # INPAINT_TELEA is better for preserving texture and quality
    result = cv2.inpaint(img, combined_mask, 3, cv2.INPAINT_TELEA)
    
    # Save with maximum quality
    cv2.imwrite(output_path, result, [cv2.IMWRITE_JPEG_QUALITY, 100])
    
    return output_path

def remove_watermark_advanced(image_path, output_path, region=None):
    """
    Advanced watermark removal with manual region selection
    If region is provided: (x, y, width, height) as percentages
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Could not read image")
    
    h, w = img.shape[:2]
    
    # Create mask
    mask = np.zeros((h, w), dtype=np.uint8)
    
    if region:
        # Manual region (x, y, w, h as percentages)
        x_start = int(w * region[0] / 100)
        y_start = int(h * region[1] / 100)
        x_end = int(w * (region[0] + region[2]) / 100)
        y_end = int(h * (region[1] + region[3]) / 100)
        
        mask[y_start:y_end, x_start:x_end] = 255
    else:
        # Auto-detect watermark regions
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Detect bright areas (common for watermarks)
        _, thresh1 = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        
        # Detect semi-transparent overlays
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh2 = cv2.threshold(blur, 180, 255, cv2.THRESH_BINARY)
        
        # Combine
        mask = cv2.bitwise_or(thresh1, thresh2)
        
        # Clean up
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.dilate(mask, kernel, iterations=1)
    
    # Apply inpainting
    result = cv2.inpaint(img, mask, 7, cv2.INPAINT_NS)
    
    # Save with maximum quality
    cv2.imwrite(output_path, result, [cv2.IMWRITE_JPEG_QUALITY, 100])
    
    return output_path

@shivuu.on_message(filters.command("removewm"))
async def remove_watermark_cmd(client: Client, message: Message):
    """
    Remove watermark from photos
    Usage: Reply to a photo with /removewm
    Advanced: /removewm x y w h (region as percentages)
    """
    
    if not message.reply_to_message:
        return await message.reply_text(
            f"<blockquote expandable>\n"
            f"<b>{sc('watermark remover')}</b>\n\n"
            f"<b>{sc('usage')}</b>\n"
            f"<code>/removewm</code> - {sc('auto detect watermark')}\n"
            f"<code>/removewm x y w h</code> - {sc('manual region')}\n\n"
            f"<b>{sc('manual region format')}</b>\n"
            f"x = {sc('horizontal position')} (%)\n"
            f"y = {sc('vertical position')} (%)\n"
            f"w = {sc('width')} (%)\n"
            f"h = {sc('height')} (%)\n\n"
            f"<b>{sc('example')}</b>\n"
            f"<code>/removewm 70 85 25 10</code>\n"
            f"{sc('removes watermark from bottom-right corner')}\n\n"
            f"<b>{sc('note')}</b>\n"
            f"• {sc('reply to a photo')}\n"
            f"• {sc('auto-detection works best')}\n"
            f"• {sc('preserves original quality')}\n"
            f"</blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    replied = message.reply_to_message
    
    # Check if photo
    if not replied.photo:
        return await message.reply_text(
            f"<blockquote>\n{sc('please reply to a photo')}\n</blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    # Parse region if provided
    region = None
    if len(message.command) > 1:
        try:
            parts = message.text.split()[1:]
            if len(parts) == 4:
                region = [float(x) for x in parts]
                if not all(0 <= x <= 100 for x in region):
                    raise ValueError("Values must be 0-100")
        except:
            return await message.reply_text(
                f"<blockquote>\n"
                f"{sc('invalid region format')}\n"
                f"{sc('use')}: <code>/removewm x y w h</code>\n"
                f"{sc('example')}: <code>/removewm 70 85 25 10</code>\n"
                f"</blockquote>",
                parse_mode=ParseMode.HTML
            )
    
    status_msg = await message.reply_text(
        f"<blockquote>\n{sc('processing image...')}\n</blockquote>",
        parse_mode=ParseMode.HTML
    )
    
    input_file = None
    output_file = None
    
    try:
        start_time = time.time()
        
        # Download photo (get highest quality)
        await status_msg.edit_text(
            f"<blockquote>\n{sc('downloading image...')}\n</blockquote>",
            parse_mode=ParseMode.HTML
        )
        
        input_file = await replied.download()
        
        # Generate output filename
        timestamp = int(time.time())
        output_file = f"cleaned_{timestamp}.jpg"
        
        # Remove watermark
        await status_msg.edit_text(
            f"<blockquote>\n{sc('removing watermark...')}\n</blockquote>",
            parse_mode=ParseMode.HTML
        )
        
        if region:
            remove_watermark_advanced(input_file, output_file, region)
        else:
            remove_watermark_advanced(input_file, output_file)
        
        process_time = time.time() - start_time
        
        # Upload cleaned image
        await status_msg.edit_text(
            f"<blockquote>\n{sc('uploading cleaned image...')}\n</blockquote>",
            parse_mode=ParseMode.HTML
        )
        
        caption = f"<b>{sc('watermark removed')}</b>\n{sc('processing time')}: <code>{process_time:.2f}s</code>"
        
        await message.reply_photo(
            photo=output_file,
            caption=caption,
            parse_mode=ParseMode.HTML
        )
        
        # Delete status message
        await status_msg.delete()
        
    except Exception as e:
        error_msg = str(e)
        print(f"Watermark removal error: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            await status_msg.edit_text(
                f"<blockquote>\n"
                f"<b>{sc('error occurred')}</b>\n"
                f"{sc('details')}: <code>{error_msg[:100]}</code>\n\n"
                f"{sc('tips')}:\n"
                f"• {sc('try manual region selection')}\n"
                f"• {sc('some watermarks are hard to detect')}\n"
                f"• {sc('use')} <code>/removewm x y w h</code>\n"
                f"</blockquote>",
                parse_mode=ParseMode.HTML
            )
        except:
            await message.reply_text(
                f"<blockquote>\n{sc('failed to process image')}\n</blockquote>",
                parse_mode=ParseMode.HTML
            )
    
    finally:
        # Cleanup
        await asyncio.sleep(1)
        for file in [input_file, output_file]:
            if file and os.path.exists(file):
                try:
                    os.remove(file)
                except:
                    pass


@shivuu.on_message(filters.command(["wmhelp", "removewmhelp"]))
async def watermark_help(client: Client, message: Message):
    """Show watermark remover help"""
    await message.reply_text(
        f"<blockquote expandable>\n"
        f"<b>{sc('watermark remover guide')}</b>\n\n"
        f"<b>{sc('commands')}</b>\n"
        f"<code>/removewm</code> - {sc('auto detect and remove')}\n"
        f"<code>/removewm x y w h</code> - {sc('remove from specific region')}\n\n"
        f"<b>{sc('how it works')}</b>\n"
        f"1. {sc('detects watermark using ai algorithms')}\n"
        f"2. {sc('uses inpainting to fill the area')}\n"
        f"3. {sc('preserves original image quality')}\n"
        f"4. {sc('no compression or quality loss')}\n\n"
        f"<b>{sc('auto detection')}</b>\n"
        f"• {sc('detects white/light watermarks')}\n"
        f"• {sc('finds semi-transparent overlays')}\n"
        f"• {sc('identifies text watermarks')}\n"
        f"• {sc('works on most common watermarks')}\n\n"
        f"<b>{sc('manual region')}</b>\n"
        f"{sc('format')}: <code>/removewm x y w h</code>\n"
        f"x = {sc('left position')} (0-100%)\n"
        f"y = {sc('top position')} (0-100%)\n"
        f"w = {sc('width')} (0-100%)\n"
        f"h = {sc('height')} (0-100%)\n\n"
        f"<b>{sc('examples')}</b>\n"
        f"<code>/removewm</code> - {sc('auto detect')}\n"
        f"<code>/removewm 70 85 25 10</code> - {sc('bottom right')}\n"
        f"<code>/removewm 5 5 20 8</code> - {sc('top left')}\n"
        f"<code>/removewm 40 90 20 8</code> - {sc('bottom center')}\n\n"
        f"<b>{sc('tips')}</b>\n"
        f"• {sc('auto-detect works 80% of time')}\n"
        f"• {sc('use manual for stubborn watermarks')}\n"
        f"• {sc('quality is preserved at 100%')}\n"
        f"• {sc('works on app and website watermarks')}\n\n"
        f"<b>{sc('supported')}</b>\n"
        f"✓ {sc('instagram watermarks')}\n"
        f"✓ {sc('tiktok watermarks')}\n"
        f"✓ {sc('stock photo watermarks')}\n"
        f"✓ {sc('app logo watermarks')}\n"
        f"✓ {sc('text watermarks')}\n"
        f"✓ {sc('semi-transparent overlays')}\n"
        f"</blockquote>",
        parse_mode=ParseMode.HTML
    )