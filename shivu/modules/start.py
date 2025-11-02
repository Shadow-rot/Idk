import random
from html import escape
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler

from shivu import application, SUPPORT_CHAT, BOT_USERNAME, db, GROUP_ID, LOGGER
from shivu import user_collection, user_totals_collection

# Import tracking function
from shivu.modules.chatlog import track_bot_start

REFERRER_REWARD = 1000
NEW_USER_BONUS = 500
VIDEO_URL = "https://files.catbox.moe/9i2vfh.mp4"


def sc(text):
    """Convert to small caps"""
    caps = {
        'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ',
        'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ',
        's': 's', 't': 'ᴛ', 'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
        'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ғ', 'G': 'ɢ', 'H': 'ʜ', 'I': 'ɪ',
        'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ', 'O': 'ᴏ', 'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ',
        'S': 's', 'T': 'ᴛ', 'U': 'ᴜ', 'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x', 'Y': 'ʏ', 'Z': 'ᴢ'
    }
    return ''.join(caps.get(c, c) for c in text)


async def process_referral(user_id: int, first_name: str, referring_user_id: int, context: CallbackContext):
    try:
        referring_user = await user_collection.find_one({"id": referring_user_id})
        if not referring_user or user_id == referring_user_id:
            return False
        new_user = await user_collection.find_one({"id": user_id})
        if new_user and new_user.get('referred_by'):
            return False

        await user_collection.update_one(
            {"id": user_id},
            {"$set": {"referred_by": referring_user_id}, "$inc": {"balance": NEW_USER_BONUS}}
        )
        await user_collection.update_one(
            {"id": referring_user_id},
            {
                "$inc": {
                    "balance": REFERRER_REWARD,
                    "referred_users": 1,
                    "pass_data.tasks.invites": 1
                },
                "$push": {"invited_user_ids": user_id}
            }
        )

        msg = f"<blockquote>{sc('referral complete')}\n{sc('agent')}::<b>{escape(first_name)}</b>\n{sc('reward')}::+{REFERRER_REWARD:,}ɢ</blockquote>"
        try:
            await context.bot.send_message(chat_id=referring_user_id, text=msg, parse_mode='HTML')
        except:
            pass
        return True
    except:
        return False


async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username
    args = context.args

    referring_user_id = None
    if args and len(args) > 0 and args[0].startswith('r_'):
        try:
            referring_user_id = int(args[0][2:])
        except:
            pass

    user_data = await user_collection.find_one({"id": user_id})
    is_new_user = user_data is None

    if is_new_user:
        new_user = {
            "id": user_id,
            "first_name": first_name,
            "username": username,
            "balance": NEW_USER_BONUS if referring_user_id else 500,
            "characters": [],
            "referred_users": 0,
            "referred_by": None,
            "invited_user_ids": [],
            "pass_data": {
                "tier": "free",
                "weekly_claims": 0,
                "tasks": {"invites": 0, "weekly_claims": 0, "grabs": 0}
            }
        }
        await user_collection.insert_one(new_user)
        user_data = new_user

        # Track AFTER inserting user so count is accurate
        await track_bot_start(user_id, first_name, username, is_new_user)

        if referring_user_id:
            await process_referral(user_id, first_name, referring_user_id, context)

    else:
        # Track returning user
        await track_bot_start(user_id, first_name, username, is_new_user)
        
        update_fields = {}
        if user_data.get('first_name') != first_name:
            update_fields['first_name'] = first_name
        if user_data.get('username') != username:
            update_fields['username'] = username
        if 'pass_data' not in user_data:
            update_fields['pass_data'] = {"tier": "free", "weekly_claims": 0, "tasks": {"invites": 0}}
        if update_fields:
            await user_collection.update_one({"id": user_id}, {"$set": update_fields})
            user_data = await user_collection.find_one({"id": user_id})

    user_balance = user_data.get('balance', 0)
    user_totals = await user_totals_collection.find_one({'id': user_id})
    total_characters = user_totals.get('count', 0) if user_totals else 0
    referred_count = user_data.get('referred_users', 0)

    if update.effective_chat.type == "private":
        caption = f"""<blockquote><b>{sc('system online')}</b>
{sc('balance')}::<code>{user_balance:,}</code>ɢ
{sc('characters')}::<code>{total_characters}</code>
{sc('referrals')}::<code>{referred_count}</code></blockquote>"""

        keyboard = [
            [InlineKeyboardButton(sc("add to group"), url=f'https://t.me/{BOT_USERNAME}?startgroup=new')],
            [InlineKeyboardButton(sc("help"), callback_data='hlp_mn'), InlineKeyboardButton(sc("referral"), callback_data='ref_mn')],
            [InlineKeyboardButton(sc("credits"), callback_data='crd_mn')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        video_html = f'<a href="{VIDEO_URL}">&#8205;</a>'
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=video_html + caption,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        caption = f"<blockquote><b>{sc('system online')}</b>\n{sc('initiate pm for access')}</blockquote>"
        keyboard = [
            [InlineKeyboardButton(sc("start"), url=f'https://t.me/{BOT_USERNAME}?start=new')],
            [InlineKeyboardButton(sc("help"), callback_data='hlp_gp')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        video_html = f'<a href="{VIDEO_URL}">&#8205;</a>'
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=video_html + caption,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )


async def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_data = await user_collection.find_one({"id": user_id})
    if not user_data:
        await query.answer(sc("start bot first"), show_alert=True)
        return

    user_totals = await user_totals_collection.find_one({'id': user_id})

    if query.data == 'hlp_mn':
        video_html = f'<a href="{VIDEO_URL}">&#8205;</a>'
        text = f"""{video_html}<blockquote><b>{sc('help module')}</b>
/grab::{sc('guess character')}
/fav::{sc('set favorite')}
/harem::{sc('collection')}
/trade::{sc('exchange')}
/bal::{sc('balance')}
/claim::{sc('daily rewards')}
/pass::{sc('pass status')}</blockquote>"""
        keyboard = [[InlineKeyboardButton(sc("back"), callback_data='bck_mn')]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    elif query.data == 'ref_mn':
        referral_link = f"https://t.me/{BOT_USERNAME}?start=r_{user_id}"
        referred_count = user_data.get('referred_users', 0)
        total_earnings = referred_count * REFERRER_REWARD

        video_html = f'<a href="{VIDEO_URL}">&#8205;</a>'
        text = f"""{video_html}<blockquote><b>{sc('referral network')}</b>
{sc('referrals')}::<code>{referred_count}</code>
{sc('earned')}::<code>{total_earnings:,}</code>ɢ
{sc('you get')}::<code>{REFERRER_REWARD:,}</code>ɢ
{sc('friend gets')}::<code>{NEW_USER_BONUS:,}</code>ɢ

<code>{referral_link}</code></blockquote>"""
        keyboard = [
            [InlineKeyboardButton(sc("share"), url=f"https://t.me/share/url?url={referral_link}")],
            [InlineKeyboardButton(sc("back"), callback_data='bck_mn')]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    elif query.data == 'crd_mn':
        video_html = f'<a href="{VIDEO_URL}">&#8205;</a>'
        text = f"{video_html}<blockquote><b>{sc('credits')}</b>\n{sc('system by dedicated team')}</blockquote>"
        keyboard = [
            [InlineKeyboardButton(sc("owner"), callback_data='own_vw')],
            [InlineKeyboardButton(sc("sudo"), callback_data='sud_ls')],
            [InlineKeyboardButton(sc("back"), callback_data='bck_mn')]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    elif query.data == 'sud_ls':
        video_html = f'<a href="{VIDEO_URL}">&#8205;</a>'
        text = f"{video_html}<blockquote><b>{sc('sudo roster')}</b></blockquote>"
        keyboard = [
            [InlineKeyboardButton("ʏᴏɪᴄʜɪ ɪsᴀɢɪ", url='https://t.me/ll_Yoichi_Isagi_ll')],
            [InlineKeyboardButton("ᴋᴀɪᴢᴇɴ", url='https://t.me/digital_paradoxx')],
            [InlineKeyboardButton("ᴋɪʟʟᴜᴀ", url='https://t.me/notkilluafr')],
            [InlineKeyboardButton("sʜɪᴋᴍᴏʀ", url='https://t.me/avinashs_sun')],
            [InlineKeyboardButton(sc("back"), callback_data='crd_mn')]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    elif query.data == 'own_vw':
        video_html = f'<a href="{VIDEO_URL}">&#8205;</a>'
        text = f"{video_html}<blockquote><b>{sc('owner profile')}</b></blockquote>"
        keyboard = [
            [InlineKeyboardButton("ᴛʜᴏʀғɪɴɴ", url='https://t.me/ll_Thorfinn_ll')],
            [InlineKeyboardButton(sc("back"), callback_data='crd_mn')]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    elif query.data == 'bck_mn':
        user_balance = user_data.get('balance', 0)
        total_characters = user_totals.get('count', 0) if user_totals else 0
        referred_count = user_data.get('referred_users', 0)

        video_html = f'<a href="{VIDEO_URL}">&#8205;</a>'
        text = f"""{video_html}<blockquote><b>{sc('system online')}</b>
{sc('balance')}::<code>{user_balance:,}</code>ɢ
{sc('characters')}::<code>{total_characters}</code>
{sc('referrals')}::<code>{referred_count}</code></blockquote>"""

        keyboard = [
            [InlineKeyboardButton(sc("add to group"), url=f'https://t.me/{BOT_USERNAME}?startgroup=new')],
            [InlineKeyboardButton(sc("help"), callback_data='hlp_mn'), InlineKeyboardButton(sc("referral"), callback_data='ref_mn')],
            [InlineKeyboardButton(sc("credits"), callback_data='crd_mn')]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')


application.add_handler(CommandHandler('start', start, block=False))
application.add_handler(CallbackQueryHandler(button_callback, block=False))

LOGGER.info("[START] futuristic UI loaded")