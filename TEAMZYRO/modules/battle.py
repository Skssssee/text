import random
import asyncio
from bson import ObjectId
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from TEAMZYRO import app, user_collection

# ----- Config -----
# Victory videos (use your provided links)
victory_videos = [
    "https://files.catbox.moe/5cezg5.mp4",
    "https://files.catbox.moe/dw2df7.mp4",
    "https://files.catbox.moe/5vgulb.mp4",
    "https://files.catbox.moe/ucdvpd.mp4",
    "https://files.catbox.moe/bhwnu4.mp4",
]

# Attack animations / names (for flavor)
ATTACK_MOVES = [
    ("⚔️ Sword Slash", 10, 25),
    ("🔥 Fireball", 12, 28),
    ("🏹 Arrow Shot", 8, 22),
    ("👊 Heavy Punch", 10, 26),
    ("⚡ Lightning Strike", 11, 30),
]

# Critical hit chance (percentage)
CRITICAL_CHANCE = 12  # 12% chance for critical (x2 damage)

# Active structures
pending_challenges = {}   # key: (challenger_id, opponent_id) -> challenge data
active_battles = {}       # opponent_id or challenger_id -> battle lock (to prevent duplicates)


# ----- Helper functions -----
async def get_user_balance(user_id):
    u = await user_collection.find_one({"id": user_id}, {"balance": 1})
    return u.get("balance", 0) if u else 0

async def ensure_user_exists(user_id, first_name=None):
    user = await user_collection.find_one({"id": user_id})
    if not user:
        await user_collection.insert_one({
            "id": user_id,
            "first_name": first_name or "Player",
            "balance": 0,
            "wins": 0,
            "losses": 0
        })

def short_name(user):
    return (user[:20] + "...") if user and len(user) > 23 else (user or "Player")


# ----- Command: /battle @username <bet> -----
@app.on_message(filters.command("battle"))
async def battle_command(client, message):
    # Usage: /battle @username 500
    if len(message.command) < 3:
        return await message.reply_text("Usage: /battle @username <bet>\nExample: /battle @friend 500")

    # parse target and bet
    target = message.command[1]
    try:
        bet = int(message.command[2])
        if bet <= 0:
            raise ValueError
    except ValueError:
        return await message.reply_text("❌ Bet must be a positive integer.")

    # resolve target user id
    target_id = None
    target_name = None
    if message.reply_to_message:
        # prefer reply target
        target_id = message.reply_to_message.from_user.id
        target_name = message.reply_to_message.from_user.first_name
    else:
        # try username or numeric id
        if target.startswith("@"):
            try:
                # try get_chat to resolve username
                member = await client.get_users(target)
                target_id = member.id
                target_name = member.first_name
            except Exception:
                return await message.reply_text("❌ Couldn't find that username. Try replying to their message instead.")
        else:
            try:
                target_id = int(target)
            except Exception:
                return await message.reply_text("❌ Provide a valid username (@name) or reply to the user's message.")

    challenger_id = message.from_user.id
    challenger_name = message.from_user.first_name

    if target_id == challenger_id:
        return await message.reply_text("You cannot battle yourself!")

    # Prevent multiple pending/active for same users
    if (challenger_id, target_id) in pending_challenges:
        return await message.reply_text("❌ You already have a pending challenge to this user.")
    if challenger_id in active_battles or target_id in active_battles:
        return await message.reply_text("❌ Either you or the opponent is already in another active battle.")

    # Ensure users exist in DB
    await ensure_user_exists(challenger_id, challenger_name)
    await ensure_user_exists(target_id, target_name)

    # Check challenger's balance
    challenger_balance = await get_user_balance(challenger_id)
    if challenger_balance < bet:
        return await message.reply_text("🚫 You don't have enough balance to place this bet.")

    # Prepare challenge message with Accept/Reject buttons
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Accept", callback_data=f"battle_accept:{challenger_id}:{target_id}:{bet}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"battle_reject:{challenger_id}:{target_id}")],
        ]
    )

    challenge_msg = await message.reply_text(
        f"⚔️ <b>{short_name(challenger_name)}</b> has challenged <b>{short_name(target_name)}</b> for <b>{bet} coins</b>!\n\n"
        f"{short_name(target_name)}, do you accept?",
        parse_mode="html",
        reply_markup=keyboard
    )

    # store pending
    pending_challenges[(challenger_id, target_id)] = {
        "challenger": challenger_id,
        "challenger_name": challenger_name,
        "opponent": target_id,
        "opponent_name": target_name,
        "bet": bet,
        "message_id": challenge_msg.id,
        "chat_id": challenge_msg.chat.id
    }


# ----- Callback: Accept / Reject -----
@app.on_callback_query(filters.regex(r"^battle_accept:(\d+):(\d+):(\d+)$"))
async def handle_accept(client, cq):
    challenger_id = int(cq.matches[0].group(1))
    opponent_id = int(cq.matches[0].group(2))
    bet = int(cq.matches[0].group(3))
    user_id = cq.from_user.id

    # Only the invited opponent can accept
    if user_id != opponent_id:
        return await cq.answer("Only the challenged user can accept this.", show_alert=True)

    key = (challenger_id, opponent_id)
    if key not in pending_challenges:
        return await cq.answer("This challenge is no longer valid.", show_alert=True)

    # Check both balances now
    challenger_balance = await get_user_balance(challenger_id)
    opponent_balance = await get_user_balance(opponent_id)
    if challenger_balance < bet:
        del pending_challenges[key]
        return await cq.edit_message_text("❌ Challenger no longer has enough balance. Challenge cancelled.")
    if opponent_balance < bet:
        del pending_challenges[key]
        return await cq.edit_message_text("❌ You don't have enough balance to accept the challenge. Challenge cancelled.")

    # Lock both users to prevent other battles
    active_battles[challenger_id] = True
    active_battles[opponent_id] = True

    # Deduct bets immediately from both
    await user_collection.update_one({"id": challenger_id}, {"$inc": {"balance": -bet}})
    await user_collection.update_one({"id": opponent_id}, {"$inc": {"balance": -bet}})

    # Start the fight in the same message (edit)
    await cq.edit_message_text("⚔️ Battle accepted! Preparing arena...")

    # Run the battle engine
    asyncio.create_task(run_battle(cq, key))


@app.on_callback_query(filters.regex(r"^battle_reject:(\d+):(\d+)$"))
async def handle_reject(client, cq):
    challenger_id = int(cq.matches[0].group(1))
    opponent_id = int(cq.matches[0].group(2))
    user_id = cq.from_user.id

    if user_id != opponent_id:
        return await cq.answer("Only the challenged user can reject this.", show_alert=True)

    key = (challenger_id, opponent_id)
    if key in pending_challenges:
        del pending_challenges[key]

    await cq.edit_message_text("❌ Challenge rejected.")


# ----- Battle engine -----
async def run_battle(callback_query, key):
    try:
        data = pending_challenges.pop(key, None)
        if not data:
            await callback_query.edit_message_text("❌ Challenge data missing. Aborting.")
            active_battles.pop(key[0], None)
            active_battles.pop(key[1], None)
            return

        challenger_id = data["challenger"]
        opponent_id = data["opponent"]
        bet = data["bet"]

        # Initial HP
        hp_chall = 100
        hp_opp = 100

        # nicknames
        challenger_name = data.get("challenger_name") or "Challenger"
        opponent_name = data.get("opponent_name") or "Opponent"

        # pot info (we already deducted both bets)
        pot = bet * 2

        # initial message
        msg = await callback_query.message.reply_text(
            f"⚔️ **Battle Start!** ⚔️\n\n"
            f"{challenger_name} ⚔ {opponent_name}\n"
            f"💰 Bet: {bet} coins each (Pot: {pot})\n\n"
            f"❤️ {challenger_name}: {hp_chall} HP\n"
            f"❤️ {opponent_name}: {hp_opp} HP\n\n"
            f"Let the battle begin!",
            parse_mode="markdown"
        )

        turn = 0
        # Battle loop
        while hp_chall > 0 and hp_opp > 0:
            await asyncio.sleep(1.0)  # small delay for animation feel
            turn += 1

            # choose attacker randomly (true -> challenger attacks)
            attacker_is_chall = random.choice([True, False])

            # choose move and damage range
            move_name, dmg_min, dmg_max = random.choice(ATTACK_MOVES)
            base_damage = random.randint(dmg_min, dmg_max)

            is_crit = random.randint(1, 100) <= CRITICAL_CHANCE
            damage = base_damage * (2 if is_crit else 1)

            if attacker_is_chall:
                hp_opp -= damage
                if hp_opp < 0:
                    hp_opp = 0
                attack_line = f"{move_name} — {challenger_name} dealt *{damage}* damage {'(CRIT!)' if is_crit else ''}"
            else:
                hp_chall -= damage
                if hp_chall < 0:
                    hp_chall = 0
                attack_line = f"{move_name} — {opponent_name} dealt *{damage}* damage {'(CRIT!)' if is_crit else ''}"

            # update message with animated status
            bar_chall = hp_bar(hp_chall)
            bar_opp = hp_bar(hp_opp)
            await msg.edit_text(
                f"⚔️ **Battle Arena** ⚔️\n\n"
                f"{attack_line}\n\n"
                f"💠 Turn: {turn}\n\n"
                f"❤️ {challenger_name}: {hp_chall} HP {bar_chall}\n"
                f"❤️ {opponent_name}: {hp_opp} HP {bar_opp}\n\n"
                f"Pot: {pot} coins",
                parse_mode="markdown"
            )

        # Decide winner
        if hp_chall > 0 and hp_opp == 0:
            winner_id = challenger_id
            winner_name = challenger_name
            loser_id = opponent_id
            loser_name = opponent_name
        elif hp_opp > 0 and hp_chall == 0:
            winner_id = opponent_id
            winner_name = opponent_name
            loser_id = challenger_id
            loser_name = challenger_name
        else:
            # draw -> return half pot to both (rare)
            await msg.edit_text("🤝 It's a draw! Bets are returned.")
            await user_collection.update_one({"id": challenger_id}, {"$inc": {"balance": bet}}, upsert=True)
            await user_collection.update_one({"id": opponent_id}, {"$inc": {"balance": bet}}, upsert=True)
            active_battles.pop(challenger_id, None)
            active_battles.pop(opponent_id, None)
            return

        # Award pot to winner
        await user_collection.update_one({"id": winner_id}, {"$inc": {"balance": pot, "wins": 1}}, upsert=True)
        await user_collection.update_one({"id": loser_id}, {"$inc": {"losses": 1}}, upsert=True)

        # Send victory video and final message
        victory_video = random.choice(VICTORY_VIDEOS)
        await msg.reply_video(victory_video, caption=f"🏆 {winner_name} wins the battle and takes {pot} coins! 🎉", has_spoiler=True)
        await msg.edit_text(f"🏁 Battle finished!\n\n🏆 Winner: {winner_name}\n💰 Winnings: {pot} coins")

    except Exception as e:
        print("Error in run_battle:", e)
        try:
            await callback_query.edit_message_text("⚠ Battle aborted due to an error.")
        except Exception:
            pass
    finally:
        # unlock players
        active_battles.pop(key[0], None)
        active_battles.pop(key[1], None)


# ----- Small helper for HP bar visuals -----
def hp_bar(hp):
    # display a small bar of 10 segments
    segments = 10
    filled = int((hp / 100) * segments)
    empty = segments - filled
    return "▰" * filled + "▱" * empty


# End of Battle Arena code
