# modules/uno.py
import random
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import CommandHandler, CallbackQueryHandler, InlineQueryHandler, CallbackContext, MessageHandler, filters
from shivu import application, user_collection
from collections import defaultdict

# ------------------------
# UNO Game Configuration
# ------------------------
SKIP_TIMEOUT = 90  # seconds before a player can be skipped
MAX_PLAYERS = 10
MIN_PLAYERS = 2

# Card colors and values
COLORS = ['r', 'g', 'b', 'y']  # red, green, blue, yellow
COLOR_NAMES = {'r': 'Red', 'g': 'Green', 'b': 'Yellow', 'y': 'Blue'}
NUMBERS = list(range(10)) + list(range(1, 10))  # 0 appears once, 1-9 appear twice
SPECIAL_CARDS = ['skip', 'reverse', '+2'] * 2  # Each appears twice per color
WILD_CARDS = ['wild', '+4'] * 4  # 4 of each

# Sticker pack file IDs mapping (you'll need to update these with actual file_ids from the pack)
# Format: 'color_value' or 'wild' or 'wild_+4'
CARD_STICKERS = {
    # You need to get actual file_ids from https://t.me/addstickers/classic_colorblind
    # Example format:
    # 'r_0': 'CAACAgIAAxkBAAIC...',
    # 'g_5': 'CAACAgIAAxkBAAIC...',
    # 'wild': 'CAACAgIAAxkBAAIC...',
}

# ------------------------
# Game State Management
# ------------------------
class UnoGame:
    def __init__(self, chat_id, creator_id, creator_name):
        self.chat_id = chat_id
        self.creator_id = creator_id
        self.players = []  # List of {id, name, cards, drew_card}
        self.deck = []
        self.discard_pile = []
        self.current_player_idx = 0
        self.direction = 1  # 1 for forward, -1 for reverse
        self.started = False
        self.lobby_open = True
        self.current_color = None
        self.last_action_time = datetime.utcnow()
        self.settings = {
            'language': 'en',
            'translations_enabled': False
        }
        
        # Add creator
        self.add_player(creator_id, creator_name)
    
    def add_player(self, user_id, name):
        if len(self.players) >= MAX_PLAYERS:
            return False
        if any(p['id'] == user_id for p in self.players):
            return False
        self.players.append({
            'id': user_id,
            'name': name,
            'cards': [],
            'drew_card': False,
            'uno_called': False
        })
        return True
    
    def remove_player(self, user_id):
        self.players = [p for p in self.players if p['id'] != user_id]
        if self.current_player_idx >= len(self.players) and self.players:
            self.current_player_idx = 0
    
    def create_deck(self):
        deck = []
        # Numbered cards
        for color in COLORS:
            for number in NUMBERS:
                deck.append(f"{color}_{number}")
        # Special cards
        for color in COLORS:
            for special in ['skip', 'reverse', '+2', '+2']:
                deck.append(f"{color}_{special}")
        # Wild cards
        deck.extend(['wild'] * 4)
        deck.extend(['wild_+4'] * 4)
        random.shuffle(deck)
        return deck
    
    def deal_cards(self):
        self.deck = self.create_deck()
        for player in self.players:
            player['cards'] = [self.deck.pop() for _ in range(7)]
        # First card
        first_card = self.deck.pop()
        while first_card.startswith('wild'):
            self.deck.insert(0, first_card)
            random.shuffle(self.deck)
            first_card = self.deck.pop()
        self.discard_pile.append(first_card)
        self.current_color = first_card.split('_')[0]
    
    def draw_card(self):
        if len(self.deck) < 5:
            # Reshuffle discard pile into deck
            top_card = self.discard_pile.pop()
            self.deck.extend(self.discard_pile)
            self.discard_pile = [top_card]
            random.shuffle(self.deck)
        return self.deck.pop() if self.deck else None
    
    def current_player(self):
        return self.players[self.current_player_idx] if self.players else None
    
    def next_player(self):
        self.current_player_idx = (self.current_player_idx + self.direction) % len(self.players)
        self.last_action_time = datetime.utcnow()
    
    def can_play_card(self, card):
        if not self.discard_pile:
            return False
        
        if card.startswith('wild'):
            return True
        
        top_card = self.discard_pile[-1]
        card_parts = card.split('_')
        top_parts = top_card.split('_')
        
        # Match color or value
        if card_parts[0] == self.current_color:
            return True
        if len(card_parts) > 1 and len(top_parts) > 1 and card_parts[1] == top_parts[1]:
            return True
        
        return False
    
    def play_card(self, player_id, card):
        player = next((p for p in self.players if p['id'] == player_id), None)
        if not player or card not in player['cards']:
            return False, "Invalid card"
        
        if not self.can_play_card(card):
            return False, "Cannot play this card"
        
        player['cards'].remove(card)
        self.discard_pile.append(card)
        player['drew_card'] = False
        
        # Handle special cards
        card_parts = card.split('_')
        if len(card_parts) > 1:
            action = card_parts[1]
            if action == 'skip':
                self.next_player()
            elif action == 'reverse':
                self.direction *= -1
                if len(self.players) == 2:
                    self.next_player()
            elif action == '+2':
                self.next_player()
                next_p = self.current_player()
                for _ in range(2):
                    drawn = self.draw_card()
                    if drawn:
                        next_p['cards'].append(drawn)
                self.next_player()
                return True, f"{next_p['name']} draws 2 cards and is skipped"
        
        if card.startswith('wild'):
            # Color will be chosen by player
            return True, "choose_color"
        
        # Update current color
        self.current_color = card_parts[0]
        
        # Check for UNO
        if len(player['cards']) == 1:
            player['uno_called'] = True
            return True, "UNO!"
        elif len(player['cards']) == 0:
            return True, "WIN"
        
        return True, "success"

# Active games: chat_id -> UnoGame
active_games = {}

# ------------------------
# Helper Functions
# ------------------------
async def ensure_user_doc(user_id: int, first_name=None, username=None):
    doc = await user_collection.find_one({'id': user_id})
    if doc:
        return doc
    new = {'id': user_id, 'first_name': first_name, 'username': username, 'balance': 0, 'tokens': 0}
    await user_collection.insert_one(new)
    return new

def get_card_display(card):
    """Convert card code to readable format"""
    if card == 'wild':
        return "🌈 Wild"
    if card == 'wild_+4':
        return "🌈 Wild +4"
    
    parts = card.split('_')
    color = COLOR_NAMES.get(parts[0], parts[0])
    value = parts[1] if len(parts) > 1 else ''
    
    emoji = {'r': '🔴', 'g': '🟢', 'b': '🔵', 'y': '🟡'}.get(parts[0], '')
    return f"{emoji} {color} {value}"

def format_game_state(game):
    """Create game state message"""
    top_card = game.discard_pile[-1] if game.discard_pile else "None"
    current = game.current_player()
    
    players_text = "\n".join([
        f"{'➡️ ' if i == game.current_player_idx else ''}{p['name']}: {len(p['cards'])} cards"
        for i, p in enumerate(game.players)
    ])
    
    return (
        f"🎮 <b>UNO Game</b>\n\n"
        f"Top card: {get_card_display(top_card)}\n"
        f"Current color: {COLOR_NAMES.get(game.current_color, 'None')}\n"
        f"Cards in deck: {len(game.deck)}\n\n"
        f"<b>Players:</b>\n{players_text}\n\n"
        f"Current turn: <b>{current['name']}</b>"
    )

# ------------------------
# Command Handlers
# ------------------------
async def new_game(update: Update, context: CallbackContext):
    """Create a new UNO game"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    if chat_id in active_games:
        await update.message.reply_text("A game is already running in this chat. Use /join to join!")
        return
    
    game = UnoGame(chat_id, user_id, user_name)
    active_games[chat_id] = game
    
    keyboard = [
        [InlineKeyboardButton("Join Game", callback_data=f"uno:join:{chat_id}")],
        [InlineKeyboardButton("Start Game", callback_data=f"uno:start:{chat_id}")],
    ]
    
    await update.message.reply_text(
        f"🎮 <b>New UNO Game Created!</b>\n\n"
        f"Creator: {user_name}\n"
        f"Players: 1/{MAX_PLAYERS}\n\n"
        f"Waiting for players to /join...\n"
        f"Need at least {MIN_PLAYERS} players to start.",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def join_game(update: Update, context: CallbackContext):
    """Join an existing game"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    game = active_games.get(chat_id)
    if not game:
        await update.message.reply_text("No active game. Use /new to start one!")
        return
    
    if game.started:
        await update.message.reply_text("Game already started!")
        return
    
    if not game.lobby_open:
        await update.message.reply_text("Lobby is closed!")
        return
    
    if game.add_player(user_id, user_name):
        await update.message.reply_text(
            f"✅ {user_name} joined the game!\n"
            f"Players: {len(game.players)}/{MAX_PLAYERS}"
        )
    else:
        await update.message.reply_text("Cannot join (already in game or lobby full)")

async def start_game(update: Update, context: CallbackContext):
    """Start the game"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    game = active_games.get(chat_id)
    if not game:
        await update.message.reply_text("No active game!")
        return
    
    if game.started:
        await update.message.reply_text("Game already started!")
        return
    
    if user_id != game.creator_id:
        await update.message.reply_text("Only the creator can start the game!")
        return
    
    if len(game.players) < MIN_PLAYERS:
        await update.message.reply_text(f"Need at least {MIN_PLAYERS} players to start!")
        return
    
    game.deal_cards()
    game.started = True
    game.lobby_open = False
    
    # Notify all players
    state_msg = format_game_state(game)
    await update.message.reply_text(
        f"{state_msg}\n\n"
        f"Game started! Use inline mode (@{context.bot.username}) to play cards.",
        parse_mode='HTML'
    )
    
    # Send cards to each player
    for player in game.players:
        try:
            cards_text = "\n".join([get_card_display(c) for c in player['cards']])
            await context.bot.send_message(
                player['id'],
                f"🎴 <b>Your cards:</b>\n\n{cards_text}\n\n"
                f"Use @{context.bot.username} in the game chat to play!",
                parse_mode='HTML'
            )
        except Exception:
            pass

async def leave_game(update: Update, context: CallbackContext):
    """Leave the current game"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    game = active_games.get(chat_id)
    if not game:
        await update.message.reply_text("No active game!")
        return
    
    game.remove_player(user_id)
    await update.message.reply_text(f"You left the game. {len(game.players)} players remaining.")
    
    if len(game.players) == 0:
        del active_games[chat_id]
        await update.message.reply_text("Game ended (no players left).")

async def close_lobby(update: Update, context: CallbackContext):
    """Close the lobby"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    game = active_games.get(chat_id)
    if not game or user_id != game.creator_id:
        return
    
    game.lobby_open = False
    await update.message.reply_text("🔒 Lobby closed.")

async def open_lobby(update: Update, context: CallbackContext):
    """Open the lobby"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    game = active_games.get(chat_id)
    if not game or user_id != game.creator_id:
        return
    
    game.lobby_open = True
    await update.message.reply_text("🔓 Lobby opened.")

async def kill_game(update: Update, context: CallbackContext):
    """Terminate the game"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    game = active_games.get(chat_id)
    if not game or user_id != game.creator_id:
        return
    
    del active_games[chat_id]
    await update.message.reply_text("💀 Game terminated.")

async def skip_player(update: Update, context: CallbackContext):
    """Skip current player if they're taking too long"""
    chat_id = update.effective_chat.id
    game = active_games.get(chat_id)
    
    if not game or not game.started:
        return
    
    time_elapsed = (datetime.utcnow() - game.last_action_time).total_seconds()
    if time_elapsed < SKIP_TIMEOUT:
        await update.message.reply_text(f"⏱ Wait {SKIP_TIMEOUT - int(time_elapsed)}s before skipping.")
        return
    
    current = game.current_player()
    game.next_player()
    await update.message.reply_text(f"⏭ Skipped {current['name']}'s turn!")

async def game_state(update: Update, context: CallbackContext):
    """Show current game state"""
    chat_id = update.effective_chat.id
    game = active_games.get(chat_id)
    
    if not game:
        await update.message.reply_text("No active game!")
        return
    
    await update.message.reply_text(format_game_state(game), parse_mode='HTML')

# ------------------------
# Inline Query Handler
# ------------------------
async def inline_query(update: Update, context: CallbackContext):
    """Handle inline queries for card selection"""
    query = update.inline_query.query
    user_id = update.inline_query.from_user.id
    
    # Find game where user is playing
    user_game = None
    for game in active_games.values():
        if any(p['id'] == user_id for p in game.players):
            user_game = game
            break
    
    if not user_game or not user_game.started:
        results = [
            InlineQueryResultArticle(
                id="no_game",
                title="No active game",
                input_message_content=InputTextMessageContent("Join a game first with /join")
            )
        ]
        await update.inline_query.answer(results, cache_time=1)
        return
    
    # Check if it's user's turn
    current = user_game.current_player()
    if current['id'] != user_id:
        results = [
            InlineQueryResultArticle(
                id="not_turn",
                title="Not your turn!",
                description=f"Wait for {current['name']} to play",
                input_message_content=InputTextMessageContent("It's not my turn yet!")
            )
        ]
        await update.inline_query.answer(results, cache_time=1)
        return
    
    player = next(p for p in user_game.players if p['id'] == user_id)
    
    # Build results
    results = []
    
    # Draw card option
    if not player['drew_card']:
        results.append(
            InlineQueryResultArticle(
                id="draw",
                title="🃏 Draw a card",
                input_message_content=InputTextMessageContent(f"/uno_draw")
            )
        )
    
    # Playable cards
    for i, card in enumerate(player['cards']):
        can_play = user_game.can_play_card(card)
        title = f"{'✅' if can_play else '❌'} {get_card_display(card)}"
        
        results.append(
            InlineQueryResultArticle(
                id=f"card_{i}",
                title=title,
                description="Play this card" if can_play else "Cannot play",
                input_message_content=InputTextMessageContent(f"/uno_play {card}")
            )
        )
    
    # Game state option
    results.append(
        InlineQueryResultArticle(
            id="state",
            title="❓ Game State",
            input_message_content=InputTextMessageContent("/uno_state")
        )
    )
    
    await update.inline_query.answer(results[:50], cache_time=1)

# ------------------------
# Callback Query Handler
# ------------------------
async def uno_callback(update: Update, context: CallbackContext):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    parts = data.split(':')
    
    if parts[1] == 'join':
        chat_id = int(parts[2])
        # Simulate join command
        context.args = []
        fake_update = Update(update.update_id, message=query.message)
        fake_update._effective_chat = query.message.chat
        fake_update._effective_user = query.from_user
        await join_game(fake_update, context)
    
    elif parts[1] == 'start':
        # Simulate start command
        fake_update = Update(update.update_id, message=query.message)
        fake_update._effective_chat = query.message.chat
        fake_update._effective_user = query.from_user
        await start_game(fake_update, context)
    
    elif parts[1] == 'color':
        # Color selection for wild cards
        chat_id = int(parts[2])
        color = parts[3]
        game = active_games.get(chat_id)
        if game:
            game.current_color = color
            game.next_player()
            await query.message.reply_text(
                f"Color changed to {COLOR_NAMES[color]}!\n\n{format_game_state(game)}",
                parse_mode='HTML'
            )

# ------------------------
# Register Handlers
# ------------------------
application.add_handler(CommandHandler("new", new_game, block=False))
application.add_handler(CommandHandler("join", join_game, block=False))
application.add_handler(CommandHandler("star", start_game, block=False))
application.add_handler(CommandHandler("leave", leave_game, block=False))
application.add_handler(CommandHandler("close", close_lobby, block=False))
application.add_handler(CommandHandler("open", open_lobby, block=False))
application.add_handler(CommandHandler("kill", kill_game, block=False))
application.add_handler(CommandHandler("skip", skip_player, block=False))
application.add_handler(CommandHandler("state", game_state, block=False))

application.add_handler(InlineQueryHandler(inline_query, block=False))
application.add_handler(CallbackQueryHandler(uno_callback, pattern=r"^uno:", block=False))