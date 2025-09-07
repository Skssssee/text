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
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
    InputMediaVideo
)
from motor.motor_asyncio import AsyncIOMotorClient

from TEAMZYRO import *  # Ensure this imports: app, user_collection, collection, require_power, db

# -------------------- Logging --------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.FileHandler("log.txt"), logging.StreamHandler()],
    level=logging.INFO,
)
LOGGER = logging.getLogger(__name__)

shops_collection = db["shops"]

# -------------------- User sessions --------------------
user_sessions = {}  # user_id: {"current_index": int, "characters": list, "message_id": int}

# -------------------- /shop command --------------------
@app.on_message(filters.command(["shop", "hshopmenu", "hshop"]))
async def show_shop(client, message):
    user_id = message.from_user.id
    characters = await shops_collection.find().to_list(length=None)

    if not characters:
        return await message.reply("🌌 The Cosmic Bazaar is empty! No legendary characters await you yet.")

    user_sessions[user_id] = {"current_index": 0, "characters": characters}

    character = characters[0]
    caption = get_shop_caption(character)
    keyboard = get_shop_keyboard(0)

    await send_shop_media(client, message.chat.id, character, caption, keyboard, user_id)


# -------------------- Callback handler --------------------
@app.on_callback_query()
async def shop_callback(client, callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data

    if user_id not in user_sessions:
        return await callback_query.answer("🌌 Open the shop first using /shop!", show_alert=True)

    session = user_sessions[user_id]
    characters = session["characters"]
    current_index = session["current_index"]

    if data == "close":
        try:
            await callback_query.message.delete()
        except:
            await callback_query.answer("❌ Unable to close!", show_alert=True)
        return

    if data == "next":
        current_index = (current_index + 1) % len(characters)
    elif data == "prev":
        current_index = (current_index - 1) % len(characters)
    elif data.startswith("buy_"):
        current_index = int(data.split("_")[1])
        session["current_index"] = current_index
        await buy_character(client, callback_query)
        return

    session["current_index"] = current_index
    character = characters[current_index]

    caption = get_shop_caption(character)
    keyboard = get_shop_keyboard(current_index)

    await send_shop_media(client, callback_query.message.chat.id, character, caption, keyboard, user_id, edit=True)
    await callback_query.answer()


# -------------------- Helpers --------------------
def get_shop_caption(character):
    return (
        f"🌟 **Explore the Cosmic Bazaar!** 🌟\n\n"
        f"**Hero:** {character.get('name','Unknown')}\n"
        f"**Realm:** {character.get('anime','Unknown')}\n"
        f"**Legend Tier:** {character.get('rarity','Unknown')}\n"
        f"**Cost:** {character.get('price',0)} Star Coins\n"
        f"**Stock:** {character.get('stock',0)}\n"
        f"**ID:** {character.get('id','N/A')}\n"
        f"✨ Summon Epic Legends to Your Collection! ✨"
    )


def get_shop_keyboard(index):
    return [
        [
            InlineKeyboardButton("⬅ ᴘʀᴇᴠ", callback_data="prev"),
            InlineKeyboardButton("ᴄʟᴀɪᴍ ɴᴏᴡ!", callback_data=f"buy_{index}"),
            InlineKeyboardButton("ɴᴇxᴛ ➝", callback_data="next")
        ],
        [InlineKeyboardButton("❌ ᴄʟᴏꜱᴇ", callback_data="close")]
    ]


async def send_shop_media(client, chat_id, character, caption, keyboard, user_id, edit=False):
    try:
        media = InputMediaPhoto(media=character['img_url'], caption=caption)
        if character['img_url'].endswith((".mp4", ".MP4")):
            media = InputMediaVideo(media=character['img_url'], caption=caption)

        if edit:
            await client.edit_message_media(
                chat_id=chat_id,
                message_id=user_sessions[user_id]["message_id"],
                media=media,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            if character['img_url'].endswith((".mp4", ".MP4")):
                msg = await client.send_video(
                    chat_id=chat_id,
                    video=character['img_url'],
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                msg = await client.send_photo(
                    chat_id=chat_id,
                    photo=character['img_url'],
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            user_sessions[user_id]["message_id"] = msg.id
    except Exception as e:
        LOGGER.error(f"Send/edit media error: {e}")


# -------------------- /addshop command --------------------
@app.on_message(filters.command("addshop"))
@require_power("add_character")
async def add_to_shop(client, message):
    args = message.text.split()[1:]
    if len(args) != 3:
        return await message.reply("🌌 Usage: /addshop [id] [price] [stock]")

    character_id, price, stock = args
    try:
        price = int(price)
        stock = int(stock)
    except:
        return await message.reply("🚫 Price and stock must be valid numbers!")

    character = await collection.find_one({"id": character_id})
    if not character:
        return await message.reply("🚫 This legend doesn't exist!")

    character["price"] = price
    character["stock"] = stock
    await shops_collection.insert_one(character)

    await message.reply(f"🎉 {character['name']} added to the shop!\n💰 Price: {price} coins\n📦 Stock: {stock}")


# -------------------- Buy character --------------------
async def buy_character(client, callback_query):
    user_id = callback_query.from_user.id
    current_index = user_sessions[user_id]["current_index"]
    characters = await shops_collection.find().to_list(length=None)

    if current_index >= len(characters):
        return await callback_query.answer("🚫 This legend has vanished!", show_alert=True)

    character = characters[current_index]
    if character.get("stock", 0) <= 0:
        await shops_collection.delete_one({"_id": character["_id"]})
        return await callback_query.answer("⚠ SOLD OUT!", show_alert=True)

    user = await user_collection.find_one({"id": user_id})
    if not user:
        return await callback_query.answer("🚫 You must register first!", show_alert=True)

    price = character["price"]
    balance = user.get("balance", 0)
    if balance < price:
        return await callback_query.answer(f"🌠 You need {price - balance} more coins!", show_alert=True)

    # Deduct balance & add to collection
    new_balance = balance - price
    user.setdefault("characters", []).append({
        "_id": ObjectId(),
        "img_url": character["img_url"],
        "name": character["name"],
        "anime": character["anime"],
        "rarity": character["rarity"],
        "id": character["id"]
    })
    await user_collection.update_one({"id": user_id}, {"$set": {"balance": new_balance, "characters": user["characters"]}})

    # Reduce stock
    new_stock = character.get("stock", 1) - 1
    if new_stock <= 0:
        await shops_collection.delete_one({"_id": character["_id"]})
    else:
        await shops_collection.update_one({"_id": character["_id"]}, {"$set": {"stock": new_stock}})

    await callback_query.answer("✅ Purchased! Check your DMs.", show_alert=True)

    # Send DM
    try:
        if character['img_url'].endswith((".mp4", ".MP4")):
            await client.send_video(
                chat_id=user_id,
                video=character["img_url"],
                caption=f"✨ You got **{character['name']}** from *{character['anime']}*!\nRarity: {character['rarity']}"
            )
        else:
            await client.send_photo(
                chat_id=user_id,
                photo=character["img_url"],
                caption=f"✨ You got **{character['name']}** from *{character['anime']}*!\nRarity: {character['rarity']}"
            )
    except:
        await callback_query.message.reply("⚠ Could not DM you! Start bot privately.")

