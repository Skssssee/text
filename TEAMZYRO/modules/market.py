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

    current_index = 0
    character = characters[current_index]

    caption = (
        f"🌟 **Welcome to the Sunday Market!** 🌟\n\n"
        f"**Name:** {character.get('name')}\n"
        f"**Anime:** {character.get('anime')}\n"
        f"**Rarity:** {character.get('rarity')}\n"
        f"**Price:** {character.get('price')} Star Coins\n"
        f"**ID:** {character.get('id')}\n\n"
        "Use the buttons below to buy or browse waifus."
    )

    keyboard = [
        [
            InlineKeyboardButton("◀️ Prev", callback_data=f"market_prev_{current_index}"),
            InlineKeyboardButton("ᴄʟᴀɪᴍ ɴᴏᴡ!", callback_data=f"market_buy_{current_index}"),
            InlineKeyboardButton("Next ▶️", callback_data=f"market_next_{current_index}"),
        ]
    ]

    try:
        if character.get("video_url"):
            await message.reply_video(
                video=character["video_url"],
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await message.reply_photo(
                photo=character["img_url"],
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
        # fallback for text-only messages
        await message.edit_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))


# --- Market Next ---
@app.on_callback_query(filters.regex(r"^market_next_\d+$"))
async def market_next(client, callback_query):
    passed_index = int(callback_query.data.split("_")[-1])

    characters = await markets_collection.find().to_list(length=None)
    if not characters:
        return await callback_query.answer("🌌 Market is empty!", show_alert=True)

    next_index = (passed_index + 1) % len(characters)
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
            InlineKeyboardButton("◀️ Prev", callback_data=f"market_prev_{next_index}"),
            InlineKeyboardButton("ᴄʟᴀɪᴍ ɴᴏᴡ!", callback_data=f"market_buy_{next_index}"),
            InlineKeyboardButton("Next ▶️", callback_data=f"market_next_{next_index}"),
        ]
    ]

    await edit_market_item(callback_query.message, character, caption, keyboard)
    await callback_query.answer()


# --- Market Prev ---
@app.on_callback_query(filters.regex(r"^market_prev_\d+$"))
async def market_prev(client, callback_query):
    passed_index = int(callback_query.data.split("_")[-1])

    characters = await markets_collection.find().to_list(length=None)
    if not characters:
        return await callback_query.answer("🌌 Market is empty!", show_alert=True)

    prev_index = (passed_index - 1) % len(characters)
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
            InlineKeyboardButton("◀️ Prev", callback_data=f"market_prev_{prev_index}"),
            InlineKeyboardButton("ᴄʟᴀɪᴍ ɴᴏᴡ!", callback_data=f"market_buy_{prev_index}"),
            InlineKeyboardButton("Next ▶️", callback_data=f"market_next_{prev_index}"),
        ]
    ]

    await edit_market_item(callback_query.message, character, caption, keyboard)
    await callback_query.answer()


# --- Market Buy ---
@app.on_callback_query(filters.regex(r"^market_buy_\d+$"))
async def market_buy(client, callback_query):
    user_id = callback_query.from_user.id
    index = int(callback_query.data.split("_")[-1])

    if not is_ist_sunday():
        return await callback_query.answer("*Market is closed. Opens every Sunday!*", show_alert=True)

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
        return await callback_query.answer(
            f"🌠 You need {price - balance} more Star Coins to buy this waifu!", show_alert=True
        )

    # Deduct balance and add character
    new_balance = balance - price
    user_chars = user.get("characters", [])
    character_data = {
        "_id": ObjectId(),
        "img_url": character.get("img_url"),
        "video_url": character.get("video_url"),
        "name": character.get("name"),
        "anime": character.get("anime"),
        "rarity": character.get("rarity"),
        "id": character.get("id"),
    }
    user_chars.append(character_data)

    await user_collection.update_one(
        {"id": user_id}, {"$set": {"balance": new_balance, "characters": user_chars}}
    )

    tag_img = random.choice(MARKET_TAG_IMAGES)
    dm_text = (
        f"🎉 Congratulations! 🎉\n\n"
        f"You've just added **{character.get('name')}** (Rarity: {character.get('rarity')}) to your collection!\n\n"
        "Thank you for shopping at the Sunday Market. ✨"
    )

    dm_sent = True
    try:
        if character.get("video_url"):
            await client.send_video(chat_id=user_id, video=character["video_url"], caption=dm_text)
            await client.send_photo(chat_id=user_id, photo=tag_img, caption="ᴛʜᴀɴᴋꜱ ꜰᴏʀ ꜱʜᴏᴘᴘɪɴɢ ɪɴ ˹ 𝐆ᴏᴊᴏ ꭙ 𝐂ᴀᴛᴄʜᴇʀ ˼!")
        else:
            await client.send_photo(chat_id=user_id, photo=character.get("img_url"), caption=dm_text)
            await client.send_photo(chat_id=user_id, photo=tag_img, caption="ᴛʜᴀɴᴋꜱ ꜰᴏʀ ꜱʜᴏᴘᴘɪɴɢ ɪɴ ˹ 𝐆ᴏᴊᴏ ꭙ 𝐂ᴀᴛᴄʜᴇʀ ˼!")
    except Exception as e:
        LOGGER.warning("Failed to DM user after purchase: %s", e)
        dm_sent = False

    # Show popup notification
    await callback_query.answer(
        "Payment Successful 🎉\nCheck bot DM to see your collection!",
        show_alert=True
    )

    # Optional: also send message in chat
    if dm_sent:
        await callback_query.message.reply_text(
            f"🎉 {character.get('name')} has been added to your collection! Check your DM for details.",
            parse_mode="html"
        )
    else:
        await callback_query.message.reply_text(
            f"🎉 {character.get('name')} added to your collection. I couldn't DM you — please /start the bot so I can send the congratulations DM."
        )


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

