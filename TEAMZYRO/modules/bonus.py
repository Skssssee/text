import asyncio
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from datetime import datetime, timedelta
from TEAMZYRO import ZYRO as bot
from TEAMZYRO import user_collection

BONUS_AMOUNT = {
    "daily": 100,
    "weekly": 500
}

async def check_and_update(user_id, bonus_type):
    field = f"{bonus_type}_bonus_time"
    user = user_collection.find_one({"user_id": user_id}) or {}
    now = datetime.utcnow()

    if field in user:
        last_claim = user[field]
        cooldown = timedelta(days=1 if bonus_type == "daily" else 7)
        if now - last_claim < cooldown:
            remaining = cooldown - (now - last_claim)
            return False, f"You already claimed {bonus_type} bonus.\nCome back after: {remaining}"

    user_collection.update_one(
        {"user_id": user_id},
        {
            "$set": {field: now},
            "$inc": {"coins": BONUS_AMOUNT[bonus_type]}
        },
        upsert=True
    )
    return True, f"🎉 You received {BONUS_AMOUNT[bonus_type]} coins as {bonus_type} bonus!"

@bot.on_message(filters.command("bonus"))
async def show_bonus_buttons(bot, message: Message):
    btn = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎁 Daily Bonus", callback_data="claim_daily"),
            InlineKeyboardButton("💰 Weekly Bonus", callback_data="claim_weekly")
        ],
        [InlineKeyboardButton("❌ Close", callback_data="bonus_close")]
    ])
    await message.reply("🎉 Choose your bonus below:", reply_markup=btn)

@bot.on_callback_query(filters.regex(r"claim_(daily|weekly)"))
async def claim_bonus(bot, query: CallbackQuery):
    bonus_type = query.data.split("_")[1]
    user_id = query.from_user.id

    success, msg = await check_and_update(user_id, bonus_type)
    await query.answer(msg, show_alert=True)

@bot.on_callback_query(filters.regex("bonus_close"))
async def close_bonus(bot, query: CallbackQuery):
    await query.message.delete()
