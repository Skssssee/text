import random
from pyrogram import filters
from TEAMZYRO import ZYRO as bot, user_collection
from pyrogram.types import InputMediaVideo

# Toss videos
TOSS_VIDEOS = [
    "https://files.catbox.moe/3jb7hg.mp4",
    "https://files.catbox.moe/g1n4z6.mp4",
    "https://files.catbox.moe/5gei42.mp4",
    "https://files.catbox.moe/vt9gl9.mp4",
    "https://files.catbox.moe/gxoxl5.mp4"
]

@bot.on_message(filters.command("flip"))
async def coin_flip(client, message):
    user_id = message.from_user.id
    args = message.text.split()

    # Usage check
    if len(args) != 3:
        return await message.reply("Usage: `/flip <amount> <heads/tails>`", quote=True)

    try:
        amount = int(args[1])
        choice = args[2].lower()
    except ValueError:
        return await message.reply("❌ Invalid amount!", quote=True)

    if choice not in ["heads", "tails"]:
        return await message.reply("❌ Choice must be `heads` or `tails`.", quote=True)

    if amount <= 0:
        return await message.reply("❌ Amount must be positive.", quote=True)

    # Fetch user balance
    user = await user_collection.find_one({"user_id": user_id})
    if not user:
        user = {"user_id": user_id, "balance": 1000}
        await user_collection.insert_one(user)

    balance = user["balance"]

    if balance < amount:
        return await message.reply("❌ You don't have enough balance.", quote=True)

    # Deduct temporary bet
    await user_collection.update_one(
        {"user_id": user_id},
        {"$inc": {"balance": -amount}}
    )

    # Random toss result
    result = random.choice(["heads", "tails"])

    # Select random video
    video_url = random.choice(TOSS_VIDEOS)

    if choice == result:
        win_amount = amount * 2
        await user_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": win_amount}}
        )
        final_text = f"🪙 Toss Result: **{result.upper()}** 🎉\n✅ You won **+{amount}** coins!"
    else:
        win_amount = 0
        final_text = f"🪙 Toss Result: **{result.upper()}** ❌\n❌ You lost **-{amount}** coins."

    # Fetch updated balance
    updated_user = await user_collection.find_one({"user_id": user_id})
    final_balance = updated_user["balance"]

    caption = f"{final_text}\n\n💰 Balance: **{final_balance}**"

    # Send video with spoiler
    await message.reply_video(
        video_url,
        caption=f"||{caption}||"
                      )
  
