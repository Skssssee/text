import random
from bson import ObjectId
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from TEAMZYRO import app, db, user_collection, collection, LOGGER

markets_collection = db["market"]

MARKET_TAG_IMAGES = [
    "https://files.catbox.moe/shslw1.jpg",
    "https://files.catbox.moe/syanmk.jpg",
    "https://files.catbox.moe/xokoit.jpg",
]

# --- Helper: Edit market item message ---
async def edit_market_item(message, character, caption, keyboard):
    try:
        if character.get("video_url"):
            await message.edit_media(
                InputMediaVideo(media=character["video_url"], caption=caption),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await message.edit_media(
                InputMediaPhoto(media=character["img_url"], caption=caption),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
    except Exception:
        await message.edit_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))


# --- /market command ---
@app.on_message(filters.command(["market", "hmarket", "hmarketmenu"]))
async def show_market(client, message):
    characters = await markets_collection.find().to_list(length=None)
    if not characters:
        return await message.reply("🌌 The Market is empty! No rare waifus available right now.")

    current = characters[0]

    caption = (
        f"🌟 **Welcome to the Market!** 🌟\n\n"
        f"**Name:** {current.get('name')}\n"
        f"**Anime:** {current.get('anime')}\n"
        f"**Rarity:** {current.get('rarity')}\n"
        f"**Price:** {current.get('price')} Star Coins\n"
        f"**Stock:** {current.get('stock', 1)}\n"
        f"**ID:** {current.get('id')}\n\n"
        "Use the buttons below to buy or browse waifus."
    )

    keyboard = [
        [
            InlineKeyboardButton("◀️ Prev", callback_data=f"market_prev_{str(current['_id'])}"),
            InlineKeyboardButton("ᴄʟᴀɪᴍ ɴᴏᴡ!", callback_data=f"market_buy_{str(current['_id'])}"),
            InlineKeyboardButton("Next ▶️", callback_data=f"market_next_{str(current['_id'])}"),
        ]
    ]

    try:
        if current.get("video_url"):
            await message.reply_video(
                video=current["video_url"],
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await message.reply_photo(
                photo=current["img_url"],
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
    except Exception as e:
        LOGGER.exception("Failed to send market media: %s", e)
        await message.reply(caption, reply_markup=InlineKeyboardMarkup(keyboard))


# --- Market Next / Prev helpers ---
def market_caption(character):
    return (
        f"🌟 **Market** 🌟\n\n"
        f"**Name:** {character.get('name')}\n"
        f"**Anime:** {character.get('anime')}\n"
        f"**Rarity:** {character.get('rarity')}\n"
        f"**Price:** {character.get('price')} Star Coins\n"
        f"**Stock:** {character.get('stock', 1)}\n"
        f"**ID:** {character.get('id')}\n\n"
        "Use the buttons below to buy or browse."
    )

@app.on_callback_query(filters.regex(r"^market_next_"))
async def market_next(client, callback_query):
    char_oid = callback_query.data.split("_")[-1]
    characters = await markets_collection.find().to_list(length=None)
    if not characters:
        return await callback_query.answer("🌌 Market is empty!", show_alert=True)

    ids = [str(c["_id"]) for c in characters]
    if char_oid not in ids:
        return await callback_query.answer("⚠️ This waifu is no longer available!", show_alert=True)

    current_index = ids.index(char_oid)
    next_index = (current_index + 1) % len(characters)
    character = characters[next_index]

    keyboard = [
        [
            InlineKeyboardButton("◀️ Prev", callback_data=f"market_prev_{str(character['_id'])}"),
            InlineKeyboardButton("ᴄʟᴀɪᴍ ɴᴏᴡ!", callback_data=f"market_buy_{str(character['_id'])}"),
            InlineKeyboardButton("Next ▶️", callback_data=f"market_next_{str(character['_id'])}"),
        ]
    ]

    await edit_market_item(callback_query.message, character, market_caption(character), keyboard)
    await callback_query.answer()

@app.on_callback_query(filters.regex(r"^market_prev_"))
async def market_prev(client, callback_query):
    char_oid = callback_query.data.split("_")[-1]
    characters = await markets_collection.find().to_list(length=None)
    if not characters:
        return await callback_query.answer("🌌 Market is empty!", show_alert=True)

    ids = [str(c["_id"]) for c in characters]
    if char_oid not in ids:
        return await callback_query.answer("⚠️ This waifu is no longer available!", show_alert=True)

    current_index = ids.index(char_oid)
    prev_index = (current_index - 1) % len(characters)
    character = characters[prev_index]

    keyboard = [
        [
            InlineKeyboardButton("◀️ Prev", callback_data=f"market_prev_{str(character['_id'])}"),
            InlineKeyboardButton("ᴄʟᴀɪᴍ ɴᴏᴡ!", callback_data=f"market_buy_{str(character['_id'])}"),
            InlineKeyboardButton("Next ▶️", callback_data=f"market_next_{str(character['_id'])}"),
        ]
    ]

    await edit_market_item(callback_query.message, character, market_caption(character), keyboard)
    await callback_query.answer()


# --- Market Buy with Stock Support ---
@app.on_callback_query(filters.regex(r"^market_buy_"))
async def market_buy(client, callback_query):
    user_id = callback_query.from_user.id
    char_oid = callback_query.data.split("_")[-1]

    character = await markets_collection.find_one({"_id": ObjectId(char_oid)})
    if not character:
        return await callback_query.answer("🚫 This waifu has already been bought!", show_alert=True)

    stock = int(character.get("stock", 1))
    if stock <= 0:
        await markets_collection.delete_one({"_id": ObjectId(char_oid)})
        return await callback_query.answer("🚫 Out of stock!", show_alert=True)

    user = await user_collection.find_one({"id": user_id})
    if not user:
        return await callback_query.answer("🚫 You need to register first!", show_alert=True)

    price = int(character.get("price", 0))
    balance = int(user.get("balance", 0))
    if balance < price:
        return await callback_query.answer(
            f"🌠 You need {price - balance} more Star Coins to buy this waifu!", show_alert=True
        )

    # Deduct balance and add character to user's collection
    new_balance = balance - price
    user_chars = user.get("characters", [])
    user_chars.append({
        "_id": ObjectId(),
        "img_url": character.get("img_url"),
        "video_url": character.get("video_url"),
        "name": character.get("name"),
        "anime": character.get("anime"),
        "rarity": character.get("rarity"),
        "id": character.get("id"),
    })
    await user_collection.update_one(
        {"id": user_id}, {"$set": {"balance": new_balance, "characters": user_chars}}
    )

    # Reduce stock by 1
    stock -= 1
    if stock <= 0:
        await markets_collection.delete_one({"_id": ObjectId(char_oid)})
    else:
        await markets_collection.update_one({"_id": ObjectId(char_oid)}, {"$set": {"stock": stock}})

    # Send DM
    tag_img = random.choice(MARKET_TAG_IMAGES)
    dm_text = (
        f"🎉 Congratulations! 🎉\n\n"
        f"You've just added **{character.get('name')}** (Rarity: {character.get('rarity')}) to your collection!\n\n"
        "Thank you for shopping at the Market. ✨"
    )

    try:
        if character.get("video_url"):
            await client.send_video(chat_id=user_id, video=character["video_url"], caption=dm_text)
        else:
            await client.send_photo(chat_id=user_id, photo=character.get("img_url"), caption=dm_text)
        await client.send_photo(chat_id=user_id, photo=tag_img,
                                caption="ᴛʜᴀɴᴋꜱ ꜰᴏʀ ꜱʜᴏᴘᴘɪɴɢ!")
    except Exception as e:
        LOGGER.warning("Failed to DM user after purchase: %s", e)

    await callback_query.answer("Payment Successful 🎉\nCheck bot DM to see your collection!", show_alert=True)

    # Update market message caption
    new_caption = f"✅ {character.get('name')} has been purchased!\nStock left: {stock}"
    await callback_query.message.edit_caption(new_caption)


# --- /add_market with Stock Support ---
SUDO_USERS = [7553434931, 8189669345, 1741022717]  # apne admin IDs daal do

@app.on_message(filters.command("add_market"))
async def add_to_market(client, message):
    user_id = message.from_user.id
    if user_id not in SUDO_USERS:
        return await message.reply("❌ You don't have permission to use this command.")

    args = message.text.split()[1:]
    if len(args) != 3:
        return await message.reply("🌌 Usage: /add_market [id] [price] [stock]")

    character_id, price, stock = args
    try:
        price = int(price)
        stock = int(stock)
    except ValueError:
        return await message.reply("🚫 Price and stock must be numbers.")

    character = await collection.find_one({"id": character_id})
    if not character:
        return await message.reply("🚫 That character ID doesn't exist.")

    character_copy = dict(character)
    character_copy["price"] = price
    character_copy["stock"] = stock
    if character_copy.get("amv_url") and not character_copy.get("video_url"):
        character_copy["video_url"] = character_copy.get("amv_url")

    await markets_collection.insert_one(character_copy)
    await message.reply(
        f"🎉 {character_copy.get('name')} has been added to the Market for {price} Coins! Stock: {stock}"
    )
