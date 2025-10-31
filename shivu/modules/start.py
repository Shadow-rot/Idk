import random
from html import escape
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler

from shivu import application, SUPPORT_CHAT, BOT_USERNAME, db, GROUP_ID, LOGGER
from shivu import user_collection, user_totals_collection

# Rewards
REFERRER_REWARD = 1000
NEW_USER_BONUS = 500

VIDEO_URL = "https://files.catbox.moe/9i2vfh.mp4"


def fmt(text):
    """lowercase futuristic format"""
    return text.lower()


async def process_referral(user_id: int, first_name: str, referring_user_id: int, context: CallbackContext):
    """process referral rewards"""
    try:
        referring_user = await user_collection.find_one({"id": referring_user_id})
        if not referring_user:
            return False

        new_user = await user_collection.find_one({"id": user_id})
        if new_user and new_user.get('referred_by'):
            return False

        if user_id == referring_user_id:
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
                    "pass_data.tasks.invites": 1,
                    "pass_data.total_invite_earnings": REFERRER_REWARD
                },
                "$push": {"invited_user_ids": user_id}
            }
        )

        msg = (
            f"referral.sync → complete\n\n"
            f"agent        :: <b>{escape(first_name)}</b>\n"
            f"status       :: linked via your node\n\n"
            f"rewards      :: +{REFERRER_REWARD:,} g\n"
            f"task.update  :: invite +1\n\n"
            f"signal → keep expanding network"
        )

        try:
            await context.bot.send_message(chat_id=referring_user_id, text=msg, parse_mode='HTML')
        except:
            pass

        return True
    except Exception as e:
        LOGGER.error(f"[REFERRAL ERROR] {e}")
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
    total_users = await user_collection.count_documents({})
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
                "last_weekly_claim": None,
                "streak_count": 0,
                "last_streak_claim": None,
                "tasks": {"invites": 0, "weekly_claims": 0, "grabs": 0},
                "mythic_unlocked": False,
                "premium_expires": None,
                "elite_expires": None,
                "pending_elite_payment": None,
                "invited_users": [],
                "total_invite_earnings": 0
            }
        }

        await user_collection.insert_one(new_user)
        user_data = new_user

        if referring_user_id:
            referral_success = await process_referral(user_id, first_name, referring_user_id, context)
            if referral_success:
                user_data['balance'] = NEW_USER_BONUS
                user_data['referred_by'] = referring_user_id

        try:
            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=(
                    f"network.node → new\n\n"
                    f"agent        :: <a href='tg://user?id={user_id}'>{escape(first_name)}</a>\n"
                    f"id           :: {user_id}\n"
                    f"total.users  :: {total_users + 1}\n\n"
                    f"status → online"
                ),
                parse_mode='HTML'
            )
        except:
            pass
    else:
        update_fields = {}
        if user_data.get('first_name') != first_name:
            update_fields['first_name'] = first_name
        if user_data.get('username') != username:
            update_fields['username'] = username

        if 'pass_data' not in user_data:
            update_fields['pass_data'] = {
                "tier": "free",
                "weekly_claims": 0,
                "last_weekly_claim": None,
                "streak_count": 0,
                "last_streak_claim": None,
                "tasks": {"invites": 0, "weekly_claims": 0, "grabs": 0},
                "mythic_unlocked": False,
                "premium_expires": None,
                "elite_expires": None,
                "pending_elite_payment": None,
                "invited_users": [],
                "total_invite_earnings": 0
            }

        if update_fields:
            await user_collection.update_one({"id": user_id}, {"$set": update_fields})
            user_data = await user_collection.find_one({"id": user_id})

    user_balance = user_data.get('balance', 0)
    user_totals = await user_totals_collection.find_one({'id': user_id})
    total_characters = user_totals.get('count', 0) if user_totals else 0
    referred_count = user_data.get('referred_users', 0)

    if update.effective_chat.type == "private":
        welcome_msg = "signal reconnected" if not is_new_user else "system online"
        bonus_msg = f"\n\nbonus        :: +{NEW_USER_BONUS} g via referral" if is_new_user and referring_user_id else ""

        caption = f"""<b>{welcome_msg}</b>

system       :: pick.catcher neural net
version      :: 4.0.nexus

function     :: spawns anime characters in groups
mode         :: collection · trading · combat
deployment   :: add to group via button below

access       :: /help for command list{bonus_msg}

━━━━━━━━━━━━━━━━━━━

<b>user.node</b>

balance      :: {user_balance:,} g
characters   :: {total_characters}
referrals    :: {referred_count}

status → synced
"""

        keyboard = [
            [InlineKeyboardButton("deploy to group", url=f'https://t.me/{BOT_USERNAME}?startgroup=new')],
            [
                InlineKeyboardButton("support.link", url=f'https://t.me/{SUPPORT_CHAT}'),
                InlineKeyboardButton("updates.feed", url=f'https://t.me/PICK_X_UPDATE')
            ],
            [InlineKeyboardButton("help.module", callback_data='hlp_main')],
            [InlineKeyboardButton("referral.net", callback_data='ref_main')],
            [InlineKeyboardButton("credits.node", callback_data='crd_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_video(
            chat_id=update.effective_chat.id,
            video=VIDEO_URL,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        caption = f"<b>system online</b>\n\ninitiate pm connection for full access"
        keyboard = [
            [InlineKeyboardButton("deploy to group", url=f'https://t.me/{BOT_USERNAME}?startgroup=new')],
            [
                InlineKeyboardButton("support.link", url=f'https://t.me/{SUPPORT_CHAT}'),
                InlineKeyboardButton("updates.feed", url=f'https://t.me/PICK_X_UPDATE')
            ],
            [InlineKeyboardButton("help.module", callback_data='hlp_grp')],
            [InlineKeyboardButton("credits.node", callback_data='crd_grp')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_video(
            chat_id=update.effective_chat.id,
            video=VIDEO_URL,
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
        await query.answer("initialize with /start first", show_alert=True)
        return

    user_totals = await user_totals_collection.find_one({'id': user_id})

    if query.data == 'hlp_main':
        help_text = f"""<b>help.module → active</b>

<b>gameplay.core</b>
/grab        :: guess character in group
/fav         :: set favorite character
/harem       :: view collection

<b>trade.system</b>
/trade       :: exchange characters
/gift        :: transfer character to user

<b>leaderboard.net</b>
/gstop       :: top groups by activity
/tophunters  :: top collectors
/ctop        :: chat rankings

<b>config.panel</b>
/changetime  :: adjust spawn interval

<b>economy.core</b>
/bal         :: check balance
/pay         :: transfer gold
/claim       :: daily rewards
/roll        :: gamble system

<b>pass.system</b>
/pass        :: view pass status
/pclaim      :: claim weekly rewards
/tasks       :: task progress

signal → stable
"""
        keyboard = [[InlineKeyboardButton("back", callback_data='bck_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_caption(caption=help_text, reply_markup=reply_markup, parse_mode='HTML')

    elif query.data == 'ref_main':
        referral_link = f"https://t.me/{BOT_USERNAME}?start=r_{user_id}"
        referred_count = user_data.get('referred_users', 0)
        total_earnings = referred_count * REFERRER_REWARD

        referral_text = f"""<b>referral.net → active</b>

<b>network.status</b>

referrals    :: {referred_count}
earned       :: {total_earnings:,} g

━━━━━━━━━━━━━━━━━━━

<b>protocol</b>

step.01      :: copy link below
step.02      :: share with agents
step.03      :: they initialize bot
step.04      :: instant rewards

━━━━━━━━━━━━━━━━━━━

<b>rewards.breakdown</b>

you.receive  :: {REFERRER_REWARD:,} g
agent.bonus  :: {NEW_USER_BONUS:,} g
task.credit  :: included

━━━━━━━━━━━━━━━━━━━

<b>invite.link</b>

<code>{referral_link}</code>

signal → tap to copy
"""
        keyboard = [
            [InlineKeyboardButton("share.link", url=f"https://t.me/share/url?url={referral_link}")],
            [InlineKeyboardButton("back", callback_data='bck_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_caption(caption=referral_text, reply_markup=reply_markup, parse_mode='HTML')

    elif query.data == 'crd_main':
        credits_text = f"""<b>credits.node → active</b>

system.info  :: pick.catcher neural network
created.by   :: dedicated development team

acknowledgment to all contributors and active users

access.panels below for team roster

signal → online
"""
        keyboard = [
            [InlineKeyboardButton("owner.profile", callback_data='own_view')],
            [InlineKeyboardButton("sudo.roster", callback_data='sud_list')],
            [InlineKeyboardButton("back", callback_data='bck_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_caption(caption=credits_text, reply_markup=reply_markup, parse_mode='HTML')

    elif query.data == 'sud_list':
        sudo_text = f"""<b>sudo.roster → active</b>

system.administrators with elevated access

tap.profiles for direct contact

signal → verified
"""
        keyboard = [
            [InlineKeyboardButton("yoichi isagi", url='https://t.me/ll_Yoichi_Isagi_ll')],
            [InlineKeyboardButton("kaizen", url='https://t.me/digital_paradoxx')],
            [InlineKeyboardButton("killua", url='https://t.me/notkilluafr')],
            [InlineKeyboardButton("shikmor", url='https://t.me/avinashs_sun')],
            [InlineKeyboardButton("back.to.credits", callback_data='crd_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_caption(caption=sudo_text, reply_markup=reply_markup, parse_mode='HTML')

    elif query.data == 'own_view':
        owner_text = f"""<b>owner.profile → active</b>

system.architect identified

tap.button for direct contact

signal → verified
"""
        keyboard = [
            [InlineKeyboardButton("thorfinn", url='https://t.me/ll_Thorfinn_ll')],
            [InlineKeyboardButton("back.to.credits", callback_data='crd_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_caption(caption=owner_text, reply_markup=reply_markup, parse_mode='HTML')

    elif query.data == 'bck_main':
        user_balance = user_data.get('balance', 0)
        total_characters = user_totals.get('count', 0) if user_totals else 0
        referred_count = user_data.get('referred_users', 0)

        caption = f"""<b>signal reconnected</b>

system       :: pick.catcher neural net
version      :: 4.0.nexus

function     :: spawns anime characters in groups
mode         :: collection · trading · combat
deployment   :: add to group via button below

access       :: /help for command list

━━━━━━━━━━━━━━━━━━━

<b>user.node</b>

balance      :: {user_balance:,} g
characters   :: {total_characters}
referrals    :: {referred_count}

status → synced
"""
        keyboard = [
            [InlineKeyboardButton("deploy to group", url=f'https://t.me/{BOT_USERNAME}?startgroup=new')],
            [
                InlineKeyboardButton("support.link", url=f'https://t.me/{SUPPORT_CHAT}'),
                InlineKeyboardButton("updates.feed", url=f'https://t.me/PICK_X_UPDATE')
            ],
            [InlineKeyboardButton("help.module", callback_data='hlp_main')],
            [InlineKeyboardButton("referral.net", callback_data='ref_main')],
            [InlineKeyboardButton("credits.node", callback_data='crd_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_caption(caption=caption, reply_markup=reply_markup, parse_mode='HTML')


application.add_handler(CommandHandler('start', start, block=False))
application.add_handler(CallbackQueryHandler(button_callback, block=False))

LOGGER.info("[START] futuristic UI system loaded")