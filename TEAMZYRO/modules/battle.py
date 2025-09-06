import random
import asyncio
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from TEAMZYRO import ZYRO as bot, user_collection

# --- Battle media ---
BATTLE_IMAGES = [
    "https://files.catbox.moe/1f6a2q.jpg",
    "https://files.catbox.moe/0o7nkl.jpg",
    "https://files.catbox.moe/3gljwk.jpg",
    "https://files.catbox.moe/5dtj1p.jpg"
]

WIN_VIDEOS = [
    "https://files.catbox.moe/5cezg5.mp4",
    "https://files.catbox.moe/dw2df7.mp4",
    "https://files.catbox.moe/5vgulb.mp4"
]

LOSE_VIDEOS = [
    "https://files.catbox.moe/ucdvpd.mp4",
    "https://files.catbox.moe/bhwnu4.mp4"
]

# --- Attack moves ---
ATTACK_MOVES = [
    ("⚔️ Sword Slash", 10, 25),
    ("🔥 Fireball", 12, 28),
    ("🏹 Arrow Shot", 8, 22),
    ("👊 Heavy Punch", 10, 26),
    ("⚡ Lightning Strike", 11, 30),
]

CRITICAL_CHANCE = 12  # % chance for double damage

# --- Active battles ---
active_battles = {}

# --- Helper HP bar ---
def hp_bar(hp):
    segments = 10
    filled = int((hp / 100) * segments)
    empty = segments - filled
    return "▰" * filled + "▱" * empty

# --- Battle Command ---
@bot.on_message(filters.command("battle"))
async def battle_cmd(client, message):
    args = message.text.split()
    user_id = message.from_user.id

    # --- Usage check ---
    if len(args) != 3 or not args[2].isdigit():
        return await message.reply(
            "⚔️ 𝗨𝗦𝗔𝗚𝗘:\n`/battle [username] <amount>`\n\n✨ 𝗘𝘅𝗮𝗺𝗽𝗹𝗲:\n`/battle [username] 500`",
            quote=True
        )

    opponent_username = args[1]
    bet_amount = int(args[2])

    if bet_amount <= 0:
        return await message.reply("❌ 𝗕𝗲𝘁 𝗮𝗺𝗼𝘂𝗻𝘁 𝗺𝘂𝘀𝘁 𝗯𝗲 𝗽𝗼𝘀𝗶𝘁𝗶𝘃𝗲!", quote=True)

    # --- Opponent check ---
    if not message.entities or len(message.entities) < 2:
        return await message.reply("❌ 𝗠𝘂𝘀𝘁 𝗺𝗲𝗻𝘁𝗶𝗼𝗻 𝗮 𝗼𝗽𝗽𝗼𝗻𝗲𝗻𝘁!", quote=True)

    opponent_id = message.entities[1].user.id if message.entities[1].user else None
    if opponent_id == user_id:
        return await message.reply("😂 𝗬𝗼𝘂 𝗰𝗮𝗻'𝘁 𝗯𝗮𝘁𝘁𝗹𝗲 𝘆𝗼𝘂𝗿𝘀𝗲𝗹𝗳!", quote=True)

    # --- Prevent multiple battles ---
    if user_id in active_battles or opponent_id in active_battles:
        return await message.reply("⛔ Either you or opponent already in a battle!", quote=True)

    active_battles[user_id] = True
    active_battles[opponent_id] = True

    # --- Ensure balances ---
    user = await user_collection.find_one({"user_id": user_id}) or {"user_id": user_id, "balance": 1000}
    opponent = await user_collection.find_one({"user_id": opponent_id}) or {"user_id": opponent_id, "balance": 1000}

    if user["balance"] < bet_amount:
        active_battles.pop(user_id, None)
        active_battles.pop(opponent_id, None)
        return await message.reply("❌ You don't have enough balance!", quote=True)
    if opponent["balance"] < bet_amount:
        active_battles.pop(user_id, None)
        active_battles.pop(opponent_id, None)
        return await message.reply("❌ Opponent doesn't have enough balance!", quote=True)

    # Deduct bets temporarily
    await user_collection.update_one({"user_id": user_id}, {"$inc": {"balance": -bet_amount}}, upsert=True)
    await user_collection.update_one({"user_id": opponent_id}, {"$inc": {"balance": -bet_amount}}, upsert=True)

    # --- Battle Animation ---
    hp_user = 100
    hp_opponent = 100
    turn = 0

    battle_msg = await message.reply_photo(
        photo=random.choice(BATTLE_IMAGES),
        caption=f"⚔️ **BATTLE START** ⚔️\n\n{message.from_user.first_name} vs {opponent_username}\nHP: {hp_user} / {hp_opponent}",
        parse_mode="markdown"
    )

    while hp_user > 0 and hp_opponent > 0:
        await asyncio.sleep(1)  # delay for animation effect
        turn += 1

        attacker_is_user = random.choice([True, False])
        move_name, dmg_min, dmg_max = random.choice(ATTACK_MOVES)
        base_damage = random.randint(dmg_min, dmg_max)
        is_crit = random.randint(1, 100) <= CRITICAL_CHANCE
        damage = base_damage * (2 if is_crit else 1)

        if attacker_is_user:
            hp_opponent -= damage
            if hp_opponent < 0: hp_opponent = 0
            attack_text = f"{move_name} — {message.from_user.first_name} dealt {damage} {'(CRIT!)' if is_crit else ''}"
        else:
            hp_user -= damage
            if hp_user < 0: hp_user = 0
            attack_text = f"{move_name} — {opponent_username} dealt {damage} {'(CRIT!)' if is_crit else ''}"

        await battle_msg.edit_caption(
            f"⚔️ **BATTLE TURN {turn}** ⚔️\n\n{attack_text}\n\n"
            f"❤️ {message.from_user.first_name}: {hp_user} {hp_bar(hp_user)}\n"
            f"❤️ {opponent_username}: {hp_opponent} {hp_bar(hp_opponent)}",
            parse_mode="markdown"
        )

    # --- Decide Winner ---
    if hp_user > 0:
        winner_id = user_id
        loser_id = opponent_id
        winner_name = message.from_user.first_name
        loser_name = opponent_username
        victory_media = random.choice(WIN_VIDEOS)
        loser_media = random.choice(LOSE_VIDEOS)
    else:
        winner_id = opponent_id
        loser_id = user_id
        winner_name = opponent_username
        loser_name = message.from_user.first_name
        victory_media = random.choice(WIN_VIDEOS)
        loser_media = random.choice(LOSE_VIDEOS)

    # Add pot to winner
    pot = bet_amount * 2
    await user_collection.update_one({"user_id": winner_id}, {"$inc": {"balance": pot}}, upsert=True)

    # Send final result
    await message.reply_video(victory_media, caption=f"🏆 {winner_name} WINS the battle! 💰 +{pot} coins")
    await message.reply_video(loser_media, caption=f"💀 {loser_name} lost the battle...")

    # Unlock players
    active_battles.pop(user_id, None)
    active_battles.pop(opponent_id, None)
    
