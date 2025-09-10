import random
import math
import asyncio
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from TEAMZYRO import ZYRO as bot, user_collection

# Active games memory cache
active_games = {}

# --- Helper: Save game to DB ---
async def save_game(user_id, game):
    await user_collection.update_one(
        {"id": user_id},
        {"$set": {"active_game": game}},
        upsert=True
    )
    active_games[user_id] = game

# --- Helper: Load game from DB ---
async def load_game(user_id):
    if user_id in active_games:
        return active_games[user_id]
    user = await user_collection.find_one({"id": user_id})
    if user and "active_game" in user:
        active_games[user_id] = user["active_game"]
        return active_games[user_id]
    return None

# --- Helper: Delete game ---
async def delete_game(user_id):
    active_games.pop(user_id, None)
    await user_collection.update_one(
        {"id": user_id},
        {"$unset": {"active_game": ""}}
    )

# --- Start Mines ---
@bot.on_message(filters.command("mines"))
async def start_mines(client, message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) < 3:
        return await message.reply("Usage: /mines [coins] [bombs]")

    try:
        bet = int(args[1])
        bombs = int(args[2])
    except ValueError:
        return await message.reply("⚠ Invalid numbers")

    if bombs < 2 or bombs > 20:
        return await message.reply("⚠ Bombs must be between 2 and 20!")

    user = await user_collection.find_one({"id": user_id})
    balance = user.get("balance", 0) if user else 0
    if balance < bet:
        return await message.reply("🚨 Not enough coins")

    # Deduct bet
    await user_collection.update_one({"id": user_id}, {"$inc": {"balance": -bet}}, upsert=True)

    # Create game
    mine_positions = random.sample(range(25), bombs)
    game = {
        "bet": bet,
        "bombs": bombs,
        "mine_positions": mine_positions,
        "clicked": [],
        "multiplier": 1.0
    }
    await save_game(user_id, game)

    # Build keyboard
    keyboard = [
        [InlineKeyboardButton("❓", callback_data=f"mines_tile:{user_id}:{i*5+j}") for j in range(5)]
        for i in range(5)
    ]
    keyboard.append([InlineKeyboardButton("💸 Cash Out", callback_data=f"mines_cashout:{user_id}")])

    await message.reply(
        f"🎮 Mines Game Started!\nBet: {bet}\nBombs: {bombs}\nMultiplier: 1.00x",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- Tile click handler ---
@bot.on_callback_query(filters.regex(r"^mines_tile:"))
async def tap_tile(client, cq):
    try:
        _, user_id_str, pos_str = cq.data.split(":")
        user_id = int(user_id_str)
        pos = int(pos_str)
    except Exception:
        return await cq.answer("⚠ Invalid button!", show_alert=True)

    if cq.from_user.id != user_id:
        return await cq.answer("This is not your game!", show_alert=True)

    game = await load_game(user_id)
    if not game:
        return await cq.answer("⚠ No active game!", show_alert=True)

    if pos in game["clicked"]:
        return await cq.answer("Already opened!", show_alert=True)

    game["clicked"].append(pos)

    # --- If mine clicked ---
    if pos in game["mine_positions"]:
        await delete_game(user_id)
        keyboard = []
        for i in range(5):
            row = []
            for j in range(5):
                idx = i*5+j
                if idx in game["mine_positions"]:
                    row.append(InlineKeyboardButton("💣", callback_data="mines_ignore"))
                elif idx in game["clicked"]:
                    row.append(InlineKeyboardButton("✅", callback_data="mines_ignore"))
                else:
                    row.append(InlineKeyboardButton("❎", callback_data="mines_ignore"))
            keyboard.append(row)
        
        return await cq.message.edit_text(
            f"💥 Boom! Mine hit.\nLost: {game['bet']} coins.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # --- Safe click ---
    game["multiplier"] = round(game["multiplier"] + 0.05, 2)
    potential_win = math.floor(game["bet"] * game["multiplier"])
    await save_game(user_id, game)

    # Update board
    keyboard = []
    for i in range(5):
        row = []
        for j in range(5):
            idx = i*5+j
            if idx in game["clicked"]:
                row.append(InlineKeyboardButton("✅", callback_data="mines_ignore"))
            else:
                row.append(InlineKeyboardButton("❓", callback_data=f"mines_tile:{user_id}:{idx}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("💸 Cash Out", callback_data=f"mines_cashout:{user_id}")])

    await cq.message.edit_text(
        f"🎮 Mines Game\nBet: {game['bet']}\nBombs: {game['bombs']}\nMultiplier: {game['multiplier']:.2f}x\nPotential Win: {potential_win}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await cq.answer("Tile opened ✅")

# --- Cashout handler ---
@bot.on_callback_query(filters.regex(r"^mines_cashout:"))
async def cashout(client, cq):
    await cq.answer()
    user_id = int(cq.data.split(":")[1])
    if cq.from_user.id != user_id:
        return await cq.answer("This is not your game!", show_alert=True)

    game = await load_game(user_id)
    if not game:
        return await cq.answer("⚠ No active game!", show_alert=True)

    await delete_game(user_id)
    earned = math.floor(game["bet"] * game["multiplier"])
    await user_collection.update_one({"id": user_id}, {"$inc": {"balance": earned}}, upsert=True)
    user = await user_collection.find_one({"id": user_id})
    new_balance = user.get("balance", 0)

    # Reveal board
    keyboard = []
    for i in range(5):
        row = []
        for j in range(5):
            idx = i*5+j
            if idx in game["mine_positions"]:
                row.append(InlineKeyboardButton("💣", callback_data="mines_ignore"))
            elif idx in game["clicked"]:
                row.append(InlineKeyboardButton("✅", callback_data="mines_ignore"))
            else:
                row.append(InlineKeyboardButton("❎", callback_data="mines_ignore"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("❌ Close", callback_data=f"mines_close:{user_id}")])

    await cq.message.edit_text(
        f"✅ Cashed out!\nWon: {earned} coins\nMultiplier: {game['multiplier']:.2f}x\nBalance: {new_balance}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- Ignore button handler ---
@bot.on_callback_query(filters.regex("^mines_ignore$"))
async def ignore_button(client, cq):
    await cq.answer()

# --- Close button handler ---
@bot.on_callback_query(filters.regex(r"^mines_close:"))
async def close_game(client, cq):
    await cq.answer()
    try:
        await cq.message.delete()
    except Exception:
        pass
