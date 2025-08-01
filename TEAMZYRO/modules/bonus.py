import asyncio
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from TEAMZYRO import ZYRO as bot, user_collection

# Coin values
DAILY_REWARD = 100
WEEKLY_REWARD = 500

def get_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💸 Daily Bonus", callback_data="daily_bonus"),
            InlineKeyboardButton("🎁 Weekly Bonus", callback_data="weekly_bonus"),
            InlineKeyboardButton("❌ Close", callback_data="bonus_close")
        ]
    ])

@bot.on_message(filters.command("bonus") & filters.private)
async def show_bonus_buttons(client, message):
    await message.reply_text(
        "🎁 Choose your bonus:",
        reply_markup=get_keyboard()
    )

@bot.on_callback_query(filters.regex("^(daily_bonus|weekly_bonus|bonus_close)$"))
async def handle_bonus(client, query: CallbackQuery):
    user_id = query.from_user.id
    user = user_collection.find_one({"user_id": user_id}) or {}

    now = datetime.utcnow()
    action = query.data

    if action == "bonus_close":
        await query.message.delete()
        return

    if action == "daily_bonus":
        last_claim = user.get("last_daily", now - timedelta(days=1, seconds=1))
        cooldown = timedelta(days=1)
        reward = DAILY_REWARD
        field = "last_daily"

    elif action == "weekly_bonus":
        last_claim = user.get("last_weekly", now - timedelta(days=7, seconds=1))
        cooldown = timedelta(days=7)
        reward = WEEKLY_REWARD
        field = "last_weekly"

    if now - last_claim >= cooldown:
        user_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {field: now},
                "$inc": {"coins": reward}
            },
            upsert=True
        )
        await query.answer(f"✅ You received {reward} coins!", show_alert=True)
    else:
        remaining = cooldown - (now - last_claim)
        await query.answer(
            f"⏳ You can claim again in {str(remaining).split('.')[0]}", show_alert=True
        )
