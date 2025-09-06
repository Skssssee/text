import random
import asyncio
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from TEAMZYRO import ZYRO as bot, user_collection  # Mongo collection imported correctly

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
    user = await user_collection.find_one({"id": user_id})
    if not user:
        await user_collection.insert_one({
            "id": user_id,
            "first_name": first_name,
            "balance": 1000,  # starting coins
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
            "⚔️ 𝗨𝗦𝗔𝗚𝗘:\n`/battle @username <amount>`\n\n✨ 𝗘𝘅𝗮𝗺𝗽𝗹𝗲:\n`/battle @friend 500`",
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
        return await message.reply("❌ Couldn't find opponent. Try replying to their message or using correct username.", quote=True)

    opponent_id = opponent.id
    opponent_name = opponent.first_name

    if opponent_id == user_id:
        return await message.reply("😂 You can't battle yourself!", quote=True)

    # --- Ensure DB entry exists ---
    await ensure_user(user_id, user_name)
    await ensure_user(opponent_id, opponent_name)

    # --- Fetch real balances from MongoDB ---
    user_data = await user_collection.find_one({"id": user_id})
    opponent_data = await user_collection.find_one({"id": opponent_id})

    user_balance = user_data.get("balance", 0)
    opponent_balance = opponent_data.get("balance", 0)

    if user_balance < bet_amount:
        return await message.reply("❌ You don't have enough balance!", quote=True)
    if opponent_balance < bet_amount:
        return await message.reply(f"❌ {opponent_name} doesn't have enough balance!", quote=True)

    # --- Prevent multiple battles ---
    if user_id in active_battles or opponent_id in active_battles:
        return await message.reply("⛔ Either you or opponent is already in a battle!", quote=True)

    # --- Send challenge with Accept/Reject buttons ---
    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Accept", callback_data=f"battle_accept:{user_id}:{opponent_id}:{bet_amount}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"battle_reject:{user_id}:{opponent_id}")
        ]]
    )

    challenge_msg = await message.reply_text(
        f"⚔️ <b>{user_name}</b> has challenged <b>{opponent_name}</b> for <b>{bet_amount} coins</b>!\n\n"
        f"{opponent_name}, do you accept?",
        parse_mode="html",
        reply_markup=keyboard
    )

# --- Callback Accept ---
@bot.on_callback_query(filters.regex(r"^battle_accept:(\d+):(\d+):(\d+)$"))
async def battle_accept(client, cq):
    challenger_id = int(cq.matches[0].group(1))
    opponent_id = int(cq.matches[0].group(2))
    bet_amount = int(cq.matches[0].group(3))
    user_id = cq.from_user.id

    if user_id != opponent_id:
        return await cq.answer("Only the challenged user can accept!", show_alert=True)

    # --- Lock players ---
    active_battles[challenger_id] = True
    active_battles[opponent_id] = True

    # --- Deduct bets ---
    await user_collection.update_one({"id": challenger_id}, {"$inc": {"balance": -bet_amount}})
    await user_collection.update_one({"id": opponent_id}, {"$inc": {"balance": -bet_amount}})

    # --- Start battle animation ---
    challenger_data = await user_collection.find_one({"id": challenger_id})
    opponent_data = await user_collection.find_one({"id": opponent_id})

    hp_chall = 100
    hp_opp = 100
    turn = 0

    msg = await cq.message.reply_photo(
        photo=random.choice(BATTLE_IMAGES),
        caption=f"⚔️ Battle Start!\n\n{challenger_data['first_name']} vs {opponent_data['first_name']}\n💰 Pot: {bet_amount*2} coins\n❤️ HP: 100/100",
        parse_mode="html"
    )

    while hp_chall > 0 and hp_opp > 0:
        await asyncio.sleep(1)
        turn += 1
        attacker_is_chall = random.choice([True, False])
        move_name, dmg_min, dmg_max = random.choice(ATTACK_MOVES)
        base_damage = random.randint(dmg_min, dmg_max)
        is_crit = random.randint(1, 100) <= CRITICAL_CHANCE
        damage = base_damage * (2 if is_crit else 1)

        if attacker_is_chall:
            hp_opp -= damage
            if hp_opp < 0: hp_opp = 0
            attack_text = f"{move_name} — {challenger_data['first_name']} dealt {damage} {'(CRIT!)' if is_crit else ''}"
        else:
            hp_chall -= damage
            if hp_chall < 0: hp_chall = 0
            attack_text = f"{move_name} — {opponent_data['first_name']} dealt {damage} {'(CRIT!)' if is_crit else ''}"

        await msg.edit_caption(
            f"⚔️ Turn {turn}\n{attack_text}\n\n"
            f"❤️ {challenger_data['first_name']}: {hp_chall} {hp_bar(hp_chall)}\n"
            f"❤️ {opponent_data['first_name']}: {hp_opp} {hp_bar(hp_opp)}",
            parse_mode="html"
        )

    # --- Decide Winner ---
    if hp_chall > 0:
        winner_id = challenger_id
        loser_id = opponent_id
        winner_name = challenger_data['first_name']
        loser_name = opponent_data['first_name']
    else:
        winner_id = opponent_id
        loser_id = challenger_id
        winner_name = opponent_data['first_name']
        loser_name = challenger_data['first_name']

    pot = bet_amount * 2
    await user_collection.update_one({"id": winner_id}, {"$inc": {"balance": pot, "wins": 1}})
    await user_collection.update_one({"id": loser_id}, {"$inc": {"losses": 1}})

    await cq.message.reply_video(random.choice(WIN_VIDEOS), caption=f"🏆 {winner_name} WINS! 💰 +{pot} coins")
    await cq.message.reply_video(random.choice(LOSE_VIDEOS), caption=f"💀 {loser_name} lost...")

    # --- Unlock players ---
    active_battles.pop(challenger_id, None)
    active_battles.pop(opponent_id, None)

# --- Callback Reject ---
@bot.on_callback_query(filters.regex(r"^battle_reject:(\d+):(\d+)$"))
async def battle_reject(client, cq):
    challenger_id = int(cq.matches[0].group(1))
    opponent_id = int(cq.matches[0].group(2))
    if cq.from_user.id != opponent_id:
        return await cq.answer("Only the challenged user can reject!", show_alert=True)
    await cq.message.edit_text("❌ Challenge Rejected.")
