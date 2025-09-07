import random
from datetime import datetime, timedelta
from bson import ObjectId
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from TEAMZYRO import app, db, user_collection

markets_collection = db["market"]
user_data = {}

MARKET_TAG_IMAGES = [
    "https://files.catbox.moe/shslw1.jpg",
    "https://files.catbox.moe/syanmk.jpg",
    "https://files.catbox.moe/xokoit.jpg",
]

# --- Helper: Check IST Sunday ---
def is_ist_sunday():
    now_utc = datetime.utcnow()
    ist_now = now_utc + timedelta(hours=5, minutes=30)
    return ist_now.weekday() == 6

# --- Helper: Edit market message ---
async def edit_market_message(message, character, keyboard):
    try:
        if character.get("video_url"):
            await message.edit_media(
                InputMediaVideo(media=character["video_url"], caption=f"🌟 {character.get('name')} 🌟\nRarity: {character.get('rarity')}\nPrice: {character.get('price')}"),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await message.edit_media(
                InputMediaPhoto(media=character["img_url"], caption=f"🌟 {character.get('name')} 🌟\nRarity: {character.get('rarity')}\nPrice: {character.get('price')}"),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception:
        await message.edit_caption(
            caption=f"🌟 {character.get('name')} 🌟\nRarity: {character.get('rarity')}\nPrice: {character.get('price')}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# --- /market command ---
@app.on_message(filters.command(["market", "hmarket", "hmarketmenu"]))
async def show_market(client, message):
    user_id = message.from_user.id
    if not is_ist_sunday():
        return await message.reply("*Market is closed. Opens every Sunday!*")

    characters = await markets_collection.find().to_list(length=None)
    if not characters:
        return await message.reply("🌌 Market is empty!")

    current_index = 0
    character = characters[current_index]

    keyboard = [
        [
            InlineKeyboardButton("Prev", callback_data=f"market_prev:{current_index}"),
            InlineKeyboardButton("ᴄʟᴀɪᴍ ɴᴏᴡ!", callback_data=f"market_buy:{current_index}"),
            InlineKeyboardButton("Next", callback_data=f"market_next:{current_index}")
        ]
    ]

    try:
        if character.get("video_url"):
            await message.reply_video(character["video_url"], caption=f"🌟 {character.get('name')} 🌟\nRarity: {character.get('rarity')}\nPrice: {character.get('price')}", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await message.reply_photo(character["img_url"], caption=f"🌟 {character.get('name')} 🌟\nRarity: {character.get('rarity')}\nPrice: {character.get('price')}", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception:
        await message.reply(f"🌟 {character.get('name')} 🌟\nRarity: {character.get('rarity')}\nPrice: {character.get('price')}", reply_markup=InlineKeyboardMarkup(keyboard))

    user_data[user_id] = {"current_index": current_index}

# --- Prev/Next callback ---
async def handle_market_nav(callback_query, direction: str):
    user_id = callback_query.from_user.id
    characters = await markets_collection.find().to_list(length=None)
    if not characters:
        return await callback_query.answer("🌌 Market is empty!", show_alert=True)

    current_index = user_data.get(user_id, {}).get("current_index", 0)
    if direction == "next":
        new_index = (current_index + 1) % len(characters)
    else:
        new_index = (current_index - 1) % len(characters)

    character = characters[new_index]
    keyboard = [
        [
            InlineKeyboardButton("Prev", callback_data=f"market_prev:{new_index}"),
            InlineKeyboardButton("ᴄʟᴀɪᴍ ɴᴏᴡ!", callback_data=f"market_buy:{new_index}"),
            InlineKeyboardButton("Next", callback_data=f"market_next:{new_index}")
        ]
    ]

    await edit_market_message(callback_query.message, character, keyboard)
    user_data[user_id] = {"current_index": new_index}
    await callback_query.answer()

@app.on_callback_query(filters.regex(r"^market_next:\d+$"))
async def market_next(client, callback_query):
    await handle_market_nav(callback_query, "next")

@app.on_callback_query(filters.regex(r"^market_prev:\d+$"))
async def market_prev(client, callback_query):
    await handle_market_nav(callback_query, "prev")

# --- Buy callback ---
@app.on_callback_query(filters.regex(r"^market_buy:\d+$"))
async def market_buy(client, callback_query):
    user_id = callback_query.from_user.id
    index = int(callback_query.data.split(":")[1])

    if not is_ist_sunday():
        return await callback_query.answer("Market is closed!", show_alert=True)

    characters = await markets_collection.find().to_list(length=None)
    if index >= len(characters):
        return await callback_query.answer("🚫 This waifu is no longer available!", show_alert=True)

    character = characters[index]
    user = await user_collection.find_one({"id": user_id})
    if not user:
        return await callback_query.answer("🚫 You need to register first!", show_alert=True)

    price = int(character.get("price", 0))
    balance = int(user.get("balance", 0))
    if balance < price:
        return await callback_query.answer(f"🌠 You need {price - balance} more Star Coins!", show_alert=True)

    # Deduct and add character
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

    await user_collection.update_one({"id": user_id}, {"$set": {"balance": new_balance, "characters": user_chars}})

    tag_img = random.choice(MARKET_TAG_IMAGES)
    dm_text = f"🎉 Congratulations! 🎉\nYou've added {character.get('name')} (Rarity: {character.get('rarity')}) to your collection!"

    # Send DM
    try:
        if character.get("video_url"):
            await client.send_video(chat_id=user_id, video=character["video_url"], caption=dm_text)
        else:
            await client.send_photo(chat_id=user_id, photo=character.get("img_url"), caption=dm_text)
        await client.send_photo(chat_id=user_id, photo=tag_img, caption="ᴛʜᴀɴᴋꜱ ꜰᴏʀ ꜱʜᴏᴘᴘɪɴɢ ɪɴ ˹ 𝐆ᴏᴊᴏ ꭙ 𝐂ᴀᴛᴄʜᴇʀ ˼!")
        await callback_query.answer("🎉 Purchase successful! Check your DM for details.")
    except:
        await callback_query.answer("🎉 Purchased, but I couldn't DM you. Please /start the bot.", show_alert=True)
        
