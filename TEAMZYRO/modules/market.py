import urllib.request
from TEAMZYRO import ZYRO as bot, db, user_collection
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

market_collection = db["market"]

user_data = {}
market_data = {}

@bot.on_message(filters.command(["market", "hmarket"]))
async def show_market(client, message):
    user_id = message.from_user.id
    message_id = message.id

    items_cursor = market_collection.find()
    items = await items_cursor.to_list(length=None)

    if not items:
        await message.reply("🛒 The Galactic Market is empty! No waifu or AMV for sale yet.")
        return

    current_index = 0
    item = items[current_index]

    caption_message = (
        f"🛍️ **Welcome to the Galactic Market!** 🛍️\n\n"
        f"**Name:** {item['name']}\n"
        f"**Realm:** {item['anime']}\n"
        f"**Rarity:** {item['rarity']}\n"
        f"**Price:** {item['price']} Star Coins\n"
        f"**ID:** {item['id']}\n"
        f"**Available:** {item['quantity']} left\n"
    )

    keyboard = [
        [InlineKeyboardButton("Buy Now!", callback_data=f"marketbuy_{current_index}"),
         InlineKeyboardButton("Next Item", callback_data="marketnext")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if item.get("is_video"):
        await message.reply_video(
            video=item["url"],
            caption=caption_message,
            reply_markup=reply_markup
        )
    else:
        await message.reply_photo(
            photo=item["url"],
            caption=caption_message,
            reply_markup=reply_markup
        )

    market_data[user_id] = {"current_index": current_index, "market_message_id": message_id}


@bot.on_callback_query(filters.regex(r"^marketbuy_\d+$"))
async def buy_market_item(client, callback_query):
    user_id = callback_query.from_user.id
    current_index = int(callback_query.data.split("_")[1])

    items_cursor = market_collection.find()
    items = await items_cursor.to_list(length=None)

    if current_index >= len(items):
        await callback_query.answer("🚫 This item is no longer in the Market!", show_alert=True)
        return

    item = items[current_index]

    user = await user_collection.find_one({"id": user_id})
    if not user:
        await callback_query.answer("🚫 Please register before buying from the Market!", show_alert=True)
        return

    price = item['price']
    balance = user.get("balance", 0)

    if balance < price:
        await callback_query.answer(
            f"💸 Not enough Star Coins! You need {price - balance} more.",
            show_alert=True
        )
        return

    # Deduct balance
    new_balance = balance - price

    # Reduce quantity
    new_quantity = item["quantity"] - 1

    if new_quantity <= 0:
        await market_collection.delete_one({"_id": item["_id"]})
    else:
        await market_collection.update_one(
            {"_id": item["_id"]},
            {"$set": {"quantity": new_quantity}}
        )

    # Add to user collection
    character_data = {
        "_id": ObjectId(),
        "url": item["url"],
        "name": item["name"],
        "anime": item["anime"],
        "rarity": item["rarity"],
        "id": item["id"],
        "is_video": item.get("is_video", False)
    }
    user["characters"].append(character_data)

    await user_collection.update_one(
        {"id": user_id},
        {"$set": {"balance": new_balance, "characters": user["characters"]}}
    )

    # Popup
    await callback_query.answer(
        f"🎉 Payment Successfully Completed!\nCheck your DM 📩\nRemaining Balance: {new_balance} ⭐",
        show_alert=True
    )

    # Send DM with receipt
    try:
        caption = (
            "╔════════════════════╗\n"
            "   ✨ **ＰＡＹＭＥＮＴ ＲＥＣＥＩＶＥＤ** ✨\n"
            "╚════════════════════╝\n\n"
            f"🎀 You claimed: **{item['name']}**\n"
            f"🌌 From: {item['anime']}\n"
            f"💎 Rarity: {item['rarity']}\n\n"
            "Thanks for shopping in **ɢᴏᴊᴏ ᴄᴀᴛᴄʜᴇʀ ʙᴏᴛ**!\n"
            "✨ Your waifu has been added to your collection!"
        )
        if item.get("is_video"):
            await client.send_video(user_id, video=item["url"], caption=caption)
        else:
            await client.send_photo(user_id, photo=item["url"], caption=caption)
    except Exception as e:
        logging.error(f"Failed to send DM: {e}")


@bot.on_callback_query(filters.regex("^marketnext$"))
async def next_market_item(client, callback_query):
    user_id = callback_query.from_user.id
    user_state = market_data.get(user_id, {})
    current_index = user_state.get("current_index", 0)

    items_cursor = market_collection.find()
    items = await items_cursor.to_list(length=None)

    if not items:
        await callback_query.answer("🛒 The Galactic Market is empty now!", show_alert=True)
        return

    next_index = (current_index + 1) % len(items)
    item = items[next_index]

    caption_message = (
        f"🛍️ **Browse the Galactic Market!** 🛍️\n\n"
        f"**Name:** {item['name']}\n"
        f"**Realm:** {item['anime']}\n"
        f"**Rarity:** {item['rarity']}\n"
        f"**Price:** {item['price']} Star Coins\n"
        f"**ID:** {item['id']}\n"
        f"**Available:** {item['quantity']} left\n"
    )

    keyboard = [
        [InlineKeyboardButton("Buy Now!", callback_data=f"marketbuy_{next_index}"),
         InlineKeyboardButton("Next Item", callback_data="marketnext")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if item.get("is_video"):
        await callback_query.message.edit_media(
            media=InputMediaVideo(media=item['url'], caption=caption_message),
            reply_markup=reply_markup
        )
    else:
        await callback_query.message.edit_media(
            media=InputMediaPhoto(media=item['url'], caption=caption_message),
            reply_markup=reply_markup
        )

    market_data[user_id]["current_index"] = next_index
    await callback_query.answer()


@bot.on_message(filters.command("addmarket"))
@require_power("add_character")
async def add_to_market(client, message):
    args = message.text.split()[1:]

    if len(args) != 3:
        await message.reply("🛒 Usage: /addmarket [id] [price] [quantity]")
        return

    character_id, price, qty = args

    try:
        price = int(price)
        qty = int(qty)
    except ValueError:
        await message.reply("🚫 Price and Quantity must be numbers!")
        return

    character = await collection.find_one({"id": character_id})
    if not character:
        await message.reply("🚫 This character/AMV doesn't exist in DB!")
        return

    market_item = {
        "id": character["id"],
        "name": character["name"],
        "anime": character["anime"],
        "rarity": character["rarity"],
        "url": character["img_url"] if "img_url" in character else character["video_url"],
        "is_video": "video_url" in character,
        "price": price,
        "quantity": qty
    }

    await market_collection.insert_one(market_item)

    await message.reply(
        f"🎉 {character['name']} has been added to the Market for {price} ⭐ (x{qty} available)"
  )

@bot.on_message(filters.command("mymarket"))
async def my_market_history(client, message):
    user_id = message.from_user.id
    user = await user_collection.find_one({"id": user_id})

    if not user or "characters" not in user or not user["characters"]:
        await message.reply("📭 You haven't purchased anything from the Galactic Market yet!")
        return

    # Filter only Market purchases
    market_items = [c for c in user["characters"] if c.get("from_market", False)]

    if not market_items:
        await message.reply("🛒 You haven't claimed any waifu/AMV from the Market yet!")
        return

    current_index = 0
    item = market_items[current_index]

    caption = (
        f"🛍️ **Your Market Purchase** 🛍️\n\n"
        f"**Name:** {item['name']}\n"
        f"🌌 From: {item['anime']}\n"
        f"💎 Rarity: {item['rarity']}\n"
        f"📦 ID: {item['id']}\n"
        f"({current_index+1}/{len(market_items)})"
    )

    keyboard = [
        [
            InlineKeyboardButton("⬅️ Prev", callback_data="mymarket_prev"),
            InlineKeyboardButton("➡️ Next", callback_data="mymarket_next")
        ],
        [InlineKeyboardButton("❌ Close", callback_data="mymarket_close")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if item.get("is_video"):
        sent = await message.reply_video(
            video=item["url"],
            caption=caption,
            reply_markup=reply_markup
        )
    else:
        sent = await message.reply_photo(
            photo=item["url"],
            caption=caption,
            reply_markup=reply_markup
        )

    mymarket_data[user_id] = {"index": current_index, "items": market_items, "msg_id": sent.id}


async def update_mymarket_view(callback_query, direction):
    user_id = callback_query.from_user.id
    state = mymarket_data.get(user_id)

    if not state:
        await callback_query.answer("⚠️ Please use /mymarket again!", show_alert=True)
        return

    items = state["items"]
    current_index = state["index"]

    if direction == "next":
        current_index = (current_index + 1) % len(items)
    elif direction == "prev":
        current_index = (current_index - 1) % len(items)

    item = items[current_index]

    caption = (
        f"🛍️ **Your Market Purchase** 🛍️\n\n"
        f"**Name:** {item['name']}\n"
        f"🌌 From: {item['anime']}\n"
        f"💎 Rarity: {item['rarity']}\n"
        f"📦 ID: {item['id']}\n"
        f"({current_index+1}/{len(items)})"
    )

    keyboard = [
        [
            InlineKeyboardButton("⬅️ Prev", callback_data="mymarket_prev"),
            InlineKeyboardButton("➡️ Next", callback_data="mymarket_next")
        ],
        [InlineKeyboardButton("❌ Close", callback_data="mymarket_close")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if item.get("is_video"):
        await callback_query.message.edit_media(
            media=InputMediaVideo(media=item['url'], caption=caption),
            reply_markup=reply_markup
        )
    else:
        await callback_query.message.edit_media(
            media=InputMediaPhoto(media=item['url'], caption=caption),
            reply_markup=reply_markup
        )

    mymarket_data[user_id]["index"] = current_index
    await callback_query.answer()


@bot.on_callback_query(filters.regex("^mymarket_next$"))
async def mymarket_next(client, callback_query):
    await update_mymarket_view(callback_query, "next")


@bot.on_callback_query(filters.regex("^mymarket_prev$"))
async def mymarket_prev(client, callback_query):
    await update_mymarket_view(callback_query, "prev")


@bot.on_callback_query(filters.regex("^mymarket_close$"))
async def mymarket_close(client, callback_query):
    user_id = callback_query.from_user.id
    try:
        await callback_query.message.delete()
    except:
        pass
    mymarket_data.pop(user_id, None)
    await callback_query.answer("❌ Closed view", show_alert=False)
  
