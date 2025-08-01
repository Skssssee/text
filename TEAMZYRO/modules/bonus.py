from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from datetime import datetime, timedelta
from TEAMZYRO import ZYRO as bot
from TEAMZYRO import user_collection

DAILY_REWARD = 100
WEEKLY_REWARD = 500

def get_user_data(user_id: int):
    return user_collection.find_one({"user_id": user_id}) or {}

def update_bonus_time(user_id: int, bonus_type: str):
    now = datetime.utcnow().isoformat()
    user_collection.update_one(
        {"user_id": user_id},
        {"$set": {f"last_{bonus_type}": now}},
        upsert=True
    )

def update_user_coins(user_id: int, coins: int):
    user_collection.update_one(
        {"user_id": user_id},
        {"$inc": {"coins": coins}},
        upsert=True
    )

def can_claim_bonus(user_id: int, bonus_type: str, cooldown_hours: int):
    user = get_user_data(user_id)
    last_time = user.get(f"last_{bonus_type}")

    if not last_time:
        return True

    try:
        last_dt = datetime.fromisoformat(last_time)
    except Exception:
        return True  # if somehow invalid format

    elapsed = (datetime.utcnow() - last_dt).total_seconds() / 3600
    return elapsed >= cooldown_hours

@bot.on_message(filters.command("bonus"))
async def bonus_command(_, message: Message):
    btns = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌞 Daily Bonus", callback_data="daily_bonus"),
            InlineKeyboardButton("📅 Weekly Bonus", callback_data="weekly_bonus"),
            InlineKeyboardButton("❌ Close", callback_data="bonus_close")
        ]
    ])
    await message.reply("🎁 Choose your bonus:", reply_markup=btns)

@bot.on_callback_query(filters.regex("^(daily_bonus|weekly_bonus|bonus_close)$"))
async def bonus_callback(_, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data

    if data == "bonus_close":
        await query.message.delete()
        return

    if data == "daily_bonus":
        bonus_type = "daily"
        reward = DAILY_REWARD
        cooldown = 24
    else:
        bonus_type = "weekly"
        reward = WEEKLY_REWARD
        cooldown = 24 * 7

    if can_claim_bonus(user_id, bonus_type, cooldown):
        update_bonus_time(user_id, bonus_type)
        update_user_coins(user_id, reward)
        await query.answer(f"✅ You received {reward} waifu coins!", show_alert=True)
    else:
        await query.answer("⛔ Already claimed! Try again later.", show_alert=True)
