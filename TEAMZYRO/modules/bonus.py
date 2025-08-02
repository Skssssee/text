import asyncio
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from datetime import datetime, timedelta
from TEAMZYRO import ZYRO as bot
from TEAMZYRO import user_collection

# Bonus values
DAILY_REWARD = 100
WEEKLY_REWARD = 500

# Get user data from MongoDB
def get_user_data(user_id: int):
    return user_collection.find_one({"user_id": user_id}) or {}

# Update last bonus claim time
def update_bonus_time(user_id: int, bonus_type: str):
    now = datetime.utcnow()
    user_collection.update_one(
        {"user_id": user_id},
        {"$set": {f"last_{bonus_type}": now}},
        upsert=True
    )

# Add coins to user's balance
def update_user_coins(user_id: int, coins: int):
    user_collection.update_one(
        {"user_id": user_id},
        {"$inc": {"coins": coins}},
        upsert=True
    )

# Check if bonus can be claimed
def can_claim_bonus(user_id: int, bonus_type: str, cooldown_hours: int):
    user = get_user_data(user_id)
    last_time = user.get(f"last_{bonus_type}")
    if not last_time:
        return True
    elapsed = (datetime.utcnow() - last_time).total_seconds() / 3600
    return elapsed >= cooldown_hours

# /bonus command
@bot.on_message(filters.command("bonus"))
async def bonus_command(_, message: Message):
    btns = InlineKeyboardMarkup([[
        InlineKeyboardButton("🌞 Daily Bonus", callback_data="daily_bonus"),
        InlineKeyboardButton("📅 Weekly Bonus", callback_data="weekly_bonus"),
        InlineKeyboardButton("❌ Close", callback_data="bonus_close")
    ]])
    await message.reply("🎁 **Choose your bonus:**", reply_markup=btns)

# Callback handling
@bot.on_callback_query(filters.regex("^(daily_bonus|weekly_bonus|bonus_close)$"))
async def bonus_callback(_, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data

    if data == "bonus_close":
        await query.message.delete()
        return

    bonus_type = "daily" if data == "daily_bonus" else "weekly"
    reward = DAILY_REWARD if bonus_type == "daily" else WEEKLY_REWARD
    cooldown = 24 if bonus_type == "daily" else 24 * 7

    if can_claim_bonus(user_id, bonus_type, cooldown):
        update_bonus_time(user_id, bonus_type)
        update_user_coins(user_id, reward)
        await query.answer(f"✅ You received {reward} waifu coins!", show_alert=True)
    else:
        await query.answer("⛔ Already claimed! Try again later.", show_alert=True)
