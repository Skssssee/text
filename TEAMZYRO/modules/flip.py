import random
from pyrogram import filters
from TEAMZYRO import ZYRO as bot, user_collection

# Toss videos
TOSS_VIDEOS = [
    "https://files.catbox.moe/3jb7hg.mp4",
    "https://files.catbox.moe/g1n4z6.mp4",
    "https://files.catbox.moe/5gei42.mp4",
    "https://files.catbox.moe/vt9gl9.mp4",
    "https://files.catbox.moe/gxoxl5.mp4"
]

# Toss images
TOSS_IMAGES = [
    "https://files.catbox.moe/fp8m21.jpg",
    "https://files.catbox.moe/2t1ixu.jpg",
    "https://files.catbox.moe/uj3ktk.jpg",
    "https://files.catbox.moe/1mt3fo.jpg"
]

@bot.on_message(filters.command("flip"))
async def coin_flip(client, message):
    user_id = message.from_user.id
    args = message.text.split()

    # Usage check
    if len(args) != 3:
        return await message.reply_photo(
            random.choice(TOSS_IMAGES),
            caption="⚡ ᴜsᴀɢᴇ: `/flip <ᴀᴍᴏᴜɴᴛ> <head/tail>`"
        )

    try:
        amount = int(args[1])
        choice = args[2].lower()
    except ValueError:
        return await message.reply_photo(
            random.choice(TOSS_IMAGES),
            caption="❌ ɪɴᴠᴀʟɪᴅ ᴀᴍᴏᴜɴᴛ!"
        )

    if choice not in ["head", "tail"]:
        return await message.reply_photo(
            random.choice(TOSS_IMAGES),
            caption="❌ ᴄʜᴏɪᴄᴇ ᴍᴜsᴛ ʙᴇ `head` ᴏʀ `tail`."
        )

    if amount <= 0:
        return await message.reply_photo(
            random.choice(TOSS_IMAGES),
            caption="❌ ᴀᴍᴏᴜɴᴛ ᴍᴜsᴛ ʙᴇ ᴘᴏsɪᴛɪᴠᴇ!"
        )

    # Fetch user balance
    user = await user_collection.find_one({"user_id": user_id})
    if not user:
        user = {"user_id": user_id, "balance": 1000}
        await user_collection.insert_one(user)

    balance = user["balance"]

    if balance < amount:
        return await message.reply_photo(
            random.choice(TOSS_IMAGES),
            caption="❌ ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴇɴᴏᴜɢʜ ʙᴀʟᴀɴᴄᴇ!"
        )

    # Deduct bet first
    await user_collection.update_one(
        {"user_id": user_id},
        {"$inc": {"balance": -amount}}
    )

    # Toss result
    result = random.choice(["head", "tail"])
    video_url = random.choice(TOSS_VIDEOS)

    if choice == result:
        win_amount = amount * 2
        await user_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": win_amount}}
        )
        final_text = (
            f"🪙 ᴛᴏss ʀᴇsᴜʟᴛ: **{result.upper()}** 🎉\n"
            f"✅ ʏᴏᴜ ᴡᴏɴ **+{amount}** ᴄᴏɪɴs!"
        )
    else:
        final_text = (
            f"🪙 ᴛᴏss ʀᴇsᴜʟᴛ: **{result.upper()}** ❌\n"
            f"❌ ʏᴏᴜ ʟᴏsᴛ **-{amount}** ᴄᴏɪɴs."
        )

    # Fetch updated balance
    updated_user = await user_collection.find_one({"user_id": user_id})
    final_balance = updated_user["balance"]

    caption = f"{final_text}\n\n💰 ᴄᴜʀʀᴇɴᴛ ʙᴀʟᴀɴᴄᴇ: **{final_balance}**"

    # Send video with spoiler
    await message.reply_video(
        video_url,
        caption=f"||{caption}||"
    )
