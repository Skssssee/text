import asyncio
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from datetime import datetime, timedelta
from TEAMZYRO import ZYRO as bot
from TEAMZYRO import user_collection

# Helper function to format datetime
def get_time_key(period):
    now = datetime.utcnow()
    if period == "daily":
        return now.strftime("daily-%Y-%m-%d")
    elif period == "weekly":
        # ISO week: e.g., "2025-W31"
        return now.strftime("weekly-%G-W%V")

# Create bonus buttons
def bonus_markup():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🎁 Daily Bonus", callback_data="claim_daily"),
                InlineKeyboardButton("🗓 Weekly Bonus", callback_data="claim_weekly")
            ],
            [InlineKeyboardButton("❌ Close", callback_data="bonus_close")]
        ]
    )

# /bonus command
@bot.on_message(filters.command("bonus"))
async def bonus_cmd(_, message: Message):
    await message.reply(
        "**🎁 Claim your bonus:**",
        reply_markup=bonus_markup()
    )

# Claim button handler
@bot.on_callback_query(filters.regex("claim_"))
async def claim_bonus(_, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data  # 'claim_daily' or 'claim_weekly'

    period = "daily" if "daily" in data else "weekly"
    reward = 100 if period == "daily" else 500
    time_key = get_time_key(period)

    # Check user's last claimed time
    user = user_collection.find_one({"user_id": user_id}) or {}
    last_claims = user.get("bonus_claims", {})
    
    if last_claims.get(time_key):
        await query.answer(f"You already claimed your {period} bonus 🎁", show_alert=True)
        return

    # Update user's coin and claim time
    user_collection.update_one(
        {"user_id": user_id},
        {
            "$inc": {"coins": reward},
            "$set": {f"bonus_claims.{time_key}": True}
        },
        upsert=True
    )

    await query.answer()
    await query.edit_message_text(
        f"✅ **{period.capitalize()} bonus claimed!**\n\nYou received `{reward}` coins 🎉",
        reply_markup=None
    )

# Close button
@bot.on_callback_query(filters.regex("bonus_close"))
async def close_bonus(_, query: CallbackQuery):
    await query.message.delete()
    await query.answer()
