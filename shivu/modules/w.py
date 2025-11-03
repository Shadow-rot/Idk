from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from shivu import shivuu
import os
import time
import asyncio

# Test print to confirm module is loaded
print("✓ Watermark remover module loaded")

def sc(text):
    """Small caps converter"""
    m = {'a':'ᴀ','b':'ʙ','c':'ᴄ','d':'ᴅ','e':'ᴇ','f':'ғ','g':'ɢ','h':'ʜ','i':'ɪ','j':'ᴊ','k':'ᴋ','l':'ʟ','m':'ᴍ','n':'ɴ','o':'ᴏ','p':'ᴘ','q':'ǫ','r':'ʀ','s':'s','t':'ᴛ','u':'ᴜ','v':'ᴠ','w':'ᴡ','x':'x','y':'ʏ','z':'ᴢ'}
    return ''.join(m.get(c.lower(), c) for c in text)

def remove_watermark_simple(image_path, output_path, region=None):
    """Simplified watermark removal"""
    try:
        import cv2
        import numpy as np
        from PIL import Image
        
        # Load image
        img = cv2.imread(image_path)
        if img is None:
            pil_img = Image.open(image_path).convert('RGB')
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        
        h, w = img.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        
        if region and len(region) == 4:
            # Manual region
            x_p, y_p, w_p, h_p = region
            x = int(w * x_p / 100)
            y = int(h * y_p / 100)
            width = int(w * w_p / 100)
            height = int(h * h_p / 100)
            
            x = max(0, min(x, w-1))
            y = max(0, min(y, h-1))
            x2 = min(x + width, w)
            y2 = min(y + height, h)
            
            mask[y:y2, x:x2] = 255
        else:
            # Auto-detect
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, bright = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
            _, dark = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
            mask = cv2.bitwise_or(bright, dark)
            
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        if np.count_nonzero(mask) == 0:
            cv2.imwrite(output_path, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
            return output_path, False
        
        result = cv2.inpaint(img, mask, 7, cv2.INPAINT_TELEA)
        cv2.imwrite(output_path, result, [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        return output_path, True
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise


# SIMPLER HANDLER - No filters.reply requirement
@shivuu.on_message(filters.command("removewm"))
async def remove_watermark_cmd(client: Client, message: Message):
    """Remove watermark - handler registered"""
    
    # DEBUG: Print when command is triggered
    print(f"\n{'='*50}")
    print(f"✓ /removewm command triggered!")
    print(f"User: {message.from_user.id if message.from_user else 'Unknown'}")
    print(f"Chat: {message.chat.id}")
    print(f"Text: {message.text}")
    print(f"Has reply: {message.reply_to_message is not None}")
    print(f"{'='*50}\n")
    
    # Check for reply
    if not message.reply_to_message:
        print("No reply detected, sending help")
        return await message.reply_text(
            f"<b>{sc('watermark remover')}</b>\n\n"
            f"<b>{sc('usage')}:</b>\n"
            f"• Reply to a photo with <code>/removewm</code>\n"
            f"• <code>/removewm x y w h</code> for manual region\n\n"
            f"<b>{sc('examples')}:</b>\n"
            f"<code>/removewm</code> - auto detect\n"
            f"<code>/removewm 70 85 25 10</code> - bottom right\n"
            f"<code>/removewm 5 5 20 8</code> - top left",
            parse_mode=ParseMode.HTML
        )
    
    replied = message.reply_to_message
    
    # Check for photo
    if not replied.photo:
        print("Replied message has no photo")
        return await message.reply_text(
            f"❌ {sc('please reply to a photo')}",
            parse_mode=ParseMode.HTML
        )
    
    print(f"Photo found: {replied.photo.file_id}")
    
    # Parse region
    region = None
    try:
        if len(message.command) > 1:
            parts = message.text.split()[1:]
            if len(parts) == 4:
                region = [float(x) for x in parts]
                if not all(0 <= x <= 100 for x in region):
                    raise ValueError()
                print(f"Manual region: {region}")
    except:
        return await message.reply_text(
            f"❌ {sc('invalid format')}\n{sc('use')}: <code>/removewm x y w h</code>",
            parse_mode=ParseMode.HTML
        )
    
    status = await message.reply_text(f"⏳ {sc('processing...')}")
    
    input_file = None
    output_file = None
    
    try:
        print("Starting download...")
        start = time.time()
        
        # Download
        input_file = await replied.download(file_name=f"wm_input_{int(time.time())}.jpg")
        print(f"Downloaded to: {input_file}")
        
        if not os.path.exists(input_file):
            raise Exception("Download failed - file not found")
        
        await status.edit_text(f"⏳ {sc('removing watermark...')}")
        
        # Process
        output_file = f"wm_output_{int(time.time())}.jpg"
        print(f"Processing: {input_file} -> {output_file}")
        
        output_path, found = remove_watermark_simple(input_file, output_file, region)
        
        if not os.path.exists(output_file):
            raise Exception("Processing failed - output not created")
        
        process_time = time.time() - start
        print(f"Processing completed in {process_time:.2f}s")
        
        await status.edit_text(f"⏳ {sc('uploading...')}")
        
        # Upload
        caption = (
            f"<b>✓ {sc('watermark removed')}</b>\n"
            f"⏱ {sc('time')}: <code>{process_time:.2f}s</code>"
        )
        
        if not found and not region:
            caption += f"\n\n💡 {sc('no watermark detected automatically')}"
        
        await message.reply_photo(
            photo=output_file,
            caption=caption,
            parse_mode=ParseMode.HTML
        )
        
        print("Upload successful!")
        await status.delete()
        
    except Exception as e:
        error = str(e)
        print(f"ERROR: {error}")
        import traceback
        traceback.print_exc()
        
        try:
            await status.edit_text(
                f"❌ <b>{sc('error')}</b>\n"
                f"<code>{error[:150]}</code>\n\n"
                f"💡 {sc('tips')}:\n"
                f"• {sc('try manual region')}\n"
                f"• {sc('use')}: <code>/removewm x y w h</code>",
                parse_mode=ParseMode.HTML
            )
        except:
            await message.reply_text(f"❌ {sc('processing failed')}")
    
    finally:
        # Cleanup
        await asyncio.sleep(2)
        for f in [input_file, output_file]:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                    print(f"Cleaned up: {f}")
                except Exception as e:
                    print(f"Cleanup failed for {f}: {e}")


# Simple test command to verify bot is working
@shivuu.on_message(filters.command("wmtest"))
async def test_handler(client: Client, message: Message):
    """Test if handlers are working"""
    print("✓ /wmtest command received and working!")
    await message.reply_text(
        f"✅ <b>{sc('bot is working!')}</b>\n\n"
        f"Handler registration: <code>OK</code>\n"
        f"Message processing: <code>OK</code>\n\n"
        f"{sc('you can now use')} /removewm",
        parse_mode=ParseMode.HTML
    )

print("✓ Handlers registered: /removewm, /wmtest")