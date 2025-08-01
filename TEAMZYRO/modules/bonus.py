from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from modules.database.bonus_db import can_claim_bonus, update_bonus_time

DAILY_REWARD = 100
WEEKLY_REWARD = 500

@Client.on_message(filters.command("bonus"))
async def bonus_handler(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌞 Daily Bonus", callback_data="daily_bonus")],
        [InlineKeyboardButton("📅 Weekly Bonus", callback_data="weekly_bonus")],
        [InlineKeyboardButton("❌ Close", callback_data="bonus_close")]
    ])
    await message.reply("🎁 Choose your bonus:", reply_markup=keyboard)

@Client.on_callback_query(filters.regex("^(daily_bonus|weekly_bonus|bonus_close)$"))
async def bonus_callback(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data

    if data == "bonus_close":
        await callback.message.delete()
        return

    if data == "daily_bonus":
        bonus_type = "daily"
        reward = DAILY_REWARD
        cooldown = 24
    elif data == "weekly_bonus":
        bonus_type = "weekly"
        reward = WEEKLY_REWARD
        cooldown = 168

    if can_claim_bonus(user_id, bonus_type, cooldown):
        update_bonus_time(user_id, bonus_type)
        await callback.answer(f"✅ You received {reward} waifu coins!", show_alert=True)
        # TODO: Update user coins if coin system is there
    else:
        await callback.answer("⛔ Already claimed! Try later.", show_alert=True)
