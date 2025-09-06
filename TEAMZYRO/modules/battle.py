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

# --- Ensure user exists in DB ---
async def ensure_user(user_id, first_name):
    user = await user_collection.find_one({"user_id": user_id})
    if not user:
        await user_collection.insert_one({
            "user_id": user_id,
            "first_name": first_name,
            "balance": 1000,
            "wins": 0,
            "losses": 0
        })

# --- Battle Command ---
@bot.on_message(filters.command("battle"))
async def battle_cmd(client, message):
    args = message.text.split()
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    # --- Usage check ---
    if len(args) != 3 or not args[2].isdigit():
        return await message.reply(
            "⚔️ 𝗨𝗦𝗔𝗚𝗘:\n`/battle [username] [amount]",
            quote=True
        )

    opponent_username = args[1]
    bet_amount = int(args[2])

    if bet_amount <= 0:
        return await message.reply("❌ 𝗕𝗲𝘁 𝗺𝘂𝘀𝘁 𝗯𝗲 𝗮 𝗽𝗼𝘀𝗶𝘁𝗶𝘃𝗲 𝗶𝗻𝘁𝗲𝗴𝗲𝗿!", quote=True)

    # --- Resolve opponent ---
    try:
        opponent = await client.get_users(opponent_username)
    except Exception:
        return await message.reply("❌ Couldn't find opponent. Try replying to their message or using correct username.", quote=True)

    opponent_id = opponent.id
    opponent_name = opponent.first_name

    if opponent_id == user_id:
        return await message.reply("😂 You can't battle yourself!", quote=True)

    # --- Ensure DB entry exists ---
    await ensure_user(user_id, user_name)
    await ensure_user(opponent_id, opponent_name)

    # --- Fetch real balances ---
    user_data = await user_collection.find_one({"user_id": user_id})
    opponent_data = await user_collection.find_one({"user_id": opponent_id})

    user_balance = user_data.get("balance", 0)
    opponent_balance = opponent_data.get("balance", 0)

    if user_balance < bet_amount:
        return await message.reply("❌ You don't have enough balance!", quote=True)
    if opponent_balance < bet_amount:
        return await message.reply(f"❌ {opponent_name} doesn't have enough balance!", quote=True)

    # --- Prevent multiple battles ---
    if user_id in active_battles or opponent_id in active_battles:
        return await message.reply("⛔ Either you or opponent is already in a battle!", quote=True)

    active_battles[user_id] = True
    active_battles[opponent_id] = True

    # --- Deduct bets temporarily ---
    await user_collection.update_one({"user_id": user_id}, {"$inc": {"balance": -bet_amount}})
    await user_collection.update_one({"user_id": opponent_id}, {"$inc": {"balance": -bet_amount}})

    # --- Battle Animation ---
    hp_user = 100
    hp_opponent = 100
    turn = 0

    battle_msg = await message.reply_photo(
        photo=random.choice(BATTLE_IMAGES),
        caption=f"⚔️ **BATTLE START** ⚔️\n\n{user_name} vs {opponent_name}\nHP: {hp_user} / {hp_opponent}",
        parse_mode="markdown"
    )

    while hp_user > 0 and hp_opponent > 0:
        await asyncio.sleep(1)
        turn += 1

        attacker_is_user = random.choice([True, False])
        move_name, dmg_min, dmg_max = random.choice(ATTACK_MOVES)
        base_damage = random.randint(dmg_min, dmg_max)
        is_crit = random.randint(1, 100) <= CRITICAL_CHANCE
        damage = base_damage * (2 if is_crit else 1)

        if attacker_is_user:
            hp_opponent -= damage
            if hp_opponent < 0: hp_opponent = 0
            attack_text = f"{move_name} — {user_name} dealt {damage} {'(CRIT!)' if is_crit else ''}"
        else:
            hp_user -= damage
            if hp_user < 0: hp_user = 0
            attack_text = f"{move_name} — {opponent_name} dealt {damage} {'(CRIT!)' if is_crit else ''}"

        await battle_msg.edit_caption(
            f"⚔️ **BATTLE TURN {turn}** ⚔️\n\n{attack_text}\n\n"
            f"❤️ {user_name}: {hp_user} {hp_bar(hp_user)}\n"
            f"❤️ {opponent_name}: {hp_opponent} {hp_bar(hp_opponent)}",
            parse_mode="markdown"
        )

    # --- Decide Winner ---
    if hp_user > 0:
        winner_id = user_id
        loser_id = opponent_id
        winner_name = user_name
        loser_name = opponent_name
        victory_media = random.choice(WIN_VIDEOS)
        loser_media = random.choice(LOSE_VIDEOS)
    else:
        winner_id = opponent_id
        loser_id = user_id
        winner_name = opponent_name
        loser_name = user_name
        victory_media = random.choice(WIN_VIDEOS)
        loser_media = random.choice(LOSE_VIDEOS)

    pot = bet_amount * 2
    await user_collection.update_one({"user_id": winner_id}, {"$inc": {"balance": pot, "wins": 1}})
    await user_collection.update_one({"user_id": loser_id}, {"$inc": {"losses": 1}})

    await message.reply_video(victory_media, caption=f"🏆 {winner_name} WINS! 💰 +{pot} coins")
    await message.reply_video(loser_media, caption=f"💀 {loser_name} lost the battle...")

    active_battles.pop(user_id, None)
    active_battles.pop(opponent_id, None)
    
