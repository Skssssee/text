import asyncio
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from datetime import datetime, timedelta
from TEAMZYRO import ZYRO as app
from TEAMZYRO import user_collection

def get_user(user_id):
    return user_collection.find_one({"user_id": user_id}) or {}

def update_user(user_id, update):
    user_collection.update_one({"user_id": user_id}, {"$set": update}, upsert=True)

@app.on_message(filters.command("bonus"))
async def bonus_menu(_, message: Message):
    btn = [
        [
            InlineKeyboardButton("💰 Daily Bonus", callback_data="daily_bonus"),
            InlineKeyboardButton("💎 Weekly Bonus", callback_data="weekly_bonus")
        ],
        [InlineKeyboardButton("❌ Close", callback_data="close_bonus")]
    ]
    await message.reply("Choose your bonus:", reply_markup=InlineKeyboardMarkup(btn))

@app.on_callback_query(filters.regex("^(daily_bonus|weekly_bonus|close_bonus)$"))
async def handle_bonus(c: app, cq: CallbackQuery):
    user_id = cq.from_user.id
    data = cq.data
    user = get_user(user_id)
    now = datetime.utcnow()

    if data == "close_bonus":
        return await cq.message.delete()

    if data == "daily_bonus":
        last_claim = user.get("daily_claim")
        if last_claim and now < last_claim + timedelta(hours=24):
            remain = (last_claim + timedelta(hours=24)) - now
            return await cq.answer(f"Come back in {remain.seconds // 3600}h {remain.seconds // 60 % 60}m", show_alert=True)
        coins = user.get("coins", 0) + 100
        update_user(user_id, {"coins": coins, "daily_claim": now})
        return await cq.answer("✅ You got 100 coins today!", show_alert=True)

    if data == "weekly_bonus":
        last_claim = user.get("weekly_claim")
        if last_claim and now < last_claim + timedelta(days=7):
            remain = (last_claim + timedelta(days=7)) - now
            return await cq.answer(f"Come back in {remain.days}d {remain.seconds // 3600}h", show_alert=True)
        coins = user.get("coins", 0) + 500
        update_user(user_id, {"coins": coins, "weekly_claim": now})
        return await cq.answer("✅ You got 500 coins this week!", show_alert=True)
