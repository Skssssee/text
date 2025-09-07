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
    InputMediaVideo,
)
from motor.motor_asyncio import AsyncIOMotorClient

from TEAMZYRO import *

markets_collection = db["market"]

MARKET_TAG_IMAGES = [
    "https://files.catbox.moe/shslw1.jpg",
    "https://files.catbox.moe/syanmk.jpg",
    "https://files.catbox.moe/xokoit.jpg",
]

# --- Helper: Check if it's Sunday IST ---
def is_ist_sunday():
    now_utc = datetime.utcnow()
    ist_now = now_utc + timedelta(hours=5, minutes=30)
    return ist_now.weekday() == 6  # Sunday

# --- /market command ---
@app.on_message(filters.command(["market", "hmarket", "hmarketmenu"]))
async def show_market(client, message):
    if not is_ist_sunday():
        return await message.reply("*Market is closed. Opens every Sunday!*")

    characters = await markets_collection.find().to_list(length=None)
    if not characters:
        return await message.reply("🌌 The Market is empty! No rare waifus available right now.")

    current = characters[0]

    caption = (
        f"🌟 **Welcome to the Sunday Market!** 🌟\n\n"
        f"**Name:** {current.get('name')}\n"
        f"**Anime:** {current.get('anime')}\n"
        f"**Rarity:** {current.get('rarity')}\n"
        f"**Price:** {current.get('price')} Star Coins\n"
        f"**ID:** {current.get('id')}\n\n"
        "Use the buttons below to buy or browse waifus."
    )

    keyboard = [
        [
            InlineKeyboardButton("◀️ Prev", callback_data=f"market_prev_{current['_id']}"),
            InlineKeyboardButton("ᴄʟᴀɪᴍ ɴᴏᴡ!", callback_data=f"market_buy_{current['_id']}"),
            InlineKeyboardButton("Next ▶️", callback_data=f"market_next_{current['_id']}"),
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


# --- Helper to edit market item ---
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


# --- Market Next ---
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

    caption = (
        f"🌟 **Sunday Market** 🌟\n\n"
        f"**Name:** {character.get('name')}\n"
        f"**Anime:** {character.get('anime')}\n"
        f"**Rarity:** {character.get('rarity')}\n"
        f"**Price:** {character.get('price')} Star Coins\n"
        f"**ID:** {character.get('id')}\n\n"
        "Use the buttons below to buy or browse."
    )

    keyboard = [
        [
            InlineKeyboardButton("◀️ Prev", callback_data=f"market_prev_{character['_id']}"),
            InlineKeyboardButton("ᴄʟᴀɪᴍ ɴᴏᴡ!", callback_data=f"market_buy_{character['_id']}"),
            InlineKeyboardButton("Next ▶️", callback_data=f"market_next_{character['_id']}"),
        ]
    ]

    await edit_market_item(callback_query.message, character, caption, keyboard)
    await callback_query.answer()


# --- Market Prev ---
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

    caption = (
        f"🌟 **Sunday Market** 🌟\n\n"
        f"**Name:** {character.get('name')}\n"
        f"**Anime:** {character.get('anime')}\n"
        f"**Rarity:** {character.get('rarity')}\n"
        f"**Price:** {character.get('price')} Star Coins\n"
        f"**ID:** {character.get('id')}\n\n"
        "Use the buttons below to buy or browse."
    )

    keyboard = [
        [
            InlineKeyboardButton("◀️ Prev", callback_data=f"market_prev_{character['_id']}"),
            InlineKeyboardButton("ᴄʟᴀɪᴍ ɴᴏᴡ!", callback_data=f"market_buy_{character['_id']}"),
            InlineKeyboardButton("Next ▶️", callback_data=f"market_next_{character['_id']}"),
        ]
    ]

    await edit_market_item(callback_query.message, character, caption, keyboard)
    await callback_query.answer()


# --- Market Buy ---
@app.on_callback_query(filters.regex(r"^market_buy_"))
async def market_buy(client, callback_query):
    user_id = callback_query.from_user.id
    char_oid = callback_query.data.split("_")[-1]

    if not is_ist_sunday():
        return await callback_query.answer("*Market is closed. Opens every Sunday!*", show_alert=True)

    character = await markets_collection.find_one({"_id": ObjectId(char_oid)})
    if not character:
        return await callback_query.answer("🚫 This waifu has already been bought!", show_alert=True)

    user = await user_collection.find_one({"id": user_id})
    if not user:
        return await callback_query.answer("🚫 You need to register first!", show_alert=True)

    price = int(character.get("price", 0))
    balance = int(user.get("balance", 0))

    if balance < price:
        return await callback_query.answer(
            f"🌠 You need {price - balance} more Star Coins to buy this waifu!", show_alert=True
        )

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

    # 🔥 Remove from market
    await markets_collection.delete_one({"_id": ObjectId(char_oid)})

    tag_img = random.choice(MARKET_TAG_IMAGES)
    dm_text = (
        f"🎉 Congratulations! 🎉\n\n"
        f"You've just added **{character.get('name')}** (Rarity: {character.get('rarity')}) to your collection!\n\n"
        "Thank you for shopping at the Sunday Market. ✨"
    )

    try:
        if character.get("video_url"):
            await client.send_video(chat_id=user_id, video=character["video_url"], caption=dm_text)
            await client.send_photo(chat_id=user_id, photo=tag_img,
                                    caption="ᴛʜᴀɴᴋꜱ ꜰᴏʀ ꜱʜᴏᴘᴘɪɴɢ ɪɴ ˹ 𝐆ᴏᴊᴏ ꭙ 𝐂ᴀᴛᴄʜᴇʀ ˼!")
        else:
            await client.send_photo(chat_id=user_id, photo=character.get("img_url"), caption=dm_text)
            await client.send_photo(chat_id=user_id, photo=tag_img,
                                    caption="ᴛʜᴀɴᴋꜱ ꜰᴏʀ ꜱʜᴏᴘᴘɪɴɢ ɪɴ ˹ 𝐆ᴏᴊᴏ ꭙ 𝐂ᴀᴛᴄʜᴇʀ ˼!")
    except Exception as e:
        LOGGER.warning("Failed to DM user after purchase: %s", e)

    await callback_query.answer("Payment Successful 🎉\nCheck bot DM to see your collection!", show_alert=True)
    await callback_query.message.edit_caption("✅ This waifu has been sold and removed from the Market.")


# --- /add_market command ---
@app.on_message(filters.command("add_market"))
@require_power("add_character")
async def add_to_market(client, message):
    args = message.text.split()[1:]
    if len(args) != 2:
        return await message.reply("🌌 Usage: /add_market <id> <price>")

    character_id, price = args
    try:
        price = int(price)
    except ValueError:
        return await message.reply("🚫 Price must be a number.")

    character = await collection.find_one({"id": character_id})
    if not character:
        return await message.reply("🚫 That character ID doesn't exist.")

    character_copy = dict(character)
    character_copy["price"] = price
    if character_copy.get("amv_url") and not character_copy.get("video_url"):
        character_copy["video_url"] = character_copy.get("amv_url")

    await markets_collection.insert_one(character_copy)
    await message.reply(
        f"🎉 {character_copy.get('name')} has been added to the Market for {price} Coins!"
)
    
