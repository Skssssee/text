import random
from bson import ObjectId
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from TEAMZYRO import *

market_collection = db["market"]
user_market_state = {}  # To track which user sees which character in /market

# Prices by rarity
RARITY_PRICES = {3: 5000, 4: 9000, 6: 15000}

# Create a small price table string
PRICE_TABLE = "\n".join([f"Rarity {r} → {p} coins" for r, p in RARITY_PRICES.items()])

# /market command
@app.on_message(filters.command("market"))
async def show_market(client, message):
    user_id = message.from_user.id

    # Fetch only rare characters (3,4,6)
    characters_cursor = market_collection.find({"rarity": {"$in": [3, 4, 6]}})
    characters = await characters_cursor.to_list(length=None)

    if not characters:
        await message.reply("🌌 The Market is empty! No rare waifus available.")
        return

    # Randomly pick 3 characters
    characters_to_show = random.sample(characters, min(3, len(characters)))

    # Store user state
    user_market_state[user_id] = {"characters": characters_to_show, "current_index": 0}

    await send_market_character(user_id, message, 0)


# Helper function to send a market character
async def send_market_character(user_id, message_or_callback, index: int):
    state = user_market_state[user_id]
    characters = state["characters"]
    character = characters[index]

    # Build caption with rarity → price info
    caption_message = (
        f"🌟 **Rare Waifu Market!** 🌟\n\n"
        f"**Name:** {character['name']}\n"
        f"**Anime:** {character['anime']}\n"
        f"**Rarity:** {character['rarity']}\n"
        f"**Price:** {RARITY_PRICES.get(character['rarity'], character.get('price', 0))} coins\n\n"
        f"💎 Only most rare waifus appear here (Rarity 3, 4, 6)!\n\n"
        f"📜 **Rarity Price Table:**\n{PRICE_TABLE}"
    )

    keyboard = [
        [
            InlineKeyboardButton("💰 Buy Now", callback_data=f"market_buy_{index}"),
            InlineKeyboardButton("➡ Next", callback_data="market_next")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(message_or_callback, "id"):  # it's a message
        await message_or_callback.reply_photo(
            photo=character["img_url"],
            caption=caption_message,
            reply_markup=reply_markup
        )
    else:  # it's a callback
        await message_or_callback.message.edit_media(
            media=InputMediaPhoto(media=character['img_url'], caption=caption_message),
            reply_markup=reply_markup
        )


# Callback to buy market waifu
@app.on_callback_query(filters.regex(r"market_buy_(\d+)"))
async def buy_market_character(client, cq):
    user_id = cq.from_user.id
    index = int(cq.matches[0].group(1))

    state = user_market_state.get(user_id)
    if not state:
        return await cq.answer("⚠ Market session expired! Use /market again.", show_alert=True)

    characters = state["characters"]
    if index >= len(characters):
        return await cq.answer("⚠ This waifu is no longer available!", show_alert=True)

    character = characters[index]

    user = await user_collection.find_one({"id": user_id})
    if not user:
        return await cq.answer("🚫 You need to register first!", show_alert=True)
        return

    price = RARITY_PRICES.get(character["rarity"], character.get("price", 0))
    balance = user.get("balance", 0)

    if balance < price:
        return await cq.answer(f"💰 You need {price - balance} more coins to buy this waifu!", show_alert=True)

    # Deduct balance and add waifu
    new_balance = balance - price
    character_data = {
        "_id": ObjectId(),
        "img_url": character["img_url"],
        "name": character["name"],
        "anime": character["anime"],
        "rarity": character["rarity"],
        "id": character["id"]
    }

    user_chars = user.get("characters", [])
    user_chars.append(character_data)
    await user_collection.update_one(
        {"id": user_id},
        {"$set": {"balance": new_balance, "characters": user_chars}}
    )

    await cq.answer(f"🎉 Waifu purchased! New Balance: {new_balance} coins", show_alert=True)


# Callback to show next market waifu
@app.on_callback_query(filters.regex(r"market_next"))
async def next_market(client, cq):
    user_id = cq.from_user.id
    state = user_market_state.get(user_id)
    if not state:
        return await cq.answer("⚠ Market session expired! Use /market again.", show_alert=True)

    current_index = state["current_index"]
    next_index = (current_index + 1) % len(state["characters"])
    state["current_index"] = next_index

    await send_market_character(user_id, cq, next_index)
    await cq.answer()


# Admin command to add waifu to market
@app.on_message(filters.command("addmarket"))
@require_power("add_market")  # same as your /addshop power
async def add_to_market(client, message):
    args = message.text.split()[1:]

    if len(args) != 2:
        return await message.reply("🌌 Usage: /addmarket <id> <price>")

    character_id, price = args
    try:
        price = int(price)
    except ValueError:
        return await message.reply("🚫 Price must be a number!")

    character = await collection.find_one({"id": character_id})
    if not character:
        return await message.reply("🚫 This waifu doesn't exist!")

    character["price"] = price
    await market_collection.insert_one(character)

    await message.reply(f"🎉 {character['name']} added to the Rare Market for {price} coins!")
