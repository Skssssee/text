from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
import math
from TEAMZYRO import ZYRO as bot   # 👈 Ye tumhare bot ka client hai
from TEAMZYRO import user_collection   # agar coins DB me rakhe ho

# Required Group ID (must join)
MUST_JOIN = -1002792716047

# Mines game storage
active_games = {}  # {user_id: {...}}

# Check if user joined required group
async def is_joined(bot, user_id):
    try:
        member = await bot.get_chat_member(MUST_JOIN, user_id)
        return member.status not in ["left", "kicked"]
    except:
        return False


@bot.on_message(filters.command("mines"))
async def start_mines(bot, message):
    user_id = message.from_user.id
    args = message.text.split()

    if not await is_joined(bot, user_id):
        return await message.reply(
            "❌ ʏᴏᴜ ᴍᴜꜱᴛ ᴊᴏɪɴ ᴛʜᴇ ʀᴇǫᴜɪʀᴇᴅ ɢʀᴏᴜᴘ ꜰɪʀꜱᴛ!",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("ᴊᴏɪɴ ɢʀᴏᴜᴘ ✅", url=f"https://t.me/c/{str(MUST_JOIN)[4:]}")]]
            )
        )

    if len(args) < 3:
        return await message.reply("ᴜꜱᴀɢᴇ: `/mines <coins> <bombs>`")

    try:
        bet = int(args[1])
        bombs = int(args[2])
    except:
        return await message.reply("⚠ ɪɴᴠᴀʟɪᴅ ɴᴜᴍʙᴇʀꜱ. ᴇxᴀᴍᴘʟᴇ: `/mines 50 3`")

    if bombs >= 10 or bombs < 1:
        return await message.reply("⚠ ʙᴏᴍʙꜱ ᴍᴜꜱᴛ ʙᴇ ʙᴇᴛᴡᴇᴇɴ 1 ᴀɴᴅ 9.")

    # (optional) check coins from DB
    user_data = await user_collection.find_one({"id": user_id})
    if not user_data or user_data.get("coins", 0) < bet:
        return await message.reply("💸 ɴᴏᴛ ᴇɴᴏᴜɢʜ ᴄᴏɪɴꜱ!")

    # deduct coins from user wallet
    await user_collection.update_one({"id": user_id}, {"$inc": {"coins": -bet}}, upsert=True)

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
    grid.append([InlineKeyboardButton("💸 ᴄᴀꜱʜ ᴏᴜᴛ", callback_data=f"cashout_{user_id}")])

    await message.reply(
        f"🎮 **ᴍɪɴᴇꜱ ɢᴀᴍᴇ ꜱᴛᴀʀᴛᴇᴅ!**\n\n"
        f"💰 ʙᴇᴛ: {bet} ᴄᴏɪɴꜱ\n💣 ʙᴏᴍʙꜱ: {bombs}\n"
        f"ᴍᴜʟᴛɪᴘʟɪᴇʀ: 1.0x\n\n"
        f"👉 ᴛᴀᴘ ᴀɴʏ ᴛɪʟᴇ ᴛᴏ ʙᴇɢɪɴ!",
        reply_markup=InlineKeyboardMarkup(grid)
    )


@bot.on_callback_query(filters.regex(r"mine_(\d+)_(\d+)"))
async def tap_tile(bot, cq):
    user_id = int(cq.matches[0].group(1))
    pos = int(cq.matches[0].group(2))

    if cq.from_user.id != user_id:
        return await cq.answer("⚠ ɴᴏᴛ ʏᴏᴜʀ ɢᴀᴍᴇ!", show_alert=True)

    game = active_games.get(user_id)
    if not game:
        return await cq.answer("⚠ ɴᴏ ᴀᴄᴛɪᴠᴇ ɢᴀᴍᴇ!", show_alert=True)

    if pos in game["clicked"]:
        return await cq.answer("ᴀʟʀᴇᴀᴅʏ ᴏᴘᴇɴᴇᴅ!", show_alert=True)

    game["clicked"].append(pos)

    if pos in game["mine_positions"]:
        # Boom 💥
        del active_games[user_id]
        return await cq.message.edit_text(
            f"💥 **ʙᴏᴏᴍ! ʏᴏᴜ ʜɪᴛ ᴀ ᴍɪɴᴇ.**\n"
            f"❌ ʏᴏᴜ ʟᴏꜱᴛ {game['bet']} ᴄᴏɪɴꜱ."
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
    grid.append([InlineKeyboardButton("💸 ᴄᴀꜱʜ ᴏᴜᴛ", callback_data=f"cashout_{user_id}")])

    await cq.message.edit_text(
        f"🎮 **ᴍɪɴᴇꜱ ɢᴀᴍᴇ**\n\n"
        f"💰 ʙᴇᴛ: {game['bet']} ᴄᴏɪɴꜱ\n"
        f"💣 ʙᴏᴍʙꜱ: {game['bombs']}\n"
        f"📈 ᴍᴜʟᴛɪᴘʟɪᴇʀ: {game['multiplier']}x\n"
        f"💵 ᴘᴏᴛᴇɴᴛɪᴀʟ ᴡɪɴ: {earned} ᴄᴏɪɴꜱ\n\n"
        f"👉 ᴄᴏɴᴛɪɴᴜᴇ ᴏʀ ᴄᴀꜱʜ ᴏᴜᴛ?",
        reply_markup=InlineKeyboardMarkup(grid)
    )


@bot.on_callback_query(filters.regex(r"cashout_(\d+)"))
async def cashout(bot, cq):
    user_id = int(cq.matches[0].group(1))

    if cq.from_user.id != user_id:
        return await cq.answer("⚠ ɴᴏᴛ ʏᴏᴜʀ ɢᴀᴍᴇ!", show_alert=True)

    game = active_games.get(user_id)
    if not game:
        return await cq.answer("⚠ ɴᴏ ᴀᴄᴛɪᴠᴇ ɢᴀᴍᴇ!", show_alert=True)

    earned = math.floor(game["bet"] * game["multiplier"])
    del active_games[user_id]

    # add earned coins back to DB
    await user_collection.update_one({"id": user_id}, {"$inc": {"coins": earned}}, upsert=True)

    await cq.message.edit_text(
        f"✅ **ʏᴏᴜ ᴄᴀꜱʜᴇᴅ ᴏᴜᴛ!**\n\n"
        f"💰 ᴡᴏɴ: {earned} ᴄᴏɪɴꜱ\n"
        f"📈 ᴍᴜʟᴛɪᴘʟɪᴇʀ: {game['multiplier']}x"
)
