from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from shivu import shivuu
import os
import time
import asyncio

print("✓ Watermark remover module loaded")

def sc(text):
    """Small caps converter"""
    m = {'a':'ᴀ','b':'ʙ','c':'ᴄ','d':'ᴅ','e':'ᴇ','f':'ғ','g':'ɢ','h':'ʜ','i':'ɪ','j':'ᴊ','k':'ᴋ','l':'ʟ','m':'ᴍ','n':'ɴ','o':'ᴏ','p':'ᴘ','q':'ǫ','r':'ʀ','s':'s','t':'ᴛ','u':'ᴜ','v':'ᴠ','w':'ᴡ','x':'x','y':'ʏ','z':'ᴢ'}
    return ''.join(m.get(c.lower(), c) for c in text)


def enhance_image_quality(img):
    """
    Enhance image quality after watermark removal
    """
    import cv2
    import numpy as np
    
    # 1. Denoise while preserving edges
    denoised = cv2.fastNlMeansDenoisingColored(img, @shivuu.on_message(filters.command("removewm"))
async def remove_watermark_cmd(client: Client, message: Message):
    """Remove watermark from photos - REQUIRES manual region"""
    
    print(f"\n{'='*50}")
    print(f"✓ /removewm command triggered")
    print(f"{'='*50}\n")
    
    # Check for reply
    if not message.reply_to_message:
        return await message.reply_text(
            f"<blockquote expandable>\n"
            f"<b>{sc('watermark remover')}</b>\n\n"
            f"<b>{sc('usage')}:</b>\n"
            f"<code>/removewm x y w h</code>\n"
            f"<code>/removewm x y w h noenhance</code> - {sc('skip quality boost')}\n\n"
            f"<b>{sc('parameters')}:</b>\n"
            f"• <code>x</code> = {sc('horizontal position')} (0-100%)\n"
            f"• <code>y</code> = {sc('vertical position')} (0-100%)\n"
            f"• <code>w</code> = {sc('width')} (0-100%)\n"
            f"• <code>h</code> = {sc('height')} (0-100%)\n\n"
            f"<b>{sc('common positions')}:</b>\n"
            f"<code>/removewm 70 85 28 12</code> - {sc('bottom right')}\n"
            f"<code>/removewm 2 85 28 12</code> - {sc('bottom left')}\n"
            f"<code>/removewm 36 88 28 10</code> - {sc('bottom center')}\n"
            f"<code>/removewm 70 2 28 10</code> - {sc('top right')}\n"
            f"<code>/removewm 2 2 28 10</code> - {sc('top left')}\n\n"
            f"<b>{sc('tips')}:</b>\n"
            f"• {sc('reply to a photo')}\n"
            f"• {sc('quality enhancement enabled by default')}\n"
            f"• {sc('use exact coordinates for best results')}\n"
            f"• {sc('smaller region = better quality')}\n"
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
    
    # Parse region and enhancement flag
    region = None
    enhance = True
    
    if len(message.command) <= 1:
        return await message.reply_text(
            f"<blockquote>\n"
            f"❌ <b>{sc('region required')}</b>\n\n"
            f"{sc('specify watermark position')}:\n"
            f"<code>/removewm x y w h</code>\n\n"
            f"<b>{sc('examples')}:</b>\n"
            f"<code>/removewm 70 85 28 12</code>\n"
            f"<code>/removewm 2 85 28 12</code>\n"
            f"<code>/removewm 36 88 28 10</code>\n"
            f"</blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    try:
        parts = message.text.split()[1:]
        
        # Check for "noenhance" flag
        if "noenhance" in [p.lower() for p in parts]:
            enhance = False
            parts = [p for p in parts if p.lower() != "noenhance"]
        
        if len(parts) != 4:
            raise ValueError("Need exactly 4 values")
        
        region = [float(x) for x in parts]
        
        # Validate range
        if not all(0 <= x <= 100 for x in region):
            raise ValueError("Values must be between 0-100")
        
        # Validate region size (not too large)
        if region[2] > 50 or region[3] > 50:
            return await message.reply_text(
                f"⚠️ {sc('region too large')}\n\n"
                f"{sc('width and height should be < 50%')}\n"
                f"{sc('current')}: w={region[2]}%, h={region[3]}%\n\n"
                f"{sc('use smaller region for better quality')}",
                parse_mode=ParseMode.HTML
            )
        
        print(f"Region: {region}, Enhance: {enhance}")
        
    except Exception as e:
        return await message.reply_text(
            f"<blockquote>\n"
            f"❌ {sc('invalid format')}\n\n"
            f"{sc('use')}: <code>/removewm x y w h</code>\n"
            f"{sc('example')}: <code>/removewm 70 85 28 12</code>\n\n"
            f"{sc('all values must be numbers 0-100')}\n"
            f"</blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    status = await message.reply_text(f"⏳ {sc('processing...')}")
    
    input_file = None
    output_file = None
    
    try:
        start = time.time()
        
        # Downloa, 10, 10, 7, 21)
    
    # 2. Sharpen slightly
    kernel_sharpening = np.array([[-1,-1,-1], 
                                   [-1, 9,-1], 
                                   [-1,-1,-1]])
    sharpened = cv2.filter2D(denoised, -1, kernel_sharpening * 0.3)
    
    # 3. Enhance contrast slightly
    lab = cv2.cvtColor(sharpened, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    l = clahe.apply(l)
    enhanced = cv2.merge([l, a, b])
    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
    
    return enhanced


def remove_watermark_accurate(image_path, output_path, region=None, enhance=True):
    """
    Accurate watermark removal with minimal photo damage
    Only removes from specified region - NO auto-detection
    """
    try:
        import cv2
        import numpy as np
        
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            from PIL import Image
            pil_img = Image.open(image_path).convert('RGB')
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        
        h, w = img.shape[:2]
        print(f"Image size: {w}x{h}")
        
        # ONLY process if manual region is specified
        if not region or len(region) != 4:
            # No region specified - just save original with optional enhancement
            print("No region specified")
            if enhance:
                print("Applying quality enhancement only...")
                img = enhance_image_quality(img)
            cv2.imwrite(output_path, img, [cv2.IMWRITE_JPEG_QUALITY, 100])
            return output_path, False
        
        # Manual region specified
        x_p, y_p, w_p, h_p = region
        
        # Calculate pixel coordinates
        x = int(w * x_p / 100)
        y = int(h * y_p / 100)
        width = int(w * w_p / 100)
        height = int(h * h_p / 100)
        
        # Bounds check
        x = max(0, min(x, w - 10))
        y = max(0, min(y, h - 10))
        x2 = min(x + width, w)
        y2 = min(y + height, h)
        
        # Make sure region is valid
        if x2 <= x or y2 <= y:
            print("Invalid region, returning original")
            cv2.imwrite(output_path, img, [cv2.IMWRITE_JPEG_QUALITY, 100])
            return output_path, False
        
        print(f"Processing region: ({x},{y}) to ({x2},{y2})")
        
        # Create mask - ONLY for the specified region
        mask = np.zeros((h, w), dtype=np.uint8)
        mask[y:y2, x:x2] = 255
        
        # Add small border to mask for smoother blending
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=1)
        
        # Use INPAINT_TELEA for better quality and texture preservation
        # Smaller radius = less aggressive = better quality
        result = cv2.inpaint(img, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
        
        # Apply quality enhancement if enabled
        if enhance:
            print("Enhancing image quality...")
            result = enhance_image_quality(result)
        
        # Save with maximum quality - NO compression
        cv2.imwrite(output_path, result, [
            cv2.IMWRITE_JPEG_QUALITY, 100,
            cv2.IMWRITE_JPEG_OPTIMIZE, 1
        ])
        
        print("Processing complete")
        return output_path, True
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise Exception(f"Processing failed: {str(e)}")


@shivuu.on_message(filters.command("removewm"))
async def remove_watermark_cmd(client: Client, message: Message):
    """Remove watermark from photos - REQUIRES manual region"""
    
    print(f"\n{'='*50}")
    print(f"✓ /removewm command triggered")
    print(f"{'='*50}\n")
    
    # Check for reply
    if not message.reply_to_message:
        return await message.reply_text(
            f"<blockquote expandable>\n"
            f"<b>{sc('watermark remover')}</b>\n\n"
            f"<b>{sc('usage')}:</b>\n"
            f"<code>/removewm x y w h</code>\n\n"
            f"<b>{sc('parameters')}:</b>\n"
            f"• <code>x</code> = {sc('horizontal position')} (0-100%)\n"
            f"• <code>y</code> = {sc('vertical position')} (0-100%)\n"
            f"• <code>w</code> = {sc('width')} (0-100%)\n"
            f"• <code>h</code> = {sc('height')} (0-100%)\n\n"
            f"<b>{sc('common positions')}:</b>\n"
            f"<code>/removewm 70 85 28 12</code> - {sc('bottom right')}\n"
            f"<code>/removewm 2 85 28 12</code> - {sc('bottom left')}\n"
            f"<code>/removewm 36 88 28 10</code> - {sc('bottom center')}\n"
            f"<code>/removewm 70 2 28 10</code> - {sc('top right')}\n"
            f"<code>/removewm 2 2 28 10</code> - {sc('top left')}\n\n"
            f"<b>{sc('tips')}:</b>\n"
            f"• {sc('reply to a photo')}\n"
            f"• {sc('use exact coordinates for best results')}\n"
            f"• {sc('smaller region = better quality')}\n"
            f"• {sc('no auto-detection to prevent damage')}\n"
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
    
    # Parse region - REQUIRED
    region = None
    
    if len(message.command) <= 1:
        return await message.reply_text(
            f"<blockquote>\n"
            f"❌ <b>{sc('region required')}</b>\n\n"
            f"{sc('specify watermark position')}:\n"
            f"<code>/removewm x y w h</code>\n\n"
            f"<b>{sc('examples')}:</b>\n"
            f"<code>/removewm 70 85 28 12</code>\n"
            f"<code>/removewm 2 85 28 12</code>\n"
            f"<code>/removewm 36 88 28 10</code>\n"
            f"</blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    try:
        parts = message.text.split()[1:]
        if len(parts) != 4:
            raise ValueError("Need exactly 4 values")
        
        region = [float(x) for x in parts]
        
        # Validate range
        if not all(0 <= x <= 100 for x in region):
            raise ValueError("Values must be between 0-100")
        
        # Validate region size (not too large)
        if region[2] > 50 or region[3] > 50:
            return await message.reply_text(
                f"⚠️ {sc('region too large')}\n\n"
                f"{sc('width and height should be < 50%')}\n"
                f"{sc('current')}: w={region[2]}%, h={region[3]}%\n\n"
                f"{sc('use smaller region for better quality')}",
                parse_mode=ParseMode.HTML
            )
        
        print(f"Region parsed: {region}")
        
    except Exception as e:
        return await message.reply_text(
            f"<blockquote>\n"
            f"❌ {sc('invalid format')}\n\n"
            f"{sc('use')}: <code>/removewm x y w h</code>\n"
            f"{sc('example')}: <code>/removewm 70 85 28 12</code>\n\n"
            f"{sc('all values must be numbers 0-100')}\n"
            f"</blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    status = await message.reply_text(f"⏳ {sc('processing...')}")
    
    input_file = None
    output_file = None
    
    try:
        start = time.time()
        
        # Download
        await status.edit_text(f"📥 {sc('downloading image...')}")
        input_file = await replied.download(file_name=f"wm_input_{int(time.time())}.jpg")
        print(f"Downloaded: {input_file}")
        
        # Process
        await status.edit_text(f"🔧 {sc('removing watermark...')}")
        output_file = f"wm_output_{int(time.time())}.jpg"
        
        output_path, success = remove_watermark_accurate(input_file, output_file, region)
        
        if not success:
            raise Exception("Processing failed or no region specified")
        
        process_time = time.time() - start
        
        # Upload
        await status.edit_text(f"📤 {sc('uploading...')}")
        
        caption = (
            f"<b>✅ {sc('watermark removed')}</b>\n\n"
            f"📍 {sc('region')}: <code>{region[0]:.0f},{region[1]:.0f} ({region[2]:.0f}×{region[3]:.0f}%)</code>\n"
            f"⏱️ {sc('time')}: <code>{process_time:.2f}s</code>\n"
            f"🎨 {sc('quality')}: <code>100%</code>"
        )
        
        await message.reply_photo(
            photo=output_file,
            caption=caption,
            parse_mode=ParseMode.HTML
        )
        
        await status.delete()
        print("Upload complete")
        
    except Exception as e:
        error = str(e)
        print(f"ERROR: {error}")
        import traceback
        traceback.print_exc()
        
        try:
            await status.edit_text(
                f"<blockquote>\n"
                f"❌ <b>{sc('error occurred')}</b>\n\n"
                f"<code>{error[:150]}</code>\n\n"
                f"💡 {sc('tips')}:\n"
                f"• {sc('check region coordinates')}\n"
                f"• {sc('use smaller region')}\n"
                f"• {sc('try different position')}\n"
                f"</blockquote>",
                parse_mode=ParseMode.HTML
            )
        except:
            await message.reply_text(f"❌ {sc('processing failed')}")
    
    finally:
        await asyncio.sleep(3)
        for f in [input_file, output_file]:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                    print(f"Cleaned: {f}")
                except:
                    pass


@shivuu.on_message(filters.command("wmhelp"))
async def watermark_help(client: Client, message: Message):
    """Detailed help for watermark remover"""
    await message.reply_photo(
        photo="https://i.imgur.com/example.jpg",  # You can add a diagram here
        caption=f"<blockquote expandable>\n"
        f"<b>{sc('watermark remover guide')}</b>\n\n"
        f"<b>{sc('how to use')}:</b>\n"
        f"1. Reply to a photo\n"
        f"2. Type <code>/removewm x y w h</code>\n"
        f"3. Wait for result\n\n"
        f"<b>{sc('understanding coordinates')}:</b>\n"
        f"• <code>x</code> = {sc('distance from left edge')} (0-100%)\n"
        f"• <code>y</code> = {sc('distance from top edge')} (0-100%)\n"
        f"• <code>w</code> = {sc('width of watermark')} (0-100%)\n"
        f"• <code>h</code> = {sc('height of watermark')} (0-100%)\n\n"
        f"<b>{sc('coordinate examples')}:</b>\n\n"
        f"<b>{sc('bottom right')}:</b>\n"
        f"<code>/removewm 70 85 28 12</code>\n"
        f"<code>/removewm 75 88 23 10</code>\n\n"
        f"<b>{sc('bottom left')}:</b>\n"
        f"<code>/removewm 2 85 28 12</code>\n"
        f"<code>/removewm 1 88 25 10</code>\n\n"
        f"<b>{sc('bottom center')}:</b>\n"
        f"<code>/removewm 36 88 28 10</code>\n"
        f"<code>/removewm 40 90 20 8</code>\n\n"
        f"<b>{sc('top right')}:</b>\n"
        f"<code>/removewm 70 2 28 10</code>\n"
        f"<code>/removewm 75 1 23 8</code>\n\n"
        f"<b>{sc('top left')}:</b>\n"
        f"<code>/removewm 2 2 28 10</code>\n"
        f"<code>/removewm 1 1 25 8</code>\n\n"
        f"<b>{sc('pro tips')}:</b>\n"
        f"• {sc('start with larger region, then refine')}\n"
        f"• {sc('keep width/height under 30% for best quality')}\n"
        f"• {sc('small adjustments make big difference')}\n"
        f"• {sc('no auto-detect = no accidental damage')}\n"
        f"• {sc('quality preserved at 100%')}\n\n"
        f"<b>{sc('common apps')}:</b>\n"
        f"TikTok: <code>/removewm 72 86 26 12</code>\n"
        f"Instagram: <code>/removewm 2 88 28 10</code>\n"
        f"Snapchat: <code>/removewm 40 90 20 8</code>\n"
        f"</blockquote>",
        parse_mode=ParseMode.HTML
    )


@shivuu.on_message(filters.command("enhance"))
async def enhance_quality_cmd(client: Client, message: Message):
    """Enhance image quality - upscale, sharpen, denoise"""
    
    print(f"\n{'='*50}")
    print(f"✓ /enhance command triggered")
    print(f"{'='*50}\n")
    
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
        print(f"Downloaded: {input_file}")
        
        # Load image
        await status.edit_text(f"🔧 {sc('processing...')}")
        img = cv2.imread(input_file)
        if img is None:
            from PIL import Image
            pil_img = Image.open(input_file).convert('RGB')
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        
        h, w = img.shape[:2]
        print(f"Original size: {w}x{h}")
        
        # STAGE 1: Upscale using EDSR (2x)
        await status.edit_text(f"🔧 {sc('upscaling')} (1/4)...")
        sr = cv2.dnn_superres.DnnSuperResImpl_create()
        # Use EDSR for better quality (you can use ESPCN for faster processing)
        # Note: This requires model files. Using basic bicubic upscale instead
        upscaled = cv2.resize(img, (w*2, h*2), interpolation=cv2.INTER_CUBIC)
        print(f"Upscaled to: {upscaled.shape[1]}x{upscaled.shape[0]}")
        
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
        print(f"Enhancement complete in {process_time:.2f}s")
        
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
        print(f"ERROR: {error}")
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
                    print(f"Cleaned: {f}")
                except:
                    pass


@shivuu.on_message(filters.command("wmtest"))
async def test_handler(client: Client, message: Message):
    """Test command"""
    await message.reply_text(
        f"✅ <b>{sc('bot active')}</b>\n\n"
        f"📦 {sc('version')}: <code>v2.0</code>\n\n"
        f"<b>{sc('commands')}:</b>\n"
        f"• <code>/removewm x y w h</code> - {sc('remove watermark')}\n"
        f"• <code>/enhance</code> - {sc('boost quality')}\n"
        f"• <code>/wmhelp</code> - {sc('detailed help')}\n",
        parse_mode=ParseMode.HTML
    )

print("✓ Handlers registered: /removewm, /enhance")