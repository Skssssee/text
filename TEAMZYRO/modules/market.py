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
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from motor.motor_asyncio import AsyncIOMotorClient

from TEAMZYRO import *
from TEAMZYRO import market_collection


# helper: Indian Sunday check (IST = UTC +5:30)
def is_ist_sunday():
    now_utc = datetime.utcnow()
    ist_now = now_utc + timedelta(hours=5, minutes=30)
    # Python weekday: Monday=0 ... Sunday=6
    return ist_now.weekday() == 6

# sample random tag images (the ones you provided)
MARKET_TAG_IMAGES = [
    "https://files.catbox.moe/shslw1.jpg",
    "https://files.catbox.moe/syanmk.jpg",
    "https://files.catbox.moe/xokoit.jpg",
]

# /market command
@app.on_message(filters.command(["market", "hmarket", "hmarketmenu"]))
async def show_market(client, message):
    user_id = message.from_user.id

    # Check open day (Sunday IST)
    if not is_ist_sunday():
        await message.reply("*Market was closed open in every Sunday*")
        return

    characters_cursor = markets_collection.find()
    characters = await characters_cursor.to_list(length=None)

    if not characters:
        await message.reply("🌌 The Market is empty! No rare waifus available right now.")
        return

    # start from index 0
    current_index = 0
    character = characters[current_index]

    # prepare caption
    caption_message = (
        f"🌟 **Welcome to the Sunday Market!** 🌟\n\n"
        f"**Name:** {character.get('name')}\n"
        f"**Anime:** {character.get('anime')}\n"
        f"**Rarity:** {character.get('rarity')}\n"
        f"**Price:** {character.get('price')} Star Coins\n"
        f"**ID:** {character.get('id')}\n\n"
        "Use the buttons below to buy or browse previous/next waifus."
    )

    # buttons: Prev, Buy, Next
    keyboard = [
        [
            InlineKeyboardButton("◀️ Prev", callback_data=f"market_prev_{current_index}"),
            InlineKeyboardButton("ᴄʟᴀɪᴍ ɴᴏᴡ!", callback_data=f"market_buy_{current_index}"),
            InlineKeyboardButton("Next ▶️", callback_data=f"market_next_{current_index}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # send media: prefer video if available
    try:
        if character.get("video_url"):
            await message.reply_video(video=character["video_url"], caption=caption_message, reply_markup=reply_markup)
        else:
            await message.reply_photo(photo=character["img_url"], caption=caption_message, reply_markup=reply_markup)
    except Exception as e:
        LOGGER.exception("Failed to send market media: %s", e)
        # fallback to photo caption only
        await message.reply(caption_message, reply_markup=reply_markup)

    # store user state (message id isn't required but keep index)
    user_data[user_id] = {"current_index": current_index}

# callback: next
@app.on_callback_query(filters.regex(r"^market_next_\d+$"))
async def market_next(client, callback_query):
    user_id = callback_query.from_user.id
    # get index from data (we'll ignore passed index and use stored state if present)
    passed_index = int(callback_query.data.split("_")[-1])

    user_state = user_data.get(user_id, {})
    current_index = user_state.get("current_index", passed_index)

    characters_cursor = markets_collection.find()
    characters = await characters_cursor.to_list(length=None)
    if not characters:
        await callback_query.answer("🌌 Market is empty!", show_alert=True)
        return

    next_index = (current_index + 1) % len(characters)
    character = characters[next_index]

    caption_message = (
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
            InlineKeyboardButton("Next ▶️", callback_data=f"market_next_{next_index}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # edit media (handle video/photo both)
    try:
        if character.get("video_url"):
            await callback_query.message.edit_media(
                media=InputMediaPhoto(media=character["video_url"], caption=caption_message)  # pyrogram expects InputMediaVideo for video edits; if edit_media fails we'll fallback
            )
        else:
            await callback_query.message.edit_media(
                media=InputMediaPhoto(media=character["img_url"], caption=caption_message)
            )
        # update stored index
        user_data[user_id] = {"current_index": next_index}
        await callback_query.answer()
    except Exception:
        # fallback: edit caption only
        try:
            await callback_query.message.edit_caption(caption=caption_message, reply_markup=reply_markup)
            user_data[user_id] = {"current_index": next_index}
            await callback_query.answer()
        except Exception:
            LOGGER.exception("Failed to edit market next media")
            await callback_query.answer("Unable to load next item right now.", show_alert=True)

# callback: prev
@app.on_callback_query(filters.regex(r"^market_prev_\d+$"))
async def market_prev(client, callback_query):
    user_id = callback_query.from_user.id
    passed_index = int(callback_query.data.split("_")[-1])

    user_state = user_data.get(user_id, {})
    current_index = user_state.get("current_index", passed_index)

    characters_cursor = markets_collection.find()
    characters = await characters_cursor.to_list(length=None)
    if not characters:
        await callback_query.answer("🌌 Market is empty!", show_alert=True)
        return

    prev_index = (current_index - 1) % len(characters)
    character = characters[prev_index]

    caption_message = (
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
            InlineKeyboardButton("Next ▶️", callback_data=f"market_next_{prev_index}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if character.get("video_url"):
            await callback_query.message.edit_media(
                media=InputMediaPhoto(media=character["video_url"], caption=caption_message)
            )
        else:
            await callback_query.message.edit_media(
                media=InputMediaPhoto(media=character["img_url"], caption=caption_message)
            )
        user_data[user_id] = {"current_index": prev_index}
        await callback_query.answer()
    except Exception:
        try:
            await callback_query.message.edit_caption(caption=caption_message, reply_markup=reply_markup)
            user_data[user_id] = {"current_index": prev_index}
            await callback_query.answer()
        except Exception:
            LOGGER.exception("Failed to edit market prev media")
            await callback_query.answer("Unable to load previous item right now.", show_alert=True)

# callback: buy
@app.on_callback_query(filters.regex(r"^market_buy_\d+$"))
async def market_buy(client, callback_query):
    user_id = callback_query.from_user.id
    index = int(callback_query.data.split("_")[-1])

    # check Sunday
    if not is_ist_sunday():
        await callback_query.answer("*Market was closed open in every Sunday*", show_alert=True)
        return

    characters_cursor = markets_collection.find()
    characters = await characters_cursor.to_list(length=None)

    if index >= len(characters):
        await callback_query.answer("🚫 This waifu is no longer available!", show_alert=True)
        return

    character = characters[index]

    user = await user_collection.find_one({"id": user_id})
    if not user:
        await callback_query.answer("🚫 You need to register with the bot first!", show_alert=True)
        return

    price = int(character.get("price", 0))
    balance = int(user.get("balance", 0))

    if balance < price:
        await callback_query.answer(f"🌠 You need {price - balance} more Star Coins to buy this waifu!", show_alert=True)
        return

    # Deduct and add to user's characters immediately
    new_balance = balance - price

    # ensure 'characters' key present
    user_chars = user.get("characters", [])
    character_data = {
        "_id": ObjectId(),
        "img_url": character.get("img_url"),
        "video_url": character.get("video_url"),
        "name": character.get("name"),
        "anime": character.get("anime"),
        "rarity": character.get("rarity"),
        "id": character.get("id")
    }
    user_chars.append(character_data)

    # update DB
    await user_collection.update_one(
        {"id": user_id},
        {"$set": {"balance": new_balance, "characters": user_chars}}
    )

    # Optionally: remove from market after purchase? (not requested) — currently leave as is.

    # Prepare DM message (with random tag image)
    tag_img = random.choice(MARKET_TAG_IMAGES)
    dm_text = (
        f"🎉 Congratulations! 🎉\n\n"
        f"You've just added **{character.get('name')}** (Rarity: {character.get('rarity')}) to your collection!\n\n"
        "Thank you for shopping at the Sunday Market. ✨"
    )

    # Try sending DM with media (video or photo) and appended tag image
    dm_sent = True
    try:
        if character.get("video_url"):
            # send video then tag image as second photo
            await client.send_video(chat_id=user_id, video=character["video_url"], caption=dm_text)
            # send tag image separately
            await client.send_photo(chat_id=user_id, photo=tag_img, caption="Tagged image")
        else:
            # send photo with tag image as separate message
            await client.send_photo(chat_id=user_id, photo=character.get("img_url"), caption=dm_text)
            await client.send_photo(chat_id=user_id, photo=tag_img, caption="Tagged image")
    except Exception as e:
        LOGGER.warning("Failed to DM user after purchase: %s", e)
        dm_sent = False

    # Reply in the chat where purchase happened
    try:
        if dm_sent:
            await callback_query.answer("🎉 Purchase successful! Check your DM for details.")
            await callback_query.message.reply_text(f"🎉 {character.get('name')} has been added to <a href='tg://user?id={user_id}'>your collection</a>.", parse_mode="html")
        else:
            await callback_query.answer("🎉 Purchased, but I couldn't DM you. Please start the bot and try again.", show_alert=True)
            await callback_query.message.reply_text(
    f"🎉 {character.get('name')} added to your collection. "
    "I couldn't DM you — ask them to /start the bot so I can send the congratulations DM."
                                   )
    except Exception:
        # final fallback
        await callback_query.answer("Purchase processed.", show_alert=True)

# /add_market command for admins (same require_power decorator you used)
@app.on_message(filters.command("add_market"))
@require_power("add_character")
async def add_to_market(client, message):
    args = message.text.split()[1:]

    if len(args) != 2:
        await message.reply("🌌 Usage: /add_market <id> <price>")
        return

    character_id, price = args
    try:
        price = int(price)
    except ValueError:
        await message.reply("🚫 Price must be a number.")
        return

    character = await collection.find_one({"id": character_id})
    if not character:
        await message.reply("🚫 That character ID doesn't exist in your main collection.")
        return

    # Rarity check: only >= 6 allowed
    try:
        rarity = int(character.get("rarity", 0))
    except Exception:
        rarity = 0

    if rarity < 6:
        await message.reply("🚫 Market only accepts waifus with rarity 6 or higher.")
        return

    # set price and insert (don't remove from main collection)
    character_copy = dict(character)  # shallow copy
    character_copy["price"] = price
    # allow video in market (if the character has a 'video_url' or 'amv_url' field)
    # normalize to 'video_url' if an 'amv_url' exists
    if character_copy.get("amv_url") and not character_copy.get("video_url"):
        character_copy["video_url"] = character_copy.get("amv_url")

    await markets_collection.insert_one(character_copy)
    await message.reply(f"🎉 {character_copy.get('name')} has been added to the Market for {price} Star Coins!")
  
