from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import random
from motor.motor_asyncio import AsyncIOMotorClient

# -------------------- MongoDB Setup --------------------
MONGO_URL = "mongodb+srv://Gojowaifu:waifu123@gojowaifu.royysxq.mongodb.net/?retryWrites=true&w=majority&appName=Gojowaifu"  # Replace with your MongoDB URI
mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client["Gojowaifu"]
users = db["users"]

# -------------------- User Balance --------------------
async def get_balance(user_id: int) -> int:
    """Fetch the user's balance. If user not exists, start with 0."""
    user = await users.find_one({"user_id": user_id})
    if not user:
        await users.insert_one({"user_id": user_id, "balance": 0})
        return 0
    return user["balance"]

async def update_balance(user_id: int, amount: int):
    """Add or subtract amount from user balance."""
    await users.update_one(
        {"user_id": user_id},
        {"$inc": {"balance": amount}},
        upsert=True
    )

# -------------------- Active Games --------------------
active_games = {}  # Store ongoing games per user

# -------------------- /mines Command --------------------
@Client.on_message(filters.command("mines"))
async def mines_start(client, message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) < 3:
        return await message.reply("Usage: `/mines <bet> <mines>`", quote=True)

    # Validate bet and mines_count
    try:
        bet = int(args[1])
        mines_count = int(args[2])
    except ValueError:
        return await message.reply("❌ Bet and mines must be numbers!", quote=True)

    # Get user's actual balance
    balance = await get_balance(user_id)
    if bet > balance:
        return await message.reply("❌ Not enough balance!", quote=True)

    if not (1 <= mines_count <= 24):
        return await message.reply("❌ Mines must be between 1 and 24.", quote=True)

    # Deduct bet from user's balance
    await update_balance(user_id, -bet)

    # Setup game board
    board = ["❓"] * 25
    mine_positions = random.sample(range(25), mines_count)

    active_games[user_id] = {
        "board": board,
        "mines": mine_positions,
        "bet": bet,
        "revealed": set(),
        "status": "playing"
    }

    # Build inline keyboard
    keyboard = []
    for i in range(0, 25, 5):
        row = [InlineKeyboardButton(board[j], callback_data=f"mines:{user_id}:{j}") for j in range(i, i+5)]
        keyboard.append(row)

    await message.reply(
        f"💣 Mines Game Started!\n\nBet: `{bet}` coins\nMines: `{mines_count}`\nBalance after bet: `{balance - bet}`",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# -------------------- Callback for Mines Game --------------------
@Client.on_callback_query(filters.regex(r"^mines"))
async def mines_play(client, callback_query: CallbackQuery):
    data = callback_query.data.split(":")
    user_id, pos = int(data[1]), int(data[2])

    if callback_query.from_user.id != user_id:
        return await callback_query.answer("❌ This is not your game!", show_alert=True)

    game = active_games.get(user_id)
    if not game or game["status"] != "playing":
        return await callback_query.answer("❌ No active game!", show_alert=True)

    if pos in game["revealed"]:
        return await callback_query.answer("❌ Already revealed!", show_alert=True)

    # Hit a mine → lose
    if pos in game["mines"]:
        for m in game["mines"]:
            game["board"][m] = "💣"
        game["status"] = "lost"
        await callback_query.edit_message_text(
            "💥 Boom! You hit a mine.\nBetter luck next time!",
            reply_markup=None
        )
        return

    # Safe cell
    game["revealed"].add(pos)
    game["board"][pos] = "✅"

    # Reward calculation
    safe_cells = 25 - len(game["mines"])
    reward = int(game["bet"] * len(game["revealed"]) / safe_cells)

    # Update inline keyboard
    keyboard = []
    for i in range(0, 25, 5):
        row = [InlineKeyboardButton(game["board"][j], callback_data=f"mines:{user_id}:{j}") for j in range(i, i+5)]
        keyboard.append(row)

    await callback_query.edit_message_text(
        f"✅ Safe! Current potential win: `{reward}` coins\nRevealed: {len(game['revealed'])}/{safe_cells}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    # All safe cells revealed → win
    if len(game["revealed"]) == safe_cells:
        await update_balance(user_id, game["bet"] + reward)
        game["status"] = "won"
        await callback_query.edit_message_text(
            f"🎉 You cleared the board!\nYou won `{game['bet'] + reward}` coins!",
            reply_markup=None
    )
