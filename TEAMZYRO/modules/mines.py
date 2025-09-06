import random
import math
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from TEAMZYRO import ZYRO as bot
from motor.motor_asyncio import AsyncIOMotorClient

# -------------------- MongoDB Setup --------------------
MONGO_URL = "mongodb+srv://Gojowaifu:waifu123@gojowaifu.royysxq.mongodb.net/?retryWrites=true&w=majority&appName=Gojowaifu"  # Replace with your MongoDB URI
mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client["gojowaifu"]
user_collection = db["users"]

# -------------------- Constants --------------------
MUST_JOIN = -1002792716047
active_games = {}  # {user_id: {...}}

# -------------------- Helper Functions --------------------
async def is_joined(client, user_id):
    try:
        member = await client.get_chat_member(MUST_JOIN, user_id)
        return member.status not in ["left", "kicked"]
    except:
        return False

async def get_balance(user_id: int) -> int:
    """Fetch user balance from MongoDB."""
    user = await user_collection.find_one({"id": user_id})
    return user.get("coins", 0) if user else 0

async def update_balance(user_id: int, amount: int):
    """Update user balance in MongoDB."""
    await user_collection.update_one({"id": user_id}, {"$inc": {"coins": amount}}, upsert=True)

# -------------------- /mines Command --------------------
@bot.on_message(filters.command("mines"))
async def start_mines(client, message):
    user_id = message.from_user.id
    args = message.text.split()

    # Must join check
    if not await is_joined(client, user_id):
        return await message.reply(
            "❌ You must join the required group first!",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Join Group ✅", url="https://t.me/+V-_VFMB8nV40YzJl")]
                ]
            )
        )

    if len(args) < 3:
        return await message.reply("Usage: /mines <coins> <bombs>")

    try:
        bet = int(args[1])
        bombs = int(args[2])
    except:
        return await message.reply("⚠ Invalid numbers. Example: /mines 50 3")

    if bombs >= 10 or bombs < 1:
        return await message.reply("⚠ Bombs must be between 1 and 9.")

    # Balance check
    balance = await get_balance(user_id)
    if balance < bet:
        return await message.reply("🚨 Not enough coins to play!")

    # Deduct bet immediately
    await update_balance(user_id, -bet)

    # Generate mine positions
    mine_positions = random.sample(range(25), bombs)

    active_games[user_id] = {
        "bet": bet,
        "bombs": bombs,
        "mine_positions": mine_positions,
        "clicked": [],
        "multiplier": 1.0
    }

    # Build grid
    grid = []
    for i in range(5):
        row = [InlineKeyboardButton("❓", callback_data=f"mine_{user_id}_{i*5+j}") for j in range(5)]
        grid.append(row)
    grid.append([InlineKeyboardButton("💸 Cash Out", callback_data=f"cashout_{user_id}")])

    await message.reply(
        f"🎮 **Mines Game Started!**\n\n"
        f"💰 Bet: {bet} coins\n💣 Bombs: {bombs}\nMultiplier: 1.0x\nBalance: {balance - bet} coins\n\n"
        f"👉 Tap any tile to begin!",
        reply_markup=InlineKeyboardMarkup(grid)
    )

# -------------------- Tile Tap --------------------
@bot.on_callback_query(filters.regex(r"mine_(\d+)_(\d+)"))
async def tap_tile(client, cq):
    user_id = int(cq.matches[0].group(1))
    pos = int(cq.matches[0].group(2))

    if cq.from_user.id != user_id:
        return await cq.answer("This is not your game!", show_alert=True)

    game = active_games.get(user_id)
    if not game:
        return await cq.answer("⚠ Game not found!", show_alert=True)

    if pos in game["clicked"]:
        return await cq.answer("Already opened!", show_alert=True)

    game["clicked"].append(pos)

    if pos in game["mine_positions"]:
        # Boom 💥 lost game
        del active_games[user_id]
        return await cq.message.edit_text(
            f"💥 **Boom! You hit a mine.**\n❌ You lost {game['bet']} coins."
        )

    # Safe tile → increase multiplier
    game["multiplier"] += 0.25
    earned = math.floor(game["bet"] * game["multiplier"])

    # Real-time balance update in DB (potential win not yet cashed)
    current_balance = await get_balance(user_id)
    potential_total = current_balance + earned

    # Update grid with ✅
    grid = []
    for i in range(5):
        row = []
        for j in range(5):
            idx = i*5+j
            if idx in game["clicked"]:
                row.append(InlineKeyboardButton("✅", callback_data="ignore"))
            else:
                row.append(InlineKeyboardButton("❓", callback_data=f"mine_{user_id}_{idx}"))
        grid.append(row)
    grid.append([InlineKeyboardButton("💸 Cash Out", callback_data=f"cashout_{user_id}")])

    await cq.message.edit_text(
        f"🎮 **Mines Game**\n\n"
        f"💰 Bet: {game['bet']} coins\n"
        f"💣 Bombs: {game['bombs']}\n"
        f"Multiplier: {game['multiplier']}x\n"
        f"Potential Win: {earned} coins\n"
        f"Current Balance: {current_balance} coins\n\n"
        f"👉 Keep going or Cash Out?",
        reply_markup=InlineKeyboardMarkup(grid)
    )

# -------------------- Cash Out --------------------
@bot.on_callback_query(filters.regex(r"cashout_(\d+)"))
async def cashout(client, cq):
    user_id = int(cq.matches[0].group(1))

    if cq.from_user.id != user_id:
        return await cq.answer("This is not your game!", show_alert=True)

    game = active_games.get(user_id)
    if not game:
        return await cq.answer("⚠ No active game!", show_alert=True)

    earned = math.floor(game["bet"] * game["multiplier"])
    del active_games[user_id]

    # Add winnings to MongoDB
    await update_balance(user_id, earned)

    # Get updated balance
    new_balance = await get_balance(user_id)

    await cq.message.edit_text(
        f"✅ **You cashed out!**\n\n"
        f"💰 Won: {earned} coins\nMultiplier: {game['multiplier']}x\n"
        f"💎 New Balance: {new_balance} coins"
    )
