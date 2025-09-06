from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
import math

# Required Group ID (must join)
MUST_JOIN = -1002792716047

# Mines game storage
active_games = {}  # {user_id: {...}}

def is_joined(client, user_id):
    try:
        member = client.get_chat_member(MUST_JOIN, user_id)
        return member.status not in ["left", "kicked"]
    except:
        return False


@Client.on_message(filters.command("mines"))
async def start_mines(client, message):
    user_id = message.from_user.id
    args = message.text.split()

    if not is_joined(client, user_id):
        return await message.reply(
            "❌ You must join the required group first!",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Join Group ✅", url=f"https://t.me/c/{str(MUST_JOIN)[4:]}")]]
            )
        )

    if len(args) < 3:
        return await message.reply("Usage: `/mines <coins> <bombs>`")

    try:
        bet = int(args[1])
        bombs = int(args[2])
    except:
        return await message.reply("⚠ Invalid numbers. Example: `/mines 50 3`")

    if bombs >= 10 or bombs < 1:
        return await message.reply("⚠ Bombs must be between 1 and 9.")

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
        f"💰 Bet: {bet} coins\n💣 Bombs: {bombs}\nMultiplier: 1.0x\n\n"
        f"👉 Tap any tile to begin!",
        reply_markup=InlineKeyboardMarkup(grid)
    )


@Client.on_callback_query(filters.regex(r"mine_(\d+)_(\d+)"))
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
        # Boom 💥
        del active_games[user_id]
        return await cq.message.edit_text(
            f"💥 **Boom! You hit a mine.**\nYou lost {game['bet']} coins."
        )

    # Safe tile
    game["multiplier"] += 0.25
    earned = math.floor(game["bet"] * game["multiplier"])

    # Update grid
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
        f"Potential Win: {earned} coins\n\n"
        f"👉 Keep going or Cash Out?",
        reply_markup=InlineKeyboardMarkup(grid)
    )


@Client.on_callback_query(filters.regex(r"cashout_(\d+)"))
async def cashout(client, cq):
    user_id = int(cq.matches[0].group(1))

    if cq.from_user.id != user_id:
        return await cq.answer("This is not your game!", show_alert=True)

    game = active_games.get(user_id)
    if not game:
        return await cq.answer("⚠ No active game!", show_alert=True)

    earned = math.floor(game["bet"] * game["multiplier"])
    del active_games[user_id]

    await cq.message.edit_text(
        f"✅ **You cashed out!**\n\n"
        f"💰 Won: {earned} coins\nMultiplier: {game['multiplier']}x"
  )
