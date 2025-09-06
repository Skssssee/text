import random
from pyrogram import filters
from pyrogram.types import InputMediaPhoto
from TEAMZYRO import app, user_collection, waifu_collection

# Gacha cost
GACHA_COST = 1000

# Rarity chances
RARITY_CHANCES = {
    "Common": 60,
    "Rare": 25,
    "Epic": 10,
    "Legendary": 5,
}

RARITY_EMOJIS = {
    "Common": "⚪",
    "Rare": "🔵",
    "Epic": "🟣",
    "Legendary": "🟡",
}


def get_random_rarity():
    rand = random.randint(1, 100)
    total = 0
    for rarity, chance in RARITY_CHANCES.items():
        total += chance
        if rand <= total:
            return rarity
    return "Common"


@app.on_message(filters.command("gacha"))
async def gacha_summon(client, message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) < 2 or not args[1].isdigit():
        return await message.reply_text("❌ Usage: `/gacha <amount>`", quote=True)

    amount = int(args[1])
    if amount < GACHA_COST:
        return await message.reply_text(f"❌ Minimum {GACHA_COST} coins required per summon!")

    user = await user_collection.find_one({"id": user_id})
    if not user or user.get("balance", 0) < amount:
        return await message.reply_text("❌ You don't have enough balance!")

    # Deduct balance
    await user_collection.update_one({"id": user_id}, {"$inc": {"balance": -amount}})

    # Determine rarity
    rarity = get_random_rarity()

    # Get a waifu from DB with same rarity
    waifu = await waifu_collection.aggregate([
        {"$match": {"rarity": rarity}},
        {"$sample": {"size": 1}}
    ]).to_list(length=1)

    if not waifu:
        return await message.reply_text("⚠ No waifus available for this rarity. Admin must add some!")

    waifu = waifu[0]

    # Save waifu to user inventory
    await user_collection.update_one(
        {"id": user_id},
        {"$push": {"waifus": waifu}}
    )

    # Send spoiler photo with waifu details
    await message.reply_photo(
        waifu["image_url"],
        caption=(
            f"✨ **You summoned a waifu!**\n\n"
            f"👩 **Name:** {waifu['name']}\n"
            f"🎬 **Anime:** {waifu['anime']}\n"
            f"{RARITY_EMOJIS.get(rarity, '⚪')} **Rarity:** {rarity}\n"
            f"💰 **Cost:** {amount} coins"
        ),
        has_spoiler=True
  )
