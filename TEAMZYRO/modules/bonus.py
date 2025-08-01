from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from datetime import datetime, timedelta
from TEAMZYRO import app, user_collection

# --- Bonus settings ---
DAILY_REWARD = 100
WEEKLY_REWARD = 500

# --- Bonus Command Handler ---
@app.on_message(filters.command("bonus"))
async def bonus_menu(client, message):
    user_id = message.from_user.id

    buttons = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("🎁 Daily Bonus", callback_data="daily_bonus"),
            InlineKeyboardButton("📦 Weekly Bonus", callback_data="weekly_bonus"),
            InlineKeyboardButton("❌ Close", callback_data="bonus_close")
        ]]
    )

    media_group = [
        InputMediaPhoto("https://telegra.ph/file/f632a47bc3c6abfa26d92.jpg", caption="🎉 Claim your bonuses below!"),
        InputMediaPhoto("https://telegra.ph/file/fdbb8f61d1014c9f79b89.jpg")
    ]

    await client.send_media_group(message.chat.id, media_group)
    await message.reply_text("👇 Click a button below to claim your bonus:", reply_markup=buttons)

# --- Callback Query Handler ---
@app.on_callback_query(filters.regex("bonus"))
async def handle_bonus(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    now = datetime.utcnow()

    user_data = user_collection.find_one({"user_id": user_id}) or {}

    if callback_query.data == "daily_bonus":
        last_claim = user_data.get("last_daily_bonus")
        if not last_claim or now - last_claim >= timedelta(days=1):
            user_collection.update_one(
                {"user_id": user_id},
                {
                    "$inc": {"coins": DAILY_REWARD},
                    "$set": {"last_daily_bonus": now}
                },
                upsert=True
            )
            await callback_query.answer(f"✅ You've received {DAILY_REWARD} coins!", show_alert=True)
        else:
            await callback_query.answer("❌ You’ve already claimed your daily bonus.", show_alert=True)

    elif callback_query.data == "weekly_bonus":
        last_claim = user_data.get("last_weekly_bonus")
        if not last_claim or now - last_claim >= timedelta(weeks=1):
            user_collection.update_one(
                {"user_id": user_id},
                {
                    "$inc": {"coins": WEEKLY_REWARD},
                    "$set": {"last_weekly_bonus": now}
                },
                upsert=True
            )
            await callback_query.answer(f"✅ You've received {WEEKLY_REWARD} coins!", show_alert=True)
        else:
            await callback_query.answer("❌ You’ve already claimed your weekly bonus.", show_alert=True)

    elif callback_query.data == "bonus_close":
        await callback_query.message.delete()
