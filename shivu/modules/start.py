import random
from html import escape 

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler

from shivu import application, PHOTO_URL, SUPPORT_CHAT, UPDATE_CHAT, BOT_USERNAME, db, GROUP_ID
from shivu import user_collection, user_totals_collection


def to_small_caps(text):
    """Convert text to small caps"""
    small_caps_map = {
        'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ',
        'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ',
        's': 's', 't': 'ᴛ', 'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
        'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ғ', 'G': 'ɢ', 'H': 'ʜ', 'I': 'ɪ',
        'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ', 'O': 'ᴏ', 'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ',
        'S': 's', 'T': 'ᴛ', 'U': 'ᴜ', 'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x', 'Y': 'ʏ', 'Z': 'ᴢ'
    }
    return ''.join(small_caps_map.get(c, c) for c in text)


async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username
    args = context.args
    referring_user_id = None

    if args and args[0].startswith('r_'):
        referring_user_id = int(args[0][2:])

    user_data = await user_collection.find_one({"id": user_id})
    total_users = await user_collection.count_documents({})

    if user_data is None:
        new_user = {
            "id": user_id, 
            "first_name": first_name, 
            "username": username, 
            "tokens": 500, 
            "characters": [],
            "referred_users": 0
        }
        await user_collection.insert_one(new_user)

        if referring_user_id:
            referring_user_data = await user_collection.find_one({"id": referring_user_id})
            if referring_user_data:
                await user_collection.update_one(
                    {"id": referring_user_id}, 
                    {"$inc": {"tokens": 1000, "referred_users": 1}}
                )
                referrer_message = f"<b>{to_small_caps('referral success')}</b>\n\n{escape(first_name)} {to_small_caps('joined using your link')}\n{to_small_caps('earned')} <b>1000 {to_small_caps('tokens')}</b>"
                try:
                    await context.bot.send_message(
                        chat_id=referring_user_id, 
                        text=referrer_message,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    print(f"Failed to send referral message: {e}")

        await context.bot.send_message(
            chat_id=GROUP_ID, 
            text=f"<b>{to_small_caps('new player')}</b>\n\n{to_small_caps('user')}: <a href='tg://user?id={user_id}'>{escape(first_name)}</a>\n{to_small_caps('id')}: <code>{user_id}</code>\n{to_small_caps('total')}: <b>{total_users}</b>", 
            parse_mode='HTML'
        )
        user_data = new_user
    else:
        if user_data['first_name'] != first_name or user_data['username'] != username:
            await user_collection.update_one(
                {"id": user_id}, 
                {"$set": {"first_name": first_name, "username": username}}
            )

    user_balance = user_data.get('balance', 0)
    user_totals = await user_totals_collection.find_one({'id': user_id})
    total_characters = user_totals['count'] if user_totals else 0
    referred_count = user_data.get('referred_users', 0)

    if update.effective_chat.type == "private":
        referral_link = f"https://t.me/{BOT_USERNAME}?start=r_{user_id}"

        caption = f"""
<b>{to_small_caps('hallo')}</b>

{to_small_caps('hey pick catcher')}

{to_small_caps('i am pick catcher')}
{to_small_caps('i spawn anime characters in your groups and let users collect them')}
{to_small_caps('so what are you waiting for add me in your group by click on the below button')}

{to_small_caps('tap the help button for details')}

{to_small_caps('hit help to find out more about how to use me')}

<b>{to_small_caps('your stats')}</b>
{to_small_caps('wallet')}: <b>{user_balance}</b> {to_small_caps('gold')}
{to_small_caps('characters')}: <b>{total_characters}</b>
{to_small_caps('referrals')}: <b>{referred_count}</b>
"""

        keyboard = [
            [InlineKeyboardButton(to_small_caps("start guessing"), url=f'https://t.me/{BOT_USERNAME}?startgroup=new')],
            [
                InlineKeyboardButton(to_small_caps("support"), url=f'https://t.me/{SUPPORT_CHAT}'),
                InlineKeyboardButton(to_small_caps("channel"), url=f'https://t.me/PICK_X_UPDATE')
            ],
            [InlineKeyboardButton(to_small_caps("help"), callback_data='help')],
            [InlineKeyboardButton(to_small_caps("referral"), callback_data='referral')],
            [InlineKeyboardButton(to_small_caps("credits"), callback_data='credits')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        photo_url = random.choice(PHOTO_URL)

        await context.bot.send_photo(
            chat_id=update.effective_chat.id, 
            photo=photo_url, 
            caption=caption, 
            reply_markup=reply_markup, 
            parse_mode='HTML'
        )

    else:
        photo_url = random.choice(PHOTO_URL)
        caption = f"<b>{to_small_caps('alive')}</b>\n\n{to_small_caps('connect to me in pm for more information')}"
        
        keyboard = [
            [InlineKeyboardButton(to_small_caps("start guessing"), url=f'https://t.me/{BOT_USERNAME}?startgroup=new')],
            [
                InlineKeyboardButton(to_small_caps("support"), url=f'https://t.me/{SUPPORT_CHAT}'),
                InlineKeyboardButton(to_small_caps("channel"), url=f'https://t.me/PICK_X_UPDATE')
            ],
            [InlineKeyboardButton(to_small_caps("help"), callback_data='help')],
            [InlineKeyboardButton(to_small_caps("credits"), callback_data='credits')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_photo(
            chat_id=update.effective_chat.id, 
            photo=photo_url, 
            caption=caption,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )


async def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_data = await user_collection.find_one({"id": user_id})
    
    if not user_data:
        await query.answer(to_small_caps("please start the bot first"), show_alert=True)
        return

    user_totals = await user_totals_collection.find_one({'id': user_id})

    if query.data == 'help':
        help_text = f"""
<b>{to_small_caps('help section')}</b>

<b>{to_small_caps('gameplay commands')}</b>
/guess - {to_small_caps('to guess character only works in group')}
/fav - {to_small_caps('add your fav')}
/collection - {to_small_caps('to see your collection')}

<b>{to_small_caps('trading commands')}</b>
/trade - {to_small_caps('to trade characters')}
/gift - {to_small_caps('give any character from your collection to another user only works in groups')}

<b>{to_small_caps('leaderboard commands')}</b>
/topgroups - {to_small_caps('see top groups ppl guesses most in that groups')}
/top - {to_small_caps('to see top users')}
/ctop - {to_small_caps('your chat top')}

<b>{to_small_caps('settings commands')}</b>
/changetime - {to_small_caps('change character appear time only works in groups')}

<b>{to_small_caps('economy commands')}</b>
/bal - {to_small_caps('check wallet')}
/pay - {to_small_caps('send gold')}
/claim - {to_small_caps('daily reward')}
/roll - {to_small_caps('gamble gold')}
"""
        help_keyboard = [[InlineKeyboardButton(to_small_caps("back"), callback_data='back')]]
        reply_markup = InlineKeyboardMarkup(help_keyboard)

        await query.edit_message_caption(
            caption=help_text, 
            reply_markup=reply_markup, 
            parse_mode='HTML'
        )

    elif query.data == 'referral':
        referral_link = f"https://t.me/{BOT_USERNAME}?start=r_{user_id}"
        referred_count = user_data.get('referred_users', 0)

        referral_text = f"""
<b>{to_small_caps('invite program')}</b>

{to_small_caps('your referrals')}: <b>{referred_count}</b>
{to_small_caps('earned')}: <b>{referred_count * 1000}</b> {to_small_caps('gold')}

<b>{to_small_caps('how to invite')}</b>
{to_small_caps('copy link below')}
{to_small_caps('share with friends')}
{to_small_caps('they click and start bot')}
{to_small_caps('instant rewards')}

<b>{to_small_caps('reward breakdown')}</b>
{to_small_caps('you get')} <b>1000</b> {to_small_caps('gold')}
{to_small_caps('friend gets')} <b>500</b> {to_small_caps('gold')}

<b>{to_small_caps('your invite link')}</b>
<code>{referral_link}</code>

{to_small_caps('tap to copy link')}
"""
        referral_keyboard = [[InlineKeyboardButton(to_small_caps("back"), callback_data='back')]]
        reply_markup = InlineKeyboardMarkup(referral_keyboard)

        await query.edit_message_caption(
            caption=referral_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    elif query.data == 'credits':
        credits_text = f"""
<b>{to_small_caps('credits')}</b>

{to_small_caps('this bot was created and maintained by our dedicated team')}

{to_small_caps('special thanks to all contributors and users who made this project possible')}

{to_small_caps('tap below to see owner and sudo users')}
"""
        credits_keyboard = [
            [InlineKeyboardButton(to_small_caps("owner"), callback_data='owner')],
            [InlineKeyboardButton(to_small_caps("sudo users"), callback_data='sudo')],
            [InlineKeyboardButton(to_small_caps("back"), callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(credits_keyboard)

        await query.edit_message_caption(
            caption=credits_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    elif query.data == 'sudo':
        sudo_text = f"""
<b>{to_small_caps('sudo users')}</b>

{to_small_caps('these are the sudo users who help manage this bot')}

{to_small_caps('tap on their names to contact them')}
"""
        sudo_keyboard = [
            [InlineKeyboardButton("lodu", url='https://t.me/ll_Yoichi_Isagi_ll')],
            [InlineKeyboardButton("꧁ღ⊱✨Kaizen ✨⊱ღ꧂", url='https://t.me/digital_paradoxx')],
            [InlineKeyboardButton("ｋｉｌｌｕａ", url='https://t.me/notkilluafr')],
            [InlineKeyboardButton(to_small_caps("back to credits"), callback_data='credits')]
        ]
        reply_markup = InlineKeyboardMarkup(sudo_keyboard)

        await query.edit_message_caption(
            caption=sudo_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    elif query.data == 'owner':
        owner_text = f"""
<b>{to_small_caps('owner')}</b>

{to_small_caps('the owner of this bot is')}

{to_small_caps('tap on the button below to contact the owner')}
"""
        owner_keyboard = [
            [InlineKeyboardButton("lodu", url='https://t.me/ll_Thorfinn_ll')],
            [InlineKeyboardButton(to_small_caps("back to credits"), callback_data='credits')]
        ]
        reply_markup = InlineKeyboardMarkup(owner_keyboard)

        await query.edit_message_caption(
            caption=owner_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    elif query.data == 'back':
        user_balance = user_data.get('balance', 0)
        total_characters = user_totals['count'] if user_totals else 0
        referred_count = user_data.get('referred_users', 0)
        
        caption = f"""
<b>{to_small_caps('hallo')}</b>

{to_small_caps('hey pick catcher')}

{to_small_caps('i am pick catcher')}
{to_small_caps('i spawn anime characters in your groups and let users collect them')}
{to_small_caps('so what are you waiting for add me in your group by click on the below button')}

{to_small_caps('tap the help button for details')}

{to_small_caps('hit help to find out more about how to use me')}

<b>{to_small_caps('your stats')}</b>
{to_small_caps('wallet')}: <b>{user_balance}</b> {to_small_caps('gold')}
{to_small_caps('characters')}: <b>{total_characters}</b>
{to_small_caps('referrals')}: <b>{referred_count}</b>
"""

        keyboard = [
            [InlineKeyboardButton(to_small_caps("start guessing"), url=f'https://t.me/{BOT_USERNAME}?startgroup=new')],
            [
                InlineKeyboardButton(to_small_caps("support"), url=f'https://t.me/{SUPPORT_CHAT}'),
                InlineKeyboardButton(to_small_caps("channel"), url=f'https://t.me/PICK_X_UPDATE')
            ],
            [InlineKeyboardButton(to_small_caps("help"), callback_data='help')],
            [InlineKeyboardButton(to_small_caps("referral"), callback_data='referral')],
            [InlineKeyboardButton(to_small_caps("credits"), callback_data='credits')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_caption(
            caption=caption,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )


start_handler = CommandHandler('start', start, block=False)
application.add_handler(start_handler)

callback_handler = CallbackQueryHandler(button_callback, block=False)
application.add_handler(callback_handler)