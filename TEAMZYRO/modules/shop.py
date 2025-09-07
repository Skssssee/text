import urllib.request
import uuid
import requests
import random
import html
import logging
from pymongo import ReturnDocument
from typing import List
from bson import ObjectId
from datetime import datetime, timedelta
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from motor.motor_asyncio import AsyncIOMotorClient

from TEAMZYRO import *

shops_collection = db["shops"]
user_data = {}

async def get_user_data(user_id):
    return await user_collection.find_one({"id": user_id})

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.FileHandler("log.txt"), logging.StreamHandler()],
    level=logging.INFO,
)
LOGGER = logging.getLogger(__name__)

# --- Show Shop ---
@app.on_message(filters.command(["shop", "hshopmenu", "hshop"]))
async def show_shop(client, message):
    user_id = message.from_user.id

    characters = await shops_collection.find().to_list(length=None)
    if not characters:
        await message.reply("🌌 The Cosmic Bazaar is empty! No legendary characters await you yet.")
        return

    current_index = 0
    character = characters[current_index]

    caption_message = (
        f"🌟 **Step into the Cosmic Bazaar!** 🌟\n\n"
        f"**Hero:** {character['name']}\n"
        f"**Realm:** {character['anime']}\n"
        f"**Legend Tier:** {character['rarity']}\n"
        f"**Cost:** {character['price']} Star Coins\n"
        f"**ID:** {character['id']}\n"
        f"✨ Unleash Epic Legends in Your Collection! ✨"
    )

    keyboard = [
        [
            InlineKeyboardButton("ᴄʟᴀɪᴍ ɴᴏᴡ!", callback_data=f"buy_{current_index}"),
            InlineKeyboardButton("ɴᴇxᴛ ʟᴇɢᴇɴᴅ ➝", callback_data="next")
        ]
    ]

    sent = await message.reply_photo(
        photo=character['img_url'],
        caption=caption_message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    user_data[user_id] = {"current_index": current_index, "characters": characters, "shop_message_id": sent.id}


# --- Buy Character ---
@app.on_callback_query(filters.regex(r"^buy_\d+$"))
async def buy_character(client, callback_query):
    user_id = callback_query.from_user.id
    current_index = int(callback_query.data.split("_")[1])

    # Load characters for user session
    characters = user_data.get(user_id, {}).get("characters", [])
    if not characters or current_index >= len(characters):
        await callback_query.answer("🚫 This legend has vanished from the Bazaar!", show_alert=True)
        return

    character = characters[current_index]

    # Check user balance
    user = await user_collection.find_one({"id": user_id})
    if not user:
        await callback_query.answer("🚫 Traveler, you must register first!", show_alert=True)
        return

    price = character['price']
    current_balance = user.get("balance", 0)

    if current_balance < price:
        await callback_query.answer(
            f"🌠 You need {price - current_balance} more Star Coins to claim this legend!",
            show_alert=True
        )
        return

    # Deduct and update user
    new_balance = current_balance - price
    character_data = {
        "_id": ObjectId(),
        "img_url": character["img_url"],
        "name": character["name"],
        "anime": character["anime"],
        "rarity": character["rarity"],
        "id": character["id"]
    }

    user.setdefault("characters", []).append(character_data)
    await user_collection.update_one(
        {"id": user_id},
        {"$set": {"balance": new_balance, "characters": user["characters"]}}
    )

    # Popup confirmation
    await callback_query.answer("✅ Payment Successfully Received! Check your DMs.", show_alert=True)

    # Send DM with waifu info
    try:
        await client.send_photo(
            chat_id=user_id,
            photo=character["img_url"],
            caption=(
                "╔══════════════════════╗\n"
                "   ✨ **ＰＡＹＭＥＮＴ ＲＥＣＥＩＶＥＤ** ✨\n"
                "╚══════════════════════╝\n\n"
                f"🎀 You claimed: **{character['name']}**\n"
                f"🌌 From: {character['anime']}\n"
                f"💎 Rarity: {character['rarity']}\n\n"
                "💖 Thanks for shopping in **ɢᴏᴊᴏ ᴄᴀᴛᴄʜᴇʀ ʙᴏᴛ**!\n"
                "✨ Your waifu has been added to your collection!"
            )
        )
    except:
        await callback_query.message.reply("⚠ Could not DM you! Please start the bot privately.")


# --- Next Item ---
@app.on_callback_query(filters.regex("^next$"))
async def next_item(client, callback_query):
    user_id = callback_query.from_user.id
    state = user_data.get(user_id, {})

    characters = state.get("characters", [])
    if not characters:
        await callback_query.answer("🌌 No more legends in the Bazaar!", show_alert=True)
        return

    current_index = state.get("current_index", 0)
    next_index = (current_index + 1) % len(characters)
    character = characters[next_index]

    caption_message = (
        f"🌟 **Explore the Cosmic Bazaar!** 🌟\n\n"
        f"**Hero:** {character['name']}\n"
        f"**Realm:** {character['anime']}\n"
        f"**Legend Tier:** {character['rarity']}\n"
        f"**Cost:** {character['price']} Star Coins\n"
        f"**ID:** {character['id']}\n"
        f"✨ Summon Epic Legends to Your Collection! ✨"
    )

    keyboard = [
        [
            InlineKeyboardButton("ᴄʟᴀɪᴍ ɴᴏᴡ!", callback_data=f"buy_{next_index}"),
            InlineKeyboardButton("ɴᴇxᴛ ʟᴇɢᴇɴᴅ ➝", callback_data="next")
        ]
    ]

    await callback_query.message.edit_media(
        media=InputMediaPhoto(media=character['img_url'], caption=caption_message),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    user_data[user_id]["current_index"] = next_index
    await callback_query.answer()


@app.on_message(filters.command("addshop"))
@require_power("add_character")
async def add_to_shop(client, message):
    args = message.text.split()[1:]

    if len(args) != 3:
        return await message.reply("🌌 Usage: /addshop <id> <price> <stock>")

    character_id, price, stock = args

    try:
        price = int(price)
        stock = int(stock)
    except ValueError:
        return await message.reply("🚫 Price and stock must be valid numbers!")

    character = await collection.find_one({"id": character_id})
    if not character:
        return await message.reply("🚫 This legend doesn't exist in the Cosmos!")

    character["price"] = price
    character["stock"] = stock  # ✅ stock system

    await shops_collection.insert_one(character)

    await message.reply(
        f"🎉 {character['name']} added to the Cosmic Bazaar!\n"
        f"💰 Price: {price} coins\n"
        f"📦 Stock: {stock} available"
    )


@app.on_callback_query(filters.regex(r"^buy_\d+$"))
async def buy_character(client, callback_query):
    user_id = callback_query.from_user.id
    current_index = int(callback_query.data.split("_")[1])

    characters_cursor = shops_collection.find()
    characters = await characters_cursor.to_list(length=None)

    if current_index >= len(characters):
        return await callback_query.answer("🚫 This legend has vanished from the Bazaar!", show_alert=True)

    character = characters[current_index]

    # ✅ Check stock
    if character.get("stock", 0) <= 0:
        await shops_collection.delete_one({"_id": character["_id"]})
        return await callback_query.answer("⚠ This legend is SOLD OUT!", show_alert=True)

    user = await user_collection.find_one({"id": user_id})
    if not user:
        return await callback_query.answer("🚫 Traveler, you must register your presence in the Cosmos!", show_alert=True)

    price = character["price"]
    current_balance = user.get("balance", 0)

    if current_balance < price:
        return await callback_query.answer(
            f"🌠 You need {price - current_balance} more Star Coins to claim this legend!",
            show_alert=True
        )

    # ✅ Deduct balance
    new_balance = current_balance - price

    # ✅ Character data
    character_data = {
        "_id": ObjectId(),
        "img_url": character["img_url"],
        "name": character["name"],
        "anime": character["anime"],
        "rarity": character["rarity"],
        "id": character["id"]
    }

    user["characters"].append(character_data)
    await user_collection.update_one(
        {"id": user_id},
        {"$set": {"balance": new_balance, "characters": user["characters"]}}
    )

    # ✅ Reduce stock
    new_stock = character.get("stock", 1) - 1
    if new_stock <= 0:
        await shops_collection.delete_one({"_id": character["_id"]})
    else:
        await shops_collection.update_one({"_id": character["_id"]}, {"$set": {"stock": new_stock}})

    # ✅ Popup
    await callback_query.answer("✅ Payment Successfully Received!", show_alert=True)

    # ✅ DM user with waifu
    try:
        await client.send_photo(
            chat_id=user_id,
            photo=character["img_url"],
            caption=(
                f"✨ ᴛʜᴀɴᴋꜱ ꜰᴏʀ ꜱʜᴏᴘᴘɪɴɢ ✨\n\n"
                f"🌸 **{character['name']}** from *{character['anime']}* "
                f"(Rarity: {character['rarity']}) is now in your collection!\n\n"
                f"🛒 ɢᴏᴊᴏ ᴄᴀᴛᴄʜᴇʀ ʙᴏᴛ"
            )
        )
    except Exception:
        pass
        
