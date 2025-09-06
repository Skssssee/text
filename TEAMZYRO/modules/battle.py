import random
import asyncio
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from TEAMZYRO import ZYRO as bot, user_collection

# --- Media ---
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

# --- Moves ---
ATTACK_MOVES = [
    ("⚔️ Sword Slash", 10, 25),
    ("🔥 Fireball", 12, 28),
    ("🏹 Arrow Shot", 8, 22),
    ("👊 Heavy Punch", 10, 26),
    ("⚡ Lightning Strike", 11, 30),
]

CRITICAL_CHANCE = 12  # %

# --- Active battles ---
active_battles = {}  # user_id -> battle_id
pending_challenges = {}  # (challenger_id, opponent_id) -> bet

# --- Helpers ---
def hp_bar(hp):
    segments = 10
    filled = int((hp / 100) * segments)
    empty = segments - filled
    return "▰" * filled + "▱" * empty

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

    if len(args) != 3 or not args[2].isdigit():
        return await message.reply(
            "⚔️ **USAGE:**\n`/battle @username <amount>`\n\n✨ **Example:**\n`/battle @friend 500`",
            quote=True
        )

    opponent_username = args[1]
    bet_amount = int(args[2])
    if bet_amount <= 0:
        return await message.reply("❌ Bet must be positive!", quote=True)

    # --- Resolve opponent ---
    try:
        opponent = await client.get_users(opponent_username)
    except Exception:
        return await message.reply("❌ Couldn't find opponent. Use correct username or reply.", quote=True)

    opponent_id = opponent.id
    opponent_name = opponent.first_name
    if opponent_id == user_id:
        return await message.reply("😂 You can't battle yourself!", quote=True)

    # --- Ensure DB ---
    await ensure_user(user_id, user_name)
    await ensure_user(opponent_id, opponent_name)

    # --- Fetch balances ---
    user_data = await user_collection.find_one({"user_id": user_id})
    opponent_data = await user_collection.find_one({"user_id": opponent_id})
    if user_data.get("balance",0) < bet_amount:
        return await message.reply("❌ You don't have enough balance!", quote=True)
    if opponent_data.get("balance",0) < bet_amount:
        return await message.reply(f"❌ {opponent_name} doesn't have enough balance!", quote=True)

    # --- Active battle check ---
    if user_id in active_battles or opponent_id in active_battles:
        return await message.reply("⛔ Either you or opponent is already in a battle!", quote=True)

    # --- Send challenge with buttons ---
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Accept", callback_data=f"battle_accept:{user_id}:{opponent_id}:{bet_amount}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"battle_reject:{user_id}:{opponent_id}")
        ]
    ])

    msg = await message.reply(
        f"⚔️ **{user_name}** has challenged **{opponent_name}** for **{bet_amount} coins**!\n\n"
        f"{opponent_name}, do you accept?",
        quote=True,
        reply_markup=keyboard
    )

    pending_challenges[(user_id, opponent_id)] = {
        "bet": bet_amount,
        "challenger_name": user_name,
        "opponent_name": opponent_name,
        "msg_id": msg.id,
        "chat_id": msg.chat.id
    }

# --- Accept / Reject Callbacks ---
@bot.on_callback_query(filters.regex(r"^battle_accept:(\d+):(\d+):(\d+)$"))
async def accept_battle(client, cq):
    challenger_id = int(cq.matches[0].group(1))
    opponent_id = int(cq.matches[0].group(2))
    bet_amount = int(cq.matches[0].group(3))
    user_id = cq.from_user.id

    if user_id != opponent_id:
        return await cq.answer("Only the challenged user can accept.", show_alert=True)

    key = (challenger_id, opponent_id)
    data = pending_challenges.pop(key, None)
    if not data:
        return await cq.answer("This challenge no longer exists.", show_alert=True)

    # --- Lock users ---
    active_battles[challenger_id] = True
    active_battles[opponent_id] = True

    # Deduct bets
    await user_collection.update_one({"user_id": challenger_id}, {"$inc": {"balance": -bet_amount}})
    await user_collection.update_one({"user_id": opponent_id}, {"$inc": {"balance": -bet_amount}})

    await cq.edit_message_text(f"⚔️ Challenge accepted! Battle starting between **{data['challenger_name']}** and **{data['opponent_name']}**...", parse_mode="markdown")
    asyncio.create_task(run_battle(cq, challenger_id, opponent_id, bet_amount, data['challenger_name'], data['opponent_name']))

@bot.on_callback_query(filters.regex(r"^battle_reject:(\d+):(\d+)$"))
async def reject_battle(client, cq):
    challenger_id = int(cq.matches[0].group(1))
    opponent_id = int(cq.matches[0].group(2))
    user_id = cq.from_user.id

    if user_id != opponent_id:
        return await cq.answer("Only the challenged user can reject.", show_alert=True)

    key = (challenger_id, opponent_id)
    data = pending_challenges.pop(key, None)
    if data:
        await cq.edit_message_text("❌ Challenge rejected.")

# --- Battle Engine ---
async def run_battle(cq, user_id, opponent_id, bet, user_name, opponent_name):
    hp_user = 100
    hp_opponent = 100
    turn = 0

    battle_msg = await cq.message.reply_photo(
        photo=random.choice(BATTLE_IMAGES),
        caption=f"⚔️ **BATTLE START** ⚔️\n\n{user_name} vs {opponent_name}\n\n❤️ {user_name}: {hp_user} {hp_bar(hp_user)}\n❤️ {opponent_name}: {hp_opponent} {hp_bar(hp_opponent)}",
        parse_mode="markdown"
    )

    while hp_user > 0 and hp_opponent > 0:
        await asyncio.sleep(1)
        turn += 1
        attacker_is_user = random.choice([True, False])
        move_name, dmg_min, dmg_max = random.choice(ATTACK_MOVES)
        base_damage = random.randint(dmg_min, dmg_max)
        is_crit = random.randint(1,100) <= CRITICAL_CHANCE
        damage = base_damage * (2 if is_crit else 1)

        if attacker_is_user:
            hp_opponent = max(hp_opponent - damage, 0)
            attack_text = f"{move_name} — {user_name} dealt {damage} {'(CRIT!)' if is_crit else ''}"
        else:
            hp_user = max(hp_user - damage, 0)
            attack_text = f"{move_name} — {opponent_name} dealt {damage} {'(CRIT!)' if is_crit else ''}"

        await battle_msg.edit_caption(
            f"⚔️ **TURN {turn}** ⚔️\n{attack_text}\n\n"
            f"❤️ {user_name}: {hp_user} {hp_bar(hp_user)}\n❤️ {opponent_name}: {hp_opponent} {hp_bar(hp_opponent)}",
            parse_mode="markdown"
        )

    # Decide winner
    if hp_user > 0:
        winner_id, loser_id = user_id, opponent_id
        winner_name, loser_name = user_name, opponent_name
    else:
        winner_id, loser_id = opponent_id, user_id
        winner_name, loser_name = opponent_name, user_name

    pot = bet*2
    await user_collection.update_one({"user_id": winner_id}, {"$inc": {"balance": pot, "wins": 1}})
    await user_collection.update_one({"user_id": loser_id}, {"$inc": {"losses": 1}})

    await cq.message.reply_video(random.choice(WIN_VIDEOS), caption=f"🏆 {winner_name} WINS! 💰 +{pot} coins")
    await cq.message.reply_video(random.choice(LOSE_VIDEOS), caption=f"💀 {loser_name} lost the battle...")

    # Unlock
    active_battles.pop(user_id, None)
    active_battles.pop(opponent_id, None)
    
