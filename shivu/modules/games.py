# modules/games.py
import math
import asyncio
from datetime import datetime, timedelta
from telegram.ext import CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import CallbackContext
from shivu import application, user_collection
import random
import time

# ------------------------
# Config
# ------------------------
GAME_COOLDOWN_SECONDS = 5   # small anti-spam per-user cooldown for games
RIDDLE_TIMEOUT = 15         # seconds allowed to answer a riddle
DEFAULT_XP_WIN = 5         # XP awarded per win (optional)
DEFAULT_TOKEN_REWARD = 1   # tokens for some games

# in-memory structures
_user_cooldowns = {}          # user_id -> datetime of last play
_pending_riddles = {}        # user_id -> {"answer": int/str, "expires_at": ts, "message_id": msg_id, "chat_id": chat_id}

# helpers -----------------------------------------------------------------
def user_on_cooldown(user_id: int) -> (bool, float):
    """Return (is_on_cooldown, seconds_left)"""
    last = _user_cooldowns.get(user_id)
    if not last:
        return False, 0.0
    elapsed = (datetime.utcnow() - last).total_seconds()
    if elapsed >= GAME_COOLDOWN_SECONDS:
        return False, 0.0
    return True, GAME_COOLDOWN_SECONDS - elapsed

async def get_user_doc(user_id: int):
    doc = await user_collection.find_one({'id': user_id})
    return doc

async def ensure_user_doc(user_id: int, first_name=None, username=None):
    doc = await get_user_doc(user_id)
    if doc:
        update = {}
        if username and username != doc.get('username'):
            update['username'] = username
        if first_name and first_name != doc.get('first_name'):
            update['first_name'] = first_name
        if update:
            await user_collection.update_one({'id': user_id}, {'$set': update})
        return doc
    # create default
    new = {'id': user_id, 'first_name': first_name, 'username': username, 'balance': 0, 'tokens': 0, 'characters': []}
    await user_collection.insert_one(new)
    return new

async def change_balance(user_id: int, delta: int):
    """Atomic inc balance and return updated doc."""
    await user_collection.update_one({'id': user_id}, {'$inc': {'balance': delta}}, upsert=True)
    return await get_user_doc(user_id)

async def change_tokens(user_id: int, delta: int):
    await user_collection.update_one({'id': user_id}, {'$inc': {'tokens': delta}}, upsert=True)
    return await get_user_doc(user_id)

# UI helpers
def play_again_button(command_name: str, args_text: str = ""):
    # callback_data: games:repeat:<command_name>:<args_text>  (args_text simple, no spaces ideally)
    cb = f"games:repeat:{command_name}:{args_text or '_'}"
    return InlineKeyboardMarkup([[InlineKeyboardButton("🎮 Play Again", callback_data=cb)]])

# ------------------------
# Games implementations
# ------------------------

async def sbet(update: Update, context: CallbackContext):
    """Coin toss bet: /sbet <amount> heads|tails"""
    user_id = update.effective_user.id
    if user_on_cooldown(user_id)[0]:
        await update.message.reply_text("⌛ Please wait a few seconds before playing again.")
        return

    try:
        amount = int(context.args[0])
        guess = context.args[1].lower()
    except Exception:
        await update.message.reply_text("Usage: /sbet <amount> heads|tails")
        return

    if amount <= 0:
        await update.message.reply_text("Amount must be positive.")
        return

    if guess not in ("heads", "tails", "head", "tail", "h", "t"):
        await update.message.reply_text("Guess must be 'heads' or 'tails'.")
        return

    # normalize
    if guess.startswith('h'):
        guess = 'heads'
    else:
        guess = 'tails'

    await ensure_user_doc(user_id, update.effective_user.first_name, update.effective_user.username)
    user = await get_user_doc(user_id)
    balance = user.get('balance', 0)

    if balance < amount:
        await update.message.reply_text("You don't have enough coins.")
        return

    # take the bet now
    await change_balance(user_id, -amount)

    outcome = random.choice(['heads', 'tails'])
    won = (outcome == guess)
    if won:
        win_amount = amount * 2
        await change_balance(user_id, win_amount)
        # optional XP / token reward
        await change_tokens(user_id, 0)  # no tokens by default
        text = f"🪙 Coin toss: {outcome} — You won! You gained {win_amount} coins."
    else:
        text = f"🪙 Coin toss: {outcome} — You lost {amount} coins."

    _user_cooldowns[user_id] = datetime.utcnow()
    await update.message.reply_text(text, reply_markup=play_again_button("sbet", f"{amount}:{guess}"))

async def roll_cmd(update: Update, context: CallbackContext):
    """Dice roll: /roll <amount> odd|even"""
    user_id = update.effective_user.id
    if user_on_cooldown(user_id)[0]:
        await update.message.reply_text("⌛ Please wait a few seconds before playing again.")
        return

    try:
        amount = int(context.args[0])
        choice = context.args[1].lower()
    except Exception:
        await update.message.reply_text("Usage: /roll <amount> odd|even")
        return

    if amount <= 0:
        await update.message.reply_text("Amount must be positive.")
        return
    if choice not in ("odd", "even", "o", "e"):
        await update.message.reply_text("Choice must be 'odd' or 'even'.")
        return
    choice = 'odd' if choice.startswith('o') else 'even'

    await ensure_user_doc(user_id, update.effective_user.first_name, update.effective_user.username)
    user = await get_user_doc(user_id)
    if user.get('balance', 0) < amount:
        await update.message.reply_text("Not enough coins.")
        return

    await change_balance(user_id, -amount)
    dice = random.randint(1, 6)
    result = 'odd' if dice % 2 else 'even'
    if result == choice:
        win_amount = amount * 2
        await change_balance(user_id, win_amount)
        text = f"🎲 Dice rolled {dice} ({result}) — You won {win_amount} coins!"
    else:
        text = f"🎲 Dice rolled {dice} ({result}) — You lost {amount} coins."

    _user_cooldowns[user_id] = datetime.utcnow()
    await update.message.reply_text(text, reply_markup=play_again_button("roll", f"{amount}:{choice}"))

async def gamble(update: Update, context: CallbackContext):
    """Gamble: /gamble <amount> l|r"""
    user_id = update.effective_user.id
    if user_on_cooldown(user_id)[0]:
        await update.message.reply_text("⌛ Wait a bit before playing again.")
        return

    try:
        amount = int(context.args[0])
        pick = context.args[1].lower()
    except Exception:
        await update.message.reply_text("Usage: /gamble <amount> l|r")
        return

    if pick not in ('l', 'r', 'left', 'right'):
        await update.message.reply_text("Choice: l or r")
        return
    pick = 'l' if pick.startswith('l') else 'r'

    await ensure_user_doc(user_id, update.effective_user.first_name, update.effective_user.username)
    user = await get_user_doc(user_id)
    if user.get('balance', 0) < amount:
        await update.message.reply_text("Not enough coins.")
        return

    await change_balance(user_id, -amount)
    outcome = random.choice(['l', 'r'])
    if outcome == pick:
        win_amount = amount * 2
        await change_balance(user_id, win_amount)
        text = f"🎰 Result: {outcome} — You won {win_amount} coins!"
    else:
        text = f"🎰 Result: {outcome} — You lost {amount} coins."

    _user_cooldowns[user_id] = datetime.utcnow()
    await update.message.reply_text(text, reply_markup=play_again_button("gamble", f"{amount}:{pick}"))

async def basket(update: Update, context: CallbackContext):
    """Basket: /basket <amount>"""
    user_id = update.effective_user.id
    if user_on_cooldown(user_id)[0]:
        await update.message.reply_text("⌛ Wait a few seconds.")
        return

    try:
        amount = int(context.args[0])
    except Exception:
        await update.message.reply_text("Usage: /basket <amount>")
        return

    await ensure_user_doc(user_id, update.effective_user.first_name, update.effective_user.username)
    user = await get_user_doc(user_id)
    if user.get('balance', 0) < amount:
        await update.message.reply_text("Not enough coins.")
        return

    await change_balance(user_id, -amount)
    # simple success chance, could be more advanced
    chance = random.random()
    # chance influenced by amount (small advantage for larger bet)
    win_chance = min(0.6, 0.35 + math.log1p(amount) / 50)
    if chance < win_chance:
        win_amount = amount * 2
        await change_balance(user_id, win_amount)
        text = f"🏀 Swish! You scored. You won {win_amount} coins!"
    else:
        text = f"🏀 Missed! You lost {amount} coins."

    _user_cooldowns[user_id] = datetime.utcnow()
    await update.message.reply_text(text, reply_markup=play_again_button("basket", str(amount)))

async def dart(update: Update, context: CallbackContext):
    """Dart: /dart <amount>"""
    user_id = update.effective_user.id
    if user_on_cooldown(user_id)[0]:
        await update.message.reply_text("⌛ Wait a few seconds.")
        return

    try:
        amount = int(context.args[0])
    except Exception:
        await update.message.reply_text("Usage: /dart <amount>")
        return

    await ensure_user_doc(user_id, update.effective_user.first_name, update.effective_user.username)
    user = await get_user_doc(user_id)
    if user.get('balance', 0) < amount:
        await update.message.reply_text("Not enough coins.")
        return

    await change_balance(user_id, -amount)
    # dart scoring: bullseye is rare
    roll = random.randint(1, 100)
    if roll <= 10:  # bullseye
        win_amount = amount * 4
        await change_balance(user_id, win_amount)
        text = f"🎯 Bullseye! You won {win_amount} coins!"
    elif roll <= 40:
        win_amount = amount * 2
        await change_balance(user_id, win_amount)
        text = f"🎯 Good hit! You won {win_amount} coins!"
    else:
        text = f"🎯 Missed! You lost {amount} coins."

    _user_cooldowns[user_id] = datetime.utcnow()
    await update.message.reply_text(text, reply_markup=play_again_button("dart", str(amount)))

# ---- stour: contract mini-game -----------------------------------------
async def stour(update: Update, context: CallbackContext):
    """/stour - 50/50 contract gamble that costs 50 coins"""
    user_id = update.effective_user.id

    # Cooldown check
    if user_on_cooldown(user_id)[0]:
        await update.message.reply_text("⌛ Wait a few seconds before trying again.")
        return

    await ensure_user_doc(user_id, update.effective_user.first_name, update.effective_user.username)
    user = await get_user_doc(user_id)

    entry_fee = 50  # cost to play

    # Check balance
    if user.get('balance', 0) < entry_fee:
        await update.message.reply_text("💰 You need at least 50 coins to start a contract.")
        return

    # Deduct entry fee
    await change_balance(user_id, -entry_fee)

    # 50/50 chance
    outcome = random.random()
    if outcome < 0.5:
        # Success — reward
        reward_type = random.choice(["coins", "tokens"])

        if reward_type == "coins":
            reward = random.randint(100, 600)
            await change_balance(user_id, reward)
            text = f"🤝 Contract successful! You earned <b>{reward}</b> coins!"
        else:
            tokens = random.randint(1, 3)
            await change_tokens(user_id, tokens)
            text = f"🎯 Contract granted you <b>{tokens}</b> token(s)!"

    else:
        # Fail — lose entry fee
        text = (
            f"💥 Contract failed! You lost <b>{entry_fee}</b> coins.\n"
            f"Try your luck again!"
        )

    # Set cooldown
    _user_cooldowns[user_id] = datetime.utcnow()

    # Send result
    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=play_again_button("stour", "")
    )

# ---- riddle system -----------------------------------------------------
async def riddle(update: Update, context: CallbackContext):
    """/riddle - sends a math riddle; user has to reply the answer within RIDDLE_TIMEOUT seconds."""
    user_id = update.effective_user.id
    if user_on_cooldown(user_id)[0]:
        await update.message.reply_text("⌛ Wait a few seconds before playing again.")
        return

    # generate a small arithmetic problem
    a = random.randint(2, 50)
    b = random.randint(1, 50)
    op = random.choice(['+', '-', '*'])
    if op == '+':
        ans = a + b
    elif op == '-':
        ans = a - b
    else:
        ans = a * b

    question = f"Solve: `{a} {op} {b}` — You have {RIDDLE_TIMEOUT} seconds. Reply with the number."
    msg = await update.message.reply_text(question, parse_mode="Markdown")

    # store pending riddle
    _pending_riddles[user_id] = {"answer": str(ans), "expires_at": time.time() + RIDDLE_TIMEOUT, "message_id": msg.message_id, "chat_id": update.effective_chat.id}
    _user_cooldowns[user_id] = datetime.utcnow()

    # schedule expiry cleaner
    async def expire_riddle(uid):
        await asyncio.sleep(RIDDLE_TIMEOUT)
        pending = _pending_riddles.get(uid)
        if pending and pending.get("expires_at", 0) <= time.time():
            _pending_riddles.pop(uid, None)
            try:
                await application.bot.send_message(pending["chat_id"], f"⏳ Time's up! The correct answer was `{ans}`.", parse_mode="Markdown")
            except Exception:
                pass

    asyncio.create_task(expire_riddle(user_id))

# Handler listening to replies for riddle answers
async def riddle_answer_listener(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in _pending_riddles:
        return  # not answering a riddle

    pending = _pending_riddles[user_id]
    # only accept reply in same chat
    if update.effective_chat.id != pending.get("chat_id"):
        return

    text = (update.message.text or "").strip()
    if not text:
        return

    # check expiration
    if time.time() > pending.get("expires_at", 0):
        _pending_riddles.pop(user_id, None)
        await update.message.reply_text("⏳ Riddle expired.")
        return

    if text == pending.get("answer"):
        # reward token(s)
        await change_tokens(user_id, DEFAULT_TOKEN_REWARD)
        await update.message.reply_text(f"✅ Correct! You earned {DEFAULT_TOKEN_REWARD} token(s).", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Wrong! Correct answer was `{pending.get('answer')}`.", parse_mode="Markdown")

    _pending_riddles.pop(user_id, None)

# ------------------------
# Callback handler for Play Again
# ------------------------
async def games_callback_query(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    # format: games:repeat:<command>:<args>
    parts = data.split(":", 3)
    if len(parts) < 4:
        return
    _, action, cmd_name, arg_text = parts
    if action != "repeat":
        return

    # transform arg_text to argv list
    if arg_text == "_" or arg_text == "":
        argv = []
    else:
        argv = arg_text.split(":")

    # simulate calling the command handlers
    fake_update = update  # reuse update; context.args = argv
    context.args = argv
    # dispatch to correct function
    if cmd_name == "sbet":
        await sbet(fake_update, context)
    elif cmd_name == "roll":
        await roll_cmd(fake_update, context)
    elif cmd_name == "gamble":
        await gamble(fake_update, context)
    elif cmd_name == "basket":
        await basket(fake_update, context)
    elif cmd_name == "dart":
        await dart(fake_update, context)
    elif cmd_name == "stour":
        await stour(fake_update, context)
    else:
        await query.message.reply_text("Unknown replay command.")

# ------------------------
# Register handlers
# ------------------------
application.add_handler(CommandHandler("sbet", sbet, block=False))
application.add_handler(CommandHandler("roll", roll_cmd, block=False))
application.add_handler(CommandHandler("gamble", gamble, block=False))
application.add_handler(CommandHandler("basket", basket, block=False))
application.add_handler(CommandHandler("dart", dart, block=False))
application.add_handler(CommandHandler("stour", stour, block=False))
application.add_handler(CommandHandler("riddle", riddle, block=False))

# This handler must be added to listen for riddle answers (text messages).
# We add it as a message handler by using a lambda wrapper via CommandHandler is not suitable.
# Instead, the bot's main message handler should call riddle_answer_listener on text messages;
# if your framework supports adding a general message handler here, uncomment and adapt:
# application.add_handler(MessageHandler(Filters.text & ~Filters.command, riddle_answer_listener, block=False))

application.add_handler(CallbackQueryHandler(games_callback_query, pattern=r"^games:repeat:", block=False))

# Note: If your framework doesn't automatically pass non-command messages to `riddle_answer_listener`,
# add a message handler for plain text in your main bot setup:
# from telegram.ext import MessageHandler, Filters
# application.add_handler(MessageHandler(Filters.text & ~Filters.command, riddle_answer_listener, block=False))

# End of games.py