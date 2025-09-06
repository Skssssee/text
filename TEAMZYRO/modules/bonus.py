import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters, types as t
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from TEAMZYRO import ZYRO as bot, user_collection

# Must-join group/channel ID
MUST_JOIN = -1002792716047   # 👈 tumhari group id

# Bonus amounts
DAILY_COINS = 100
WEEKLY_COINS = 1500   # weekly bonus

# /bonus command handler
@bot.on_message(filters.command("bonus"))
async def bonus_menu(_, message: t.Message):
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
@bot.on_callback_query()
async def bonus_handler(_, query: t.CallbackQuery):
    user_id = query.from_user.id

    # Must-join check
    try:
        member = await bot.get_chat_member(MUST_JOIN, user_id)
        if member.status in ["left", "kicked"]:
            return await query.answer(
                "🚨 You must join the required group to claim your bonus!",
                show_alert=True
            )
    except Exception:
        return await query.answer(
            "🚨 You must join the required group to claim your bonus!",
            show_alert=True
        )

    # Get user data or create if not exists
    user = await user_collection.find_one({"id": user_id})
    if not user:
        user = {
            "id": user_id,
            "coins": 0,
            "last_daily_claim": None,
            "last_weekly_claim": None,
        }
        await user_collection.insert_one(user)

    # Daily claim
    if query.data == "daily_claim":
        last_daily = user.get("last_daily_claim")
        if last_daily and (datetime.utcnow() - last_daily) < timedelta(days=1):
            remaining = timedelta(days=1) - (datetime.utcnow() - last_daily)
            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            return await query.answer(
                f"⏳ Already claimed! Next in {hours}h {minutes}m {seconds}s",
                show_alert=True
            )

        await user_collection.update_one(
            {"id": user_id},
            {"$inc": {"coins": DAILY_COINS}, "$set": {"last_daily_claim": datetime.utcnow()}}
        )
        return await query.answer(
            f"✅ You successfully claimed your Daily Bonus!\n💰 +{DAILY_COINS} coins",
            show_alert=True
        )

    # Weekly claim
    elif query.data == "weekly_claim":
        last_weekly = user.get("last_weekly_claim")
        if last_weekly and (datetime.utcnow() - last_weekly) < timedelta(weeks=1):
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
            {"$inc": {"coins": WEEKLY_COINS}, "$set": {"last_weekly_claim": datetime.utcnow()}}
        )
        return await query.answer(
            f"✅ You successfully claimed your Weekly Bonus!\n💰 +{WEEKLY_COINS} coins",
            show_alert=True
        )

    # Close button
    elif query.data == "close_bonus":
        await query.message.delete()
        return
