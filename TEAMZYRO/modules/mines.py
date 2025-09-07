import random
import math
import asyncio
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from TEAMZYRO import ZYRO as bot, user_collection

active_games = {}

# Start Mines
@bot.on_message(filters.command("mines"))
async def start_mines(client, message):
    user_id = message.from_user.id
    args = message.text.split()
    
    if len(args) < 3:
        return await message.reply("Usage: /mines [coins] [bombs]")

    try:
        bet = int(args[1])
        bombs = int(args[2])
    except:
        return await message.reply("⚠ Invalid numbers")

    if bombs < 2 or bombs > 20:
        return await message.reply("⚠ Bombs must be between 2 and 20!")

    user = await user_collection.find_one({"id": user_id})
    balance = user.get("balance", 0) if user else 0
    if balance < bet:
        return await message.reply("🚨 Not enough coins")

    # deduct bet
    await user_collection.update_one({"id": user_id}, {"$inc": {"balance": -bet}}, upsert=True)

    # create game
    mine_positions = random.sample(range(25), bombs)
    active_games[user_id] = {
        "bet": bet,
        "bombs": bombs,
        "mine_positions": mine_positions,
        "clicked": [],
        "multiplier": 1.0
    }

    # make keyboard
    keyboard = []
    for i in range(5):
        row = [InlineKeyboardButton("❓", callback_data=f"tile:{user_id}:{i*5+j}") for j in range(5)]
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("💸 Cash Out", callback_data=f"cashout:{user_id}")])

    await message.reply(
        f"🎮 Mines Game Started!\nBet: {bet}\nBombs: {bombs}\nMultiplier: 1.00x",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# Tile click
@bot.on_callback_query(filters.regex(r"^tile:(\d+):(\d+)$"))
async def tap_tile(client, cq):
    user_id, pos = cq.data.split(":")[1:]
    user_id = int(user_id)
    pos = int(pos)

    if cq.from_user.id != user_id:
        return await cq.answer("This is not your game!", show_alert=True)

    game = active_games.get(user_id)
    if not game:
        return await cq.answer("⚠ No active game!", show_alert=True)

    if pos in game["clicked"]:
        return await cq.answer("Already opened!", show_alert=True)

    game["clicked"].append(pos)

    # mine hit → game over + reveal board
    if pos in game["mine_positions"]:
        del active_games[user_id]

        keyboard = []
        for i in range(5):
            row = []
            for j in range(5):
                idx = i*5+j
                if idx in game["mine_positions"]:
                    row.append(InlineKeyboardButton("💣", callback_data="ignore"))
                elif idx in game["clicked"]:
                    row.append(InlineKeyboardButton("✅", callback_data="ignore"))
                else:
                    row.append(InlineKeyboardButton("❎", callback_data="ignore"))
            keyboard.append(row)

        return await cq.message.edit_text(
            f"💥 Boom! Mine hit.\nLost: {game['bet']} coins.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # safe click → multiplier increase
    game["multiplier"] += 0.05
    potential_win = math.floor(game["bet"] * game["multiplier"])

    # update board
    keyboard = []
    for i in range(5):
        row = []
        for j in range(5):
            idx = i*5+j
            if idx in game["clicked"]:
                row.append(InlineKeyboardButton("✅", callback_data="ignore"))
            else:
                row.append(InlineKeyboardButton("❓", callback_data=f"tile:{user_id}:{idx}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("💸 Cash Out", callback_data=f"cashout:{user_id}")])

    await cq.message.edit_text(
        f"🎮 Mines Game\nBet: {game['bet']}\nBombs: {game['bombs']}\nMultiplier: {game['multiplier']:.2f}x\nPotential Win: {potential_win}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# Cashout with animation
@bot.on_callback_query(filters.regex(r"^cashout:(\d+)$"))
async def cashout(client, cq):
    user_id = int(cq.matches[0].group(1))
    if cq.from_user.id != user_id:
        return await cq.answer("This is not your game!", show_alert=True)

    game = active_games.pop(user_id, None)
    if not game:
        return await cq.answer("⚠ No active game!", show_alert=True)

    earned = math.floor(game["bet"] * game["multiplier"])
    await user_collection.update_one({"id": user_id}, {"$inc": {"balance": earned}}, upsert=True)
    user = await user_collection.find_one({"id": user_id})
    new_balance = user.get("balance", 0)

    # --- Animation frames (coin buildup) ---
    try:
        frames = [
            f"💸 Cashing out...",
            f"💸 Cashing out... 💰",
            f"💸 Cashing out... 💰💰",
            f"💸 Cashing out... 💰💰💰",
            f"💸 Cashing out... 💰💰💰💰",
            f"💸 Cashing out... 💰💰💰💰💰"
        ]
        # Play frames (small sleeps to simulate animation)
        for frame in frames:
            # edit message (ignore if message not modified)
            try:
                await cq.message.edit_text(frame)
            except Exception:
                pass
            await asyncio.sleep(0.5)
    except Exception:
        # if anything goes wrong with animation, continue to final result
        pass

    # reveal board after animation
    keyboard = []
    for i in range(5):
        row = []
        for j in range(5):
            idx = i*5+j
            if idx in game["mine_positions"]:
                row.append(InlineKeyboardButton("💣", callback_data="ignore"))
            elif idx in game["clicked"]:
                row.append(InlineKeyboardButton("✅", callback_data="ignore"))
            else:
                row.append(InlineKeyboardButton("❎", callback_data="ignore"))
        keyboard.append(row)

    # final result edit
    await cq.message.edit_text(
        f"✅ Cashed out!\nWon: {earned} coins\nMultiplier: {game['multiplier']:.2f}x\nBalance: {new_balance}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ✅ Ignore button handler
@bot.on_callback_query(filters.regex("^ignore$"))
async def ignore_button(client, cq):
    await cq.answer()  # no alert, no response
