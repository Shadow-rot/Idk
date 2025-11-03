from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from shivu import shivuu
import os
import time
import asyncio

def sc(text):
    """Small caps converter"""
    m = {'a':'ᴀ','b':'ʙ','c':'ᴄ','d':'ᴅ','e':'ᴇ','f':'ғ','g':'ɢ','h':'ʜ','i':'ɪ','j':'ᴊ','k':'ᴋ','l':'ʟ','m':'ᴍ','n':'ɴ','o':'ᴏ','p':'ᴘ','q':'ǫ','r':'ʀ','s':'s','t':'ᴛ','u':'ᴜ','v':'ᴠ','w':'ᴡ','x':'x','y':'ʏ','z':'ᴢ'}
    return ''.join(m.get(c.lower(), c) for c in text)


@shivuu.on_message(filters.command("enhance"))
async def enhance_quality_cmd(client: Client, message: Message):
    """Enhance image quality - upscale, sharpen, denoise"""
    
    # Check for reply
    if not message.reply_to_message:
        return await message.reply_text(
            f"<blockquote>\n"
            f"<b>{sc('quality enhancer')}</b>\n\n"
            f"<b>{sc('usage')}:</b>\n"
            f"{sc('reply to a photo with')} <code>/enhance</code>\n\n"
            f"<b>{sc('features')}:</b>\n"
            f"✓ {sc('reduce noise')}\n"
            f"✓ {sc('enhance sharpness')}\n"
            f"✓ {sc('improve contrast')}\n"
            f"✓ {sc('upscale resolution')}\n"
            f"✓ {sc('preserve details')}\n\n"
            f"<b>{sc('note')}:</b> {sc('works best on good quality photos')}\n"
            f"</blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    replied = message.reply_to_message
    
    # Check for photo
    if not replied.photo:
        return await message.reply_text(
            f"❌ {sc('please reply to a photo')}",
            parse_mode=ParseMode.HTML
        )
    
    status = await message.reply_text(f"⏳ {sc('enhancing quality...')}")
    
    input_file = None
    output_file = None
    
    try:
        import cv2
        import numpy as np
        
        start = time.time()
        
        # Download
        await status.edit_text(f"📥 {sc('downloading image...')}")
        input_file = await replied.download(file_name=f"enhance_input_{int(time.time())}.jpg")
        
        # Load image
        await status.edit_text(f"🔧 {sc('processing...')}")
        img = cv2.imread(input_file)
        if img is None:
            from PIL import Image
            pil_img = Image.open(input_file).convert('RGB')
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        
        h, w = img.shape[:2]
        
        # STAGE 1: Upscale (2x)
        await status.edit_text(f"🔧 {sc('upscaling')} (1/4)...")
        upscaled = cv2.resize(img, (w*2, h*2), interpolation=cv2.INTER_CUBIC)
        
        # STAGE 2: Denoise
        await status.edit_text(f"🔧 {sc('reducing noise')} (2/4)...")
        denoised = cv2.fastNlMeansDenoisingColored(upscaled, None, 10, 10, 7, 21)
        
        # STAGE 3: Sharpen
        await status.edit_text(f"🔧 {sc('sharpening')} (3/4)...")
        kernel_sharpening = np.array([[-1,-1,-1], 
                                       [-1, 9,-1], 
                                       [-1,-1,-1]])
        sharpened = cv2.filter2D(denoised, -1, kernel_sharpening * 0.4)
        
        # STAGE 4: Enhance contrast
        await status.edit_text(f"🔧 {sc('enhancing colors')} (4/4)...")
        lab = cv2.cvtColor(sharpened, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8,8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        result = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        # Save
        output_file = f"enhanced_{int(time.time())}.jpg"
        cv2.imwrite(output_file, result, [
            cv2.IMWRITE_JPEG_QUALITY, 100,
            cv2.IMWRITE_JPEG_OPTIMIZE, 1
        ])
        
        process_time = time.time() - start
        
        # Upload
        await status.edit_text(f"📤 {sc('uploading...')}")
        
        new_h, new_w = result.shape[:2]
        caption = (
            f"<b>✨ {sc('quality enhanced')}</b>\n\n"
            f"📐 {sc('resolution')}: <code>{w}×{h}</code> → <code>{new_w}×{new_h}</code>\n"
            f"📈 {sc('upscale')}: <code>2x</code>\n"
            f"⏱️ {sc('time')}: <code>{process_time:.2f}s</code>\n"
            f"🎨 {sc('quality')}: <code>100%</code>\n\n"
            f"<b>{sc('applied')}:</b>\n"
            f"✓ {sc('noise reduction')}\n"
            f"✓ {sc('sharpening')}\n"
            f"✓ {sc('contrast enhancement')}\n"
            f"✓ {sc('resolution upscale')}"
        )
        
        await message.reply_photo(
            photo=output_file,
            caption=caption,
            parse_mode=ParseMode.HTML
        )
        
        await status.delete()
        
    except Exception as e:
        error = str(e)
        import traceback
        traceback.print_exc()
        
        try:
            await status.edit_text(
                f"<blockquote>\n"
                f"❌ <b>{sc('enhancement failed')}</b>\n\n"
                f"<code>{error[:150]}</code>\n\n"
                f"💡 {sc('the photo might be too large or corrupted')}\n"
                f"</blockquote>",
                parse_mode=ParseMode.HTML
            )
        except:
            await message.reply_text(f"❌ {sc('enhancement failed')}")
    
    finally:
        await asyncio.sleep(3)
        for f in [input_file, output_file]:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass