import random
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, user_collection

VIDEOS = [
    "https://files.catbox.moe/25ntg5.mp4",
    "https://files.catbox.moe/1fx72l.mp4"
]

TIPS = [
    "ᴜsᴇ /claim ᴅᴀɪʟʏ ғᴏʀ ғʀᴇᴇ ɢᴏʟᴅ",
    "ɪɴᴠɪᴛᴇ ғʀɪᴇɴᴅs ᴛᴏ ᴇᴀʀɴ 1000 ɢᴏʟᴅ",
    "ᴘʟᴀʏ ɢᴀᴍᴇs ᴛᴏ ɪɴᴄʀᴇᴀsᴇ xᴘ",
    "ᴄᴏʟʟᴇᴄᴛ ʀᴀʀᴇ sʟᴀᴠᴇs ᴛᴏ ɢᴇᴛ ʀɪᴄʜ",
    "ᴜsᴇ /bal ᴛᴏ ᴄʜᴇᴄᴋ ʏᴏᴜʀ ᴡᴀʟʟᴇᴛ",
    "ᴛʀᴀᴅᴇ sʟᴀᴠᴇs ᴛᴏ ɢʀᴏᴡ ғᴀsᴛᴇʀ",
    "ᴄᴏᴍᴘʟᴇᴛᴇ ᴅᴀɪʟʏ ᴛᴀsᴋs ғᴏʀ ʙᴏɴᴜs",
    "ᴅᴇᴘᴏsɪᴛ ɪɴ ʙᴀɴᴋ ғᴏʀ 5% ɪɴᴛᴇʀᴇsᴛ",
    "ᴊᴏɪɴ ʀᴀɪᴅs ғᴏʀ ʙɪɢ ʀᴇᴡᴀʀᴅs"
]

async def get_balance(user_id):
    try:
        user = await user_collection.find_one({'id': user_id})
        return user.get('balance', 0) if user else 0
    except:
        return 0

def get_random_video():
    return random.choice(VIDEOS)

def main_keyboard(uid):
    return [
        [InlineKeyboardButton("ɢᴀᴍᴇs", callback_data=f'hlp_gm_{uid}'),
         InlineKeyboardButton("ᴇᴄᴏɴᴏᴍʏ", callback_data=f'hlp_ec_{uid}'),
         InlineKeyboardButton("sʟᴀᴠᴇs", callback_data=f'hlp_sl_{uid}')],
        [InlineKeyboardButton("ʙᴀɴᴋɪɴɢ", callback_data=f'hlp_bn_{uid}'),
         InlineKeyboardButton("ʀᴀɪᴅs", callback_data=f'hlp_rd_{uid}'),
         InlineKeyboardButton("sᴛᴏʀᴇ", callback_data=f'hlp_st_{uid}')],
        [InlineKeyboardButton("ᴘᴀss", callback_data=f'hlp_ps_{uid}'),
         InlineKeyboardButton("ɪɴғᴏ", callback_data=f'hlp_if_{uid}'),
         InlineKeyboardButton("ʟᴇᴀᴅᴇʀʙᴏᴀʀᴅ", callback_data=f'hlp_lb_{uid}')],
        [InlineKeyboardButton("ʀᴇᴡᴀʀᴅs", callback_data=f'hlp_rw_{uid}'),
         InlineKeyboardButton("ɢᴜɪᴅᴇ", callback_data=f'hlp_gd_{uid}'),
         InlineKeyboardButton("ᴛɪᴘs", callback_data=f'hlp_tp_{uid}')]
    ]

def back_keyboard(uid):
    return [[InlineKeyboardButton("ʙᴀᴄᴋ", callback_data=f'hlp_mn_{uid}'),
             InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data=f'hlp_cl_{uid}')]]

def main_caption(name, bal, video_url):
    return f"""<a href="{video_url}">&#8205;</a><blockquote>ʜᴇʟᴘ ᴄᴇɴᴛᴇʀ

ʜᴇʏ <code>{name}</code>
ɴᴇᴇᴅ ʜᴇʟᴘ? ᴄʜᴏᴏsᴇ ʙᴇʟᴏᴡ

ʙᴀʟᴀɴᴄᴇ: <code>{bal}</code>

{random.choice(TIPS)}</blockquote>"""

CATEGORIES = {
    'gm': lambda v: f"""<a href="{v}">&#8205;</a><blockquote>ɢᴀᴍᴇ ᴢᴏɴᴇ

ɢᴀᴍʙʟɪɴɢ:
<code>/sbet 10000 heads</code> - ᴄᴏɪɴ ᴛᴏss
<code>/roll 10000 even</code> - ᴅɪᴄᴇ ʀᴏʟʟ
<code>/gamble 10000 l</code> - ʟᴇғᴛ/ʀɪɢʜᴛ
<code>/slot 5000</code> - sʟᴏᴛ ᴍᴀᴄʜɪɴᴇ

sᴋɪʟʟ:
<code>/basket 5000</code> - ʙᴀsᴋᴇᴛʙᴀʟʟ
<code>/dart 2000</code> - ᴅᴀʀᴛ ɢᴀᴍᴇ

sᴘᴇᴄɪᴀʟ:
<code>/riddle</code> - sᴏʟᴠᴇ ᴀɴᴅ ᴇᴀʀɴ
<code>/stour</code> - sʟᴀᴠᴇ ᴄᴏɴᴛʀᴀᴄᴛs
<code>/quiz</code> - ᴛʀɪᴠɪᴀ ǫᴜᴇsᴛɪᴏɴs</blockquote>""",

    'ec': lambda v: f"""<a href="{v}">&#8205;</a><blockquote>ᴇᴄᴏɴᴏᴍʏ

ᴄʜᴇᴄᴋ ʙᴀʟᴀɴᴄᴇ:
<code>/bal</code> - ᴡᴀʟʟᴇᴛ ᴀɴᴅ ʙᴀɴᴋ
<code>/sinv</code> - ɪɴᴠᴇɴᴛᴏʀʏ
<code>/profile</code> - ғᴜʟʟ sᴛᴀᴛs

ᴛʀᴀɴsᴀᴄᴛɪᴏɴs:
<code>/pay @user 1000</code> - sᴇɴᴅ ɢᴏʟᴅ
<code>/claim</code> - ᴅᴀɪʟʏ 2000 ɢᴏʟᴅ
<code>/deposit 5000</code> - ʙᴀɴᴋ ᴅᴇᴘᴏsɪᴛ
<code>/withdraw 5000</code> - ʙᴀɴᴋ ᴡɪᴛʜᴅʀᴀᴡ

ғʀᴇᴇ ʀᴇᴡᴀʀᴅs:
<code>/daily</code> - ᴅᴀɪʟʏ ʙᴏɴᴜs
<code>/weekly</code> - ᴡᴇᴇᴋʟʏ ʙᴏɴᴜs</blockquote>""",

    'sl': lambda v: f"""<a href="{v}">&#8205;</a><blockquote>sʟᴀᴠᴇ ᴄᴏʟʟᴇᴄᴛɪᴏɴ

ᴄᴀᴛᴄʜɪɴɢ:
<code>/grab name</code> - ᴄᴀᴛᴄʜ sʟᴀᴠᴇ
sᴘᴀᴡɴs ᴇᴠᴇʀʏ 100 ᴍᴇssᴀɢᴇs

ᴠɪᴇᴡ ᴄᴏʟʟᴇᴄᴛɪᴏɴ:
<code>/harem</code> - ʏᴏᴜʀ sʟᴀᴠᴇs
<code>/slaves</code> - ᴀʟʟ sʟᴀᴠᴇs
<code>/smode</code> - sᴏʀᴛ ʙʏ ʀᴀɴᴋ
<code>/sinfo id</code> - sʟᴀᴠᴇ ᴅᴇᴛᴀɪʟs

ᴛʀᴀᴅɪɴɢ:
<code>/trade</code> - ᴛʀᴀᴅᴇ sʟᴀᴠᴇs
<code>/gift @user id</code> - ɢɪғᴛ sʟᴀᴠᴇ

ᴍᴀʀʀɪᴀɢᴇ:
<code>/propose</code> - ᴘʀᴏᴘᴏsᴇ ᴛᴏ sʟᴀᴠᴇ
<code>/marry</code> - ᴍᴀʀʀʏ sʟᴀᴠᴇ
<code>/dice</code> - ᴍᴀʀʀɪᴀɢᴇ ɢᴀᴍᴇ

sᴇᴀʀᴄʜ:
<code>/check id</code> - ᴄʜᴇᴄᴋ ᴄʜᴀʀᴀᴄᴛᴇʀ
<code>/find name</code> - ғɪɴᴅ ʙʏ ɴᴀᴍᴇ</blockquote>""",

    'bn': lambda v: f"""<a href="{v}">&#8205;</a><blockquote>ʙᴀɴᴋɪɴɢ sʏsᴛᴇᴍ

ʙᴀsɪᴄ:
<code>/bal</code> - ᴠɪᴇᴡ ʙᴀʟᴀɴᴄᴇ
<code>/cclaim</code> - ᴅᴀɪʟʏ 2000 ɢᴏʟᴅ
<code>/xp</code> - ᴄʜᴇᴄᴋ ʟᴇᴠᴇʟ

ʙᴀɴᴋ:
<code>/deposit amount</code> - ᴅᴇᴘᴏsɪᴛ
<code>/withdraw amount</code> - ᴡɪᴛʜᴅʀᴀᴡ
5% ᴅᴀɪʟʏ ɪɴᴛᴇʀᴇsᴛ

ʟᴏᴀɴs:
<code>/loan amount</code> - ʙᴏʀʀᴏᴡ
<code>/repay</code> - ᴘᴀʏ ʙᴀᴄᴋ
ᴍᴀx 100ᴋ | 10% ɪɴᴛᴇʀᴇsᴛ | 3 ᴅᴀʏs

ᴏᴛʜᴇʀ:
<code>/pay amount</code> - ᴛʀᴀɴsғᴇʀ
<code>/notifications</code> - ᴠɪᴇᴡ ɴᴏᴛɪᴄᴇs</blockquote>""",

    'rd': lambda v: f"""<a href="{v}">&#8205;</a><blockquote>ʀᴀɪᴅ sʏsᴛᴇᴍ

sᴛᴀʀᴛ ʀᴀɪᴅ:
<code>/raid</code> - sᴛᴀʀᴛ ɴᴇᴡ ʀᴀɪᴅ
ᴄᴏsᴛ: 500 ɢᴏʟᴅ
ᴊᴏɪɴ ᴘʜᴀsᴇ: 30s

ʀᴇᴡᴀʀᴅs:
ᴄʜᴀʀᴀᴄᴛᴇʀs - 25%
ɢᴏʟᴅ 500-2000 - 35%
ʟᴏsᴇ 200-500 - 20%
ɴᴏᴛʜɪɴɢ - 15%
ᴄʀɪᴛɪᴄᴀʟ ʜɪᴛ - 5%

ғᴇᴀᴛᴜʀᴇs:
ᴍᴜʟᴛɪᴘʟᴀʏᴇʀ ᴇᴠᴇɴᴛ
5 ᴍɪɴ ᴄᴏᴏʟᴅᴏᴡɴ
ʀᴀɴᴅᴏᴍ ʀᴇᴡᴀʀᴅs</blockquote>""",

    'st': lambda v: f"""<a href="{v}">&#8205;</a><blockquote>sᴛᴏʀᴇ sʏsᴛᴇᴍ

ᴘʀᴇᴍɪᴜᴍ sᴛᴏʀᴇ:
<code>/ps</code> - ᴏᴘᴇɴ sᴛᴏʀᴇ
<code>/pstats</code> - ᴠɪᴇᴡ sᴛᴀᴛs

ʜᴏᴡ ɪᴛ ᴡᴏʀᴋs:
3 ʀᴀɴᴅᴏᴍ ᴄʜᴀʀᴀᴄᴛᴇʀs ᴇᴠᴇʀʏ 24ʜ
ʀᴇғʀᴇsʜ ᴜᴘ ᴛᴏ 2x (ᴄᴏsᴛs ɢᴏʟᴅ)
ʙᴜʏ ᴡɪᴛʜ ɢᴏʟᴅ
ᴀᴜᴛᴏ ʀᴇsᴇᴛ ᴀғᴛᴇʀ ᴄᴏᴏʟᴅᴏᴡɴ

ʀᴇɢᴜʟᴀʀ sᴛᴏʀᴇ:
<code>/store</code> - ᴏᴘᴇɴ sʜᴏᴘ
ʙᴜʏ ɪᴛᴇᴍs ᴀɴᴅ ᴜᴘɢʀᴀᴅᴇs</blockquote>""",

    'ps': lambda v: f"""<a href="{v}">&#8205;</a><blockquote>sʟᴀᴠᴇ ᴘᴀss

ᴡᴇᴇᴋʟʏ ʀᴇᴡᴀʀᴅs:
<code>/claim</code> - ᴄʟᴀɪᴍ ᴡᴇᴇᴋʟʏ
<code>/sweekly</code> - ʙᴏɴᴜs ᴀғᴛᴇʀ 6 ᴄʟᴀɪᴍs
<code>/pbonus</code> - ᴄᴏᴍᴘʟᴇᴛᴇ ᴛᴀsᴋs

ʙᴇɴᴇғɪᴛs:
ᴇxᴄʟᴜsɪᴠᴇ sʟᴀᴠᴇs
ᴇxᴛʀᴀ ɢᴏʟᴅ ʀᴇᴡᴀʀᴅs
sᴘᴇᴄɪᴀʟ ᴇᴠᴇɴᴛs ᴀᴄᴄᴇss
ᴘʀɪᴏʀɪᴛʏ sᴜᴘᴘᴏʀᴛ

<code>/pass</code> - ᴠɪᴇᴡ ᴘᴀss sᴛᴀᴛᴜs</blockquote>""",

    'if': lambda v: f"""<a href="{v}">&#8205;</a><blockquote>ɪɴғᴏʀᴍᴀᴛɪᴏɴ

ᴘᴇʀsᴏɴᴀʟ sᴛᴀᴛs:
<code>/sinv</code> - ᴄʜᴇᴄᴋ ᴛᴏᴋᴇɴs
<code>/xp</code> - ᴄʜᴇᴄᴋ ʟᴇᴠᴇʟ
<code>/sinfo</code> - ғᴜʟʟ ᴘʀᴏғɪʟᴇ
<code>/rank</code> - ʏᴏᴜʀ ʀᴀɴᴋɪɴɢ

ʟᴇᴀᴅᴇʀʙᴏᴀʀᴅs:
<code>/tops</code> - ᴛᴏᴘ ᴘʟᴀʏᴇʀs
<code>/topchat</code> - ᴛᴏᴘ ᴄʜᴀᴛs
<code>/topgroups</code> - ᴛᴏᴘ ɢʀᴏᴜᴘs
<code>/xtop</code> - xᴘ ʀᴀɴᴋɪɴɢs
<code>/gstop</code> - ɢᴏʟᴅ ʀᴀɴᴋɪɴɢs</blockquote>""",

    'lb': lambda v: f"""<a href="{v}">&#8205;</a><blockquote>ʟᴇᴀᴅᴇʀʙᴏᴀʀᴅs

ʀᴀɴᴋɪɴɢs:
<code>/tops</code> - ʀɪᴄʜᴇsᴛ ʜᴜɴᴛᴇʀs
<code>/xtop</code> - ʜɪɢʜᴇsᴛ xᴘ
<code>/gstop</code> - ᴍᴏsᴛ ɢᴏʟᴅ
<code>/tophunters</code> - ᴇʟɪᴛᴇ ʟɪsᴛ

ɢʀᴏᴜᴘ sᴛᴀᴛs:
<code>/topchat</code> - ᴀᴄᴛɪᴠᴇ ᴄʜᴀᴛs
<code>/topgroups</code> - ᴛᴏᴘ ɢʀᴏᴜᴘs

ᴄʟɪᴍʙ ᴛᴏ ᴛʜᴇ ᴛᴏᴘ</blockquote>""",

    'rw': lambda v: f"""<a href="{v}">&#8205;</a><blockquote>ᴅᴀɪʟʏ ʀᴇᴡᴀʀᴅs

ᴅᴀɪʟʏ ᴄʟᴀɪᴍs:
<code>/claim</code> - 2000 ɢᴏʟᴅ ᴅᴀɪʟʏ
<code>/daily</code> - ʙᴏɴᴜs ɢᴏʟᴅ
<code>/hclaim</code> - ᴅᴀɪʟʏ sʟᴀᴠᴇ

ᴡᴇᴇᴋʟʏ ʙᴏɴᴜsᴇs:
<code>/weekly</code> - ʙɪɢ ᴡᴇᴇᴋʟʏ ʀᴇᴡᴀʀᴅ
<code>/sweekly</code> - ᴘᴀss ʙᴏɴᴜs

ʀᴇғᴇʀʀᴀʟ ʀᴇᴡᴀʀᴅs:
ɪɴᴠɪᴛᴇ ғʀɪᴇɴᴅs - 1000 ɢᴏʟᴅ
ᴛʜᴇʏ ɢᴇᴛ - 500 ɢᴏʟᴅ</blockquote>""",

    'gd': lambda v: f"""<a href="{v}">&#8205;</a><blockquote>ǫᴜɪᴄᴋ sᴛᴀʀᴛ ɢᴜɪᴅᴇ

ɢᴇᴛ sᴛᴀʀᴛᴇᴅ:
<code>/start</code> - ᴄʀᴇᴀᴛᴇ ᴀᴄᴄᴏᴜɴᴛ
<code>/claim</code> - ᴄʟᴀɪᴍ ᴅᴀɪʟʏ

ᴄᴀᴛᴄʜ sʟᴀᴠᴇs:
ᴡᴀɪᴛ ғᴏʀ sᴘᴀᴡɴ ɪɴ ᴄʜᴀᴛ
<code>/grab name</code> - ᴄᴀᴛᴄʜ

ᴇᴀʀɴ ɢᴏʟᴅ:
<code>/roll</code> - ᴘʟᴀʏ ɢᴀᴍᴇs
ɪɴᴠɪᴛᴇ ғʀɪᴇɴᴅs
ᴄᴏᴍᴘʟᴇᴛᴇ ᴛᴀsᴋs

ʟᴇᴠᴇʟ ᴜᴘ:
ᴘʟᴀʏ ɢᴀᴍᴇs ᴛᴏ ɢᴀɪɴ xᴘ
<code>/xp</code> - ᴄʜᴇᴄᴋ ʟᴇᴠᴇʟ</blockquote>"""
}

async def help_command(update: Update, context: CallbackContext):
    try:
        user = update.effective_user
        bal = await get_balance(user.id)
        video_url = get_random_video()
        caption = main_caption(user.first_name, bal, video_url)
        keyboard = main_keyboard(user.id)

        await update.message.reply_text(
            text=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
            disable_web_page_preview=False
        )
    except Exception as e:
        print(f"Help error: {e}")
        await update.message.reply_text("Failed to send help menu")

async def help_callback(update: Update, context: CallbackContext):
    query = update.callback_query

    try:
        await query.answer()
        data = query.data.split('_')
        action = data[1]
        uid = int(data[2])

        if query.from_user.id != uid:
            await query.answer("ᴛʜɪs ɪsɴ'ᴛ ғᴏʀ ʏᴏᴜ", show_alert=True)
            return

        video_url = get_random_video()

        # Close menu
        if action == 'cl':
            await query.message.delete()
            return

        # Back to main menu
        if action == 'mn':
            bal = await get_balance(uid)
            caption = main_caption(query.from_user.first_name, bal, video_url)
            keyboard = main_keyboard(uid)
        elif action == 'tp':
            caption = f"""<a href="{video_url}">&#8205;</a><blockquote>ᴘʀᴏ ᴛɪᴘs

ʀᴀɴᴅᴏᴍ ᴛɪᴘ:
{random.choice(TIPS)}

ᴍᴏʀᴇ ᴛɪᴘs:
ᴄʟᴀɪᴍ ᴅᴀɪʟʏ ʀᴇᴡᴀʀᴅs
ᴘʟᴀʏ ɢᴀᴍᴇs ғᴏʀ xᴘ
ᴛʀᴀᴅᴇ ʀᴀʀᴇ sʟᴀᴠᴇs
ᴊᴏɪɴ ᴇᴠᴇɴᴛs
ᴜsᴇ ᴘᴀss ғᴏʀ ʙᴏɴᴜsᴇs
ɪɴᴠɪᴛᴇ ғʀɪᴇɴᴅs

ᴛᴀᴘ ғᴏʀ ɴᴇᴡ ᴛɪᴘ</blockquote>"""
            keyboard = [
                [InlineKeyboardButton("ɴᴇᴡ ᴛɪᴘ", callback_data=f'hlp_tp_{uid}')],
                [InlineKeyboardButton("ʙᴀᴄᴋ", callback_data=f'hlp_mn_{uid}'),
                 InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data=f'hlp_cl_{uid}')]
            ]
        else:
            caption = CATEGORIES.get(action, lambda v: "")(video_url)
            keyboard = back_keyboard(uid)

        await query.edit_message_text(
            text=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML',
            disable_web_page_preview=False
        )
    except Exception as e:
        print(f"Callback error: {e}")
        await query.answer("ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ", show_alert=True)

application.add_handler(CommandHandler(['help', 'menu', 'panel'], help_command, block=False))
application.add_handler(CallbackQueryHandler(help_callback, pattern=r'^hlp_[a-z]{2}_\d+$', block=False))