# shop_pro_module_fixed_v2.py
import uuid
import logging
from datetime import datetime, timedelta
import asyncio

from pymongo import ReturnDocument
from bson import ObjectId

from pyrogram import filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
    InputMediaVideo,
)

from TEAMZYRO import app, db, user_collection, require_power, collection

# ---------------- Config ----------------
ADMIN_LOG_CHAT_ID = -1002891249230 # Optional: admin log channel

shops_collection = db["shops"]
user_state = {}         # user_id -> {"current_index": int, "shop_message_id": int}
pending_confirm = {}    # nonce -> {"user_id": int, "index": int, "expires": datetime}

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("shop_pro_fixed_v2")

# ---------------- Helpers ----------------
def is_video_url(url: str) -> bool:
    return url.lower().endswith((".mp4", ".mkv", ".webm", ".mov"))

async def cleanup_expired_items():
    now = datetime.utcnow()
    await shops_collection.delete_many({"expires_at": {"$lte": now}})

def make_shop_caption(character: dict) -> str:
    stock = character.get("quantity", 1)
    price = character.get("price", 0)
    return (
        f"🌟 **Cosmic Bazaar** 🌟\n\n"
        f"**Hero:** {character.get('name','Unknown')}\n"
        f"**Realm:** {character.get('anime','Unknown')}\n"
        f"**Legend Tier:** {character.get('rarity','Common')}\n"
        f"**Price:** {price} Star Coins\n"
        f"**Stock:** {stock} left\n"
        f"**ID:** {character.get('id','-')}\n\n"
        f"✨ Grab your legend now!"
    )

def make_keyboard(index: int, nonce: str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💳 Claim Now", callback_data=f"prepare_buy:{index}:{nonce}"),
            InlineKeyboardButton("➡️ Next", callback_data="next_shop")
        ],
        [
            InlineKeyboardButton("❌ Close", callback_data="close_shop")
        ]
    ])

def make_confirm_keyboard(nonce: str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"buy_confirm:{nonce}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"buy_cancel:{nonce}")
        ]
    ])

# ---------------- Shop Command ----------------
@app.on_message(filters.command(["shop", "hshopmenu", "hshop"]))
async def show_shop(client, message):
    user_id = message.from_user.id
    await cleanup_expired_items()

    characters_cursor = shops_collection.find().sort([("_id", 1)])
    characters = await characters_cursor.to_list(length=None)
    if not characters:
        await message.reply_text("🌌 The Cosmic Bazaar is empty! No items available right now.")
        return

    current_index = 0
    character = characters[current_index]

    caption = make_shop_caption(character)
    nonce = uuid.uuid4().hex
    keyboard = make_keyboard(current_index, nonce)

    try:
        if is_video_url(character["img_url"]):
            sent = await message.reply_video(
                video=character["img_url"],
                caption=caption,
                reply_markup=keyboard
            )
        else:
            sent = await message.reply_photo(
                photo=character["img_url"],
                caption=caption,
                reply_markup=keyboard
            )
    except Exception as e:
        LOGGER.exception("Failed to send shop item media: %s", e)
        await message.reply_text("⚠️ Failed to display item (broken media).")
        return

    user_state[user_id] = {"current_index": current_index, "shop_message_id": sent.message_id}
    pending_confirm[nonce] = {"user_id": user_id, "index": current_index, "expires": datetime.utcnow() + timedelta(minutes=2)}

# ---------------- Callback Handlers ----------------
@app.on_callback_query(filters.regex(r"^prepare_buy:"))
async def prepare_buy_cb(client, callback_query):
    data = callback_query.data.split(":")
    if len(data) != 3:
        return await callback_query.answer("⚠️ Invalid action.", show_alert=True)
    _, index_s, nonce = data
    try: index = int(index_s)
    except ValueError: return await callback_query.answer("⚠️ Invalid index.", show_alert=True)

    info = pending_confirm.get(nonce)
    if not info or info["index"] != index:
        return await callback_query.answer("⚠️ Session expired.", show_alert=True)
    if info["expires"] < datetime.utcnow():
        pending_confirm.pop(nonce, None)
        return await callback_query.answer("⚠️ Session expired.", show_alert=True)
    if callback_query.from_user.id != info["user_id"]:
        return await callback_query.answer("🚫 Only buyer can confirm.", show_alert=True)

    try:
        await callback_query.message.edit_caption(
            caption=callback_query.message.caption + "\n\n🔔 Confirm your payment to complete purchase.",
            reply_markup=make_confirm_keyboard(nonce)
        )
    except: pass
    await callback_query.answer()

@app.on_callback_query(filters.regex(r"^buy_confirm:"))
async def buy_confirm_cb(client, callback_query):
    data = callback_query.data.split(":")
    if len(data)!=2: return await callback_query.answer("⚠️ Invalid.", show_alert=True)
    _, nonce = data

    info = pending_confirm.get(nonce)
    if not info: return await callback_query.answer("⚠️ Session expired.", show_alert=True)
    if callback_query.from_user.id != info["user_id"]: return await callback_query.answer("🚫 Only buyer can confirm.", show_alert=True)
    if info["expires"] < datetime.utcnow(): pending_confirm.pop(nonce, None); return await callback_query.answer("⚠️ Session expired.", show_alert=True)

    index = info["index"]
    await cleanup_expired_items()
    characters = await shops_collection.find().sort([("_id", 1)]).to_list(length=None)
    if index >= len(characters):
        pending_confirm.pop(nonce, None)
        return await callback_query.answer("❌ No longer available.", show_alert=True)

    character = characters[index]
    quantity = character.get("quantity",1)
    if quantity <=0:
        await shops_collection.delete_one({"_id": character["_id"]})
        pending_confirm.pop(nonce,None)
        return await callback_query.answer("❌ SOLD OUT!", show_alert=True)

    user_id = callback_query.from_user.id
    user = await user_collection.find_one({"id": user_id})
    if not user: return await callback_query.answer("🚫 Register first.", show_alert=True)

    price = int(character.get("price",0))
    balance = int(user.get("balance",0))
    if balance < price: return await callback_query.answer(f"💸 Need {price-balance} more coins.", show_alert=True)

    purchased_item = {
        "_id": ObjectId(),
        "img_url": character["img_url"],
        "name": character.get("name"),
        "anime": character.get("anime"),
        "rarity": character.get("rarity"),
        "id": character.get("id")
    }

    await user_collection.update_one(
        {"id": user_id},
        {"$inc": {"balance": -price, "total_spent": price}, "$push": {"characters": purchased_item}}
    )

    if quantity > 1:
        await shops_collection.update_one({"_id": character["_id"]},{"$inc":{"quantity":-1}})
        remaining = quantity-1
    else:
        await shops_collection.delete_one({"_id": character["_id"]})
        remaining=0

    dm_caption = (
        f"🎉 **Congratulations!** 🎉\n\n"
        f"**Name:** {character.get('name')}\n"
        f"**Rarity:** {character.get('rarity')}\n"
        f"**Price:** {price} Star Coins\n"
        f"**ID:** {character.get('id')}\n\n"
        f"💫 THANKS FOR SHOPPING IN GOJO CATCHER BOT 💫"
    )

    try:
        if is_video_url(character["img_url"]): await client.send_video(user_id, video=character["img_url"], caption=dm_caption)
        else: await client.send_photo(user_id, photo=character["img_url"], caption=dm_caption)
    except: LOGGER.warning("DM failed: %s", character["name"])

    await callback_query.answer("🎉 Payment successfully completed!", show_alert=True)
    try: await callback_query.message.edit_caption("✅ Purchase complete! Check your DMs.", reply_markup=None)
    except: pass

    if ADMIN_LOG_CHAT_ID:
        try:
            uname = f"@{callback_query.from_user.username}" if callback_query.from_user.username else callback_query.from_user.first_name
            await client.send_message(ADMIN_LOG_CHAT_ID,
                f"🛒 Purchase Log:\nUser: {uname} [{user_id}]\nItem: {character.get('name')} ({character.get('id')})\nPrice: {price}\nRemaining stock: {remaining}"
            )
        except: pass

    pending_confirm.pop(nonce,None)

@app.on_callback_query(filters.regex(r"^buy_cancel:"))
async def buy_cancel_cb(client, callback_query):
    data = callback_query.data.split(":")
    if len(data)!=2: return await callback_query.answer("⚠️ Invalid.", show_alert=True)
    _, nonce = data
    info = pending_confirm.get(nonce)
    if not info: return await callback_query.answer("⚠️ Session expired.", show_alert=True)
    if callback_query.from_user.id != info["user_id"]: return await callback_query.answer("🚫 Only buyer can cancel.", show_alert=True)
    pending_confirm.pop(nonce,None)
    await callback_query.answer("❌ Purchase cancelled.", show_alert=True)
    try: await callback_query.message.edit_caption("❌ Purchase cancelled.", reply_markup=None)
    except: pass

@app.on_callback_query(filters.regex(r"^next_shop$"))
async def next_shop_cb(client, callback_query):
    user_id = callback_query.from_user.id
    await cleanup_expired_items()
    characters = await shops_collection.find().sort([("_id",1)]).to_list(length=None)
    if not characters: return await callback_query.answer("🌌 No items left.", show_alert=True)
    state = user_state.get(user_id,{"current_index":0})
    current_index = state.get("current_index",0)
    next_index = (current_index+1)%len(characters)
    char = characters[next_index]
    caption = make_shop_caption(char)
    nonce = uuid.uuid4().hex
    keyboard = make_keyboard(next_index, nonce)
    try:
        if is_video_url(char["img_url"]): await callback_query.message.edit_media(InputMediaVideo(media=char["img_url"],caption=caption), reply_markup=keyboard)
        else: await callback_query.message.edit_media(InputMediaPhoto(media=char["img_url"],caption=caption), reply_markup=keyboard)
    except: await callback_query.message.edit_caption(caption, reply_markup=keyboard)
    user_state[user_id] = {"current_index":next_index,"shop_message_id":callback_query.message.message_id}
    pending_confirm[nonce] = {"user_id":user_id,"index":next_index,"expires":datetime.utcnow()+timedelta(minutes=2)}
    await callback_query.answer()

@app.on_callback_query(filters.regex(r"^close_shop$"))
async def close_shop_cb(client, callback_query):
    try: await callback_query.message.delete()
    except: pass
    user_state.pop(callback_query.from_user.id,None)
    await callback_query.answer("Shop closed.", show_alert=False)

# ---------------- Add to Shop ----------------
@app.on_message(filters.command("addshop"))
@require_power("add_character")
async def add_to_shop_cmd(client, message):
    args = message.text.split()[1:]
    if len(args) < 3:
        return await message.reply_text("Usage: /addshop [id] [price] [quantity] [expiry_minutes]")

    char_id = args[0]
    try:
        price = int(args[1])
        quantity = int(args[2])
    except ValueError:
        return await message.reply_text("Price and quantity must be numbers.")

    expiry_minutes = int(args[3]) if len(args) >= 4 else None
    character = await collection.find_one({"id": char_id})
    if not character: return await message.reply_text("🚫 Character not found in the source collection.")

    shop_doc = {
        "img_url": character.get("img_url"),
        "name": character.get("name"),
        "anime": character.get("anime"),
        "rarity": character.get("rarity"),
        "id": character.get("id"),
        "price": price,
        "quantity": quantity,
        "added_at": datetime.utcnow()
    }
    if expiry_minutes: shop_doc["expires_at"] = datetime.utcnow() + timedelta(minutes=expiry_minutes)
    await shops_collection.insert_one(shop_doc)
    await message.reply_text(f"✅ **{character.get('name')}** added to shop for {price} coins. Stock: {quantity}.")

# ---------------- Top Buyers Leaderboard ----------------
@app.on_message(filters.command("topbuyers"))
async def topbuyers_cmd(client, message):
    cursor = user_collection.find().sort([("total_spent", -1)]).limit(10)
    top = await cursor.to_list(length=10)
    if not top: return await message.reply_text("No purchases yet.")

    text = "🏆 **Top Buyers Leaderboard** 🏆\n\n"
    buttons = []
    for i, u in enumerate(top, start=1):
        name = u.get("name") or u.get("username") or str(u.get("id"))
        name = f"**{name}**"
        spent = u.get("total_spent",0)
        avatar = u.get("profile_pic")  # optional, if you store profile pics
        text += f"{i}. {name} — Spent: {spent} coins\n"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Close", callback_data="close_shop")]])
    await message.reply_text(text, reply_markup=keyboard, disable_web_page_preview=True)

# ---------------- Cleanup Task ----------------
async def _cleanup_pending_task():
    while True:
        now = datetime.utcnow()
        to_remove = [k for k,v in pending_confirm.items() if v["expires"] < now]
        for k in to_remove:
            pending_confirm.pop(k, None)
        await asyncio.sleep(30)

@app.on_message()
async def _on_started(client):
    client.loop.create_task(_cleanup_pending_task())
    LOGGER.info("Shop module started and cleanup task running.")
