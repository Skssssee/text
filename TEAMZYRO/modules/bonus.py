import asyncio
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from TEAMZYRO import ZYRO as bot, user_collection

# Bonus amounts
DAILY_COINS = 100
WEEKLY_COINS = 1500   # weekly bonus


# /bonus command
@bot.on_message(filters.command("bonus"))
async def bonus_menu(_, message: Message):
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🎁 Daily Claim", callback_data="daily_claim")],
            [InlineKeyboardButton("📅 Weekly Claim", callback_data="weekly_claim")],
            [InlineKeyboardButton("❌ Close", callback_data="close_bonus")]
        ]
    )
    await message.reply_text(
        "✨ ʙᴏɴᴜꜱ ᴍᴇɴᴜ ✨\n\nChoose one of the options below:",
        reply_markup=keyboard
    )


# Callback handler
@bot.on_callback_query(filters.regex("^(daily_claim|weekly_claim|close_bonus)$"))
async def bonus_handler(_, query: CallbackQuery):
    user_id = query.from_user.id

    # Get or create user
    user = await user_collection.find_one({"id": user_id})
    if not user:
        user = {
            "id": user_id,
            "balance": 0,
            "last_daily_claim": None,
            "last_weekly_claim": None,
        }
        await user_collection.insert_one(user)

    # Daily claim
    if query.data == "daily_claim":
        last_daily = user.get("last_daily_claim")
        if last_daily:
            last_daily = datetime.fromisoformat(last_daily)
            if (datetime.utcnow() - last_daily) < timedelta(days=1):
                remaining = timedelta(days=1) - (datetime.utcnow() - last_daily)
                hours, remainder = divmod(int(remaining.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                return await query.answer(
                    f"⏳ Already claimed! Next in {hours}h {minutes}m {seconds}s",
                    show_alert=True
                )

        await user_collection.update_one(
            {"id": user_id},
            {
                "$inc": {"balance": DAILY_COINS},
                "$set": {"last_daily_claim": datetime.utcnow().isoformat()}
            }
        )
        user = await user_collection.find_one({"id": user_id})
        return await query.answer(
            f"✅ Daily Bonus claimed!\n💰 +{DAILY_COINS} coins\n💎 Balance: {user['balance']} coins",
            show_alert=True
        )

    # Weekly claim
    elif query.data == "weekly_claim":
        last_weekly = user.get("last_weekly_claim")
        if last_weekly:
            last_weekly = datetime.fromisoformat(last_weekly)
            if (datetime.utcnow() - last_weekly) < timedelta(weeks=1):
                remaining = timedelta(weeks=1) - (datetime.utcnow() - last_weekly)
                days, remainder = divmod(int(remaining.total_seconds()), 86400)
                hours, remainder = divmod(remainder, 3600)
                minutes, seconds = divmod(remainder, 60)
                return await query.answer(
                    f"⏳ Already claimed! Next in {days}d {hours}h {minutes}m",
                    show_alert=True
                )

        await user_collection.update_one(
            {"id": user_id},
            {
                "$inc": {"balance": WEEKLY_COINS},
                "$set": {"last_weekly_claim": datetime.utcnow().isoformat()}
            }
        )
        user = await user_collection.find_one({"id": user_id})
        return await query.answer(
            f"✅ Weekly Bonus claimed!\n💰 +{WEEKLY_COINS} coins\n💎 Balance: {user['balance']} coins",
            show_alert=True
        )

    # Close button
    elif query.data == "close_bonus":
        await query.message.delete()
        
