import asyncio
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from datetime import datetime, timedelta
from TEAMZYRO import ZYRO as bot
from TEAMZYRO import user_collection
from pymongo import ReturnDocument

DAILY_REWARD = 100
WEEKLY_REWARD = 500

def ensure_user(user_id: int):
    user = user_collection.find_one({"user_id": user_id})
    if not user:
        user_collection.insert_one({"user_id": user_id, "coins": 0})
    return user_collection.find_one({"user_id": user_id})

def update_bonus_time(user_id: int, bonus_type: str):
    user_collection.update_one(
        {"user_id": user_id},
        {"$set": {f"last_{bonus_type}": datetime.utcnow()}},
        upsert=True
    )

def update_user_coins(user_id: int, coins: int):
    return user_collection.find_one_and_update(
        {"user_id": user_id},
        {"$inc": {"coins": coins}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )

def can_claim_bonus(user_id: int, bonus_type: str, cooldown_hours: int):
    user = ensure_user(user_id)
    last_time = user.get(f"last_{bonus_type}")
    if not last_time:
        return True
    if isinstance(last_time, str):
        try:
            last_time = datetime.fromisoformat(last_time)
        except:
            return True
    elapsed = (datetime.utcnow() - last_time).total_seconds() / 3600
    return elapsed >= cooldown_hours

def get_next_claim_time(user_id: int, bonus_type: str, cooldown_hours: int):
    user = ensure_user(user_id)
    last_time = user.get(f"last_{bonus_type}")
    if not last_time:
        return None
    if isinstance(last_time, str):
        try:
            last_time = datetime.fromisoformat(last_time)
        except:
            return None
    return last_time + timedelta(hours=cooldown_hours)

@bot.on_message(filters.command("bonus"))
async def bonus_command(_, message: Message):
    btns = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌞 Daily Bonus", callback_data="daily_bonus"),
         InlineKeyboardButton("📅 Weekly Bonus", callback_data="weekly_bonus")],
        [InlineKeyboardButton("❌ Close", callback_data="bonus_close")]
    ])
    await message.reply("🎁 Choose your bonus:", reply_markup=btns)

@bot.on_callback_query(filters.regex("daily_bonus|weekly_bonus|bonus_close"))
async def bonus_callback(_, query: CallbackQuery):
    await query.answer()  # ✅ First response to avoid button freeze

    user_id = query.from_user.id
    ensure_user(user_id)

    if query.data == "bonus_close":
        await query.message.delete()
        return

    bonus_type = "daily" if query.data == "daily_bonus" else "weekly"
    reward = DAILY_REWARD if bonus_type == "daily" else WEEKLY_REWARD
    cooldown = 24 if bonus_type == "daily" else 24 * 7

    if can_claim_bonus(user_id, bonus_type, cooldown):
        update_bonus_time(user_id, bonus_type)
        updated_user = update_user_coins(user_id, reward)
        new_balance = updated_user.get("coins", 0)
        next_time = datetime.utcnow() + timedelta(hours=cooldown)
        next_time_str = next_time.strftime("%d %b %Y, %I:%M %p")

        await query.message.edit_text(
            f"🎉 {bonus_type.title()} Bonus Claimed!\n\n"
            f"💰 +{reward} coins added!\n"
            f"📦 Balance: {new_balance} coins\n\n"
            f"⏳ Next Claim: {next_time_str}"
        )
    else:
        next_time = get_next_claim_time(user_id, bonus_type, cooldown)
        if next_time:
            remaining = next_time - datetime.utcnow()
            h, rem = divmod(int(remaining.total_seconds()), 3600)
            m = rem // 60
            await query.message.edit_text(
                f"⛔ {bonus_type.title()} Bonus Already Claimed!\n\n"
                f"⏳ Next Claim in: {h}h {m}m"
                  )                f"⏳ Next Claim in: {hours}h {minutes}m"
            )
