# shop_pro_module.py
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

# IMPORT FROM YOUR BOT PACKAGE (assumes same names as your project)
from TEAMZYRO import app, db, user_collection, require_power, collection

# Constants - set your admin log chat id here (int). If None, admin logs disabled.
ADMIN_LOG_CHAT_ID = -1002891249230  # <-- set to your admin channel/group id e.g. -1001234567890

# Collections
shops_collection = db["shops"]

# In-memory state
user_state = {}         # user_id -> {"current_index": int, "shop_message_id": int}
pending_confirm = {}    # nonce -> {"user_id": int, "index": int, "expires": datetime}

# Logger
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("shop_pro")

# ---------------- Helpers ----------------
def is_video_url(url: str) -> bool:
    return url.lower().endswith((".mp4", ".mkv", ".webm", ".mov"))

async def cleanup_expired_items():
    """Delete expired shop items whose expires_at < now."""
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
    nonce = uuid.uuid4().hex  # unique per message

    keyboard = make_keyboard(current_index, nonce)

    # send photo or video support
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

    # store user state and pending nonce (valid for 2 minutes)
    user_state[user_id] = {"current_index": current_index, "shop_message_id": sent.message_id}
    pending_confirm[nonce] = {"user_id": user_id, "index": current_index, "expires": datetime.utcnow() + timedelta(minutes=2)}

# ---------------- Prepare Buy (Confirm modal) ----------------
@app.on_callback_query(filters.regex(r"^prepare_buy:"))
async def prepare_buy_cb(client, callback_query):
    data = callback_query.data.split(":")
    if len(data) != 3:
        await callback_query.answer("⚠️ Invalid action.", show_alert=True)
        return
    _, index_s, nonce = data
    try:
        index = int(index_s)
    except ValueError:
        await callback_query.answer("⚠️ Invalid index.", show_alert=True)
        return

    # validate nonce and owner
    info = pending_confirm.get(nonce)
    if not info or info["index"] != index:
        await callback_query.answer("⚠️ This purchase session expired. Open shop again.", show_alert=True)
        return

    if info["expires"] < datetime.utcnow():
        pending_confirm.pop(nonce, None)
        await callback_query.answer("⚠️ This purchase session expired. Try again.", show_alert=True)
        return

    if callback_query.from_user.id != info["user_id"]:
        await callback_query.answer("🚫 Only the original buyer can confirm this purchase.", show_alert=True)
        return

    # show confirm/cancel keyboard (edit message caption to show confirm prompt)
    try:
        await callback_query.message.edit_caption(
            caption=callback_query.message.caption + "\n\n🔔 Confirm your payment to complete purchase.",
            reply_markup=make_confirm_keyboard(nonce)
        )
    except Exception:
        # if media edit not possible, fallback to answering
        pass

    await callback_query.answer()  # silent

# ---------------- Buy Confirm ----------------
@app.on_callback_query(filters.regex(r"^buy_confirm:"))
async def buy_confirm_cb(client, callback_query):
    data = callback_query.data.split(":")
    if len(data) != 2:
        await callback_query.answer("⚠️ Invalid.", show_alert=True)
        return
    _, nonce = data
    info = pending_confirm.get(nonce)
    if not info:
        await callback_query.answer("⚠️ Session expired or invalid.", show_alert=True)
        return

    # ensure only buyer can confirm
    if callback_query.from_user.id != info["user_id"]:
        await callback_query.answer("🚫 Only the buyer can confirm.", show_alert=True)
        return

    # re-check expiry
    if info["expires"] < datetime.utcnow():
        pending_confirm.pop(nonce, None)
        await callback_query.answer("⚠️ Session expired. Try again.", show_alert=True)
        return

    index = info["index"]

    # reload shop items (clean expired & fresh fetch)
    await cleanup_expired_items()
    characters = await shops_collection.find().sort([("_id", 1)]).to_list(length=None)
    if index >= len(characters):
        pending_confirm.pop(nonce, None)
        await callback_query.answer("❌ This legend is no longer available.", show_alert=True)
        return

    character = characters[index]
    quantity = character.get("quantity", 1)
    if quantity <= 0:
        # remove and inform
        await shops_collection.delete_one({"_id": character["_id"]})
        pending_confirm.pop(nonce, None)
        await callback_query.answer("❌ This legend is SOLD OUT!", show_alert=True)
        return

    user_id = callback_query.from_user.id
    user = await user_collection.find_one({"id": user_id})
    if not user:
        await callback_query.answer("🚫 Register first to buy.", show_alert=True)
        return

    price = int(character.get("price", 0))
    balance = int(user.get("balance", 0))

    if balance < price:
        await callback_query.answer(f"💸 You need {price - balance} more Star Coins.", show_alert=True)
        return

    # perform DB updates atomically-ish
    # 1) deduct balance and push character to user
    purchased_item = {
        "_id": ObjectId(),
        "img_url": character["img_url"],
        "name": character.get("name"),
        "anime": character.get("anime"),
        "rarity": character.get("rarity"),
        "id": character.get("id")
    }

    # Update user: deduct balance, append character, update total_spent
    total_spent_inc = price
    await user_collection.update_one(
        {"id": user_id},
        {
            "$inc": {"balance": -price, "total_spent": total_spent_inc},
            "$push": {"characters": purchased_item}
        },
        upsert=False
    )

    # 2) decrement quantity or remove item
    if quantity > 1:
        await shops_collection.update_one({"_id": character["_id"]}, {"$inc": {"quantity": -1}})
        remaining = quantity - 1
    else:
        # delete the item
        await shops_collection.delete_one({"_id": character["_id"]})
        remaining = 0

    # Compose DM message
    dm_caption = (
        f"🎉 Congratulations — you claimed a new Legend! 🎉\n\n"
        f"**Name:** {character.get('name')}\n"
        f"**Rarity:** {character.get('rarity')}\n"
        f"**Price:** {price} Star Coins\n"
        f"**ID:** {character.get('id')}\n\n"
        f"💫 THANKS FOR SHOPPING IN GOJO CATCHER BOT 💫"
    )

    # Send DM (photo or video)
    try:
        if is_video_url(character["img_url"]):
            await client.send_video(user_id, video=character["img_url"], caption=dm_caption)
        else:
            await client.send_photo(user_id, photo=character["img_url"], caption=dm_caption)
    except Exception as e:
        LOGGER.warning("Failed to DM buyer: %s", e)

    # Popup confirmation
    await callback_query.answer("🎉 Payment successfully completed!", show_alert=True)

    # Edit original shop message caption to show success
    try:
        await callback_query.message.edit_caption("✅ Purchase complete! Check your DMs for details.")
    except Exception:
        pass

    # Admin log (if configured)
    try:
        if ADMIN_LOG_CHAT_ID:
            buyer_username = f"@{callback_query.from_user.username}" if callback_query.from_user.username else callback_query.from_user.first_name
            await client.send_message(
                ADMIN_LOG_CHAT_ID,
                f"🛒 Purchase Log:\nUser: {buyer_username} [{user_id}]\nItem: {character.get('name')} ({character.get('id')})\nPrice: {price}\nRemaining stock: {remaining}"
            )
    except Exception as e:
        LOGGER.warning("Failed to send admin log: %s", e)

    # Clean pending nonce
    pending_confirm.pop(nonce, None)

# ---------------- Buy Cancel ----------------
@app.on_callback_query(filters.regex(r"^buy_cancel:"))
async def buy_cancel_cb(client, callback_query):
    data = callback_query.data.split(":")
    if len(data) != 2:
        await callback_query.answer("⚠️ Invalid.", show_alert=True)
        return
    _, nonce = data
    info = pending_confirm.get(nonce)
    if not info:
        await callback_query.answer("⚠️ Session expired or invalid.", show_alert=True)
        return
    if callback_query.from_user.id != info["user_id"]:
        await callback_query.answer("🚫 Only the buyer can cancel.", show_alert=True)
        return

    # remove pending and restore original caption/buttons by reloading item if still exists
    pending_confirm.pop(nonce, None)
    await callback_query.answer("❌ Purchase cancelled.", show_alert=True)

    # Try to reload the shop item into the message (best-effort)
    await cleanup_expired_items()
    characters = await shops_collection.find().sort([("_id", 1)]).to_list(length=None)
    idx = info["index"]
    if 0 <= idx < len(characters):
        char = characters[idx]
        caption = make_shop_caption(char)
        keyboard = make_keyboard(idx, uuid.uuid4().hex)
        try:
            if is_video_url(char["img_url"]):
                await callback_query.message.edit_media(InputMediaVideo(media=char["img_url"], caption=caption), reply_markup=keyboard)
            else:
                await callback_query.message.edit_media(InputMediaPhoto(media=char["img_url"], caption=caption), reply_markup=keyboard)
        except Exception:
            pass

# ---------------- Next & Close ----------------
@app.on_callback_query(filters.regex(r"^next_shop$"))
async def next_shop_cb(client, callback_query):
    user_id = callback_query.from_user.id
    await cleanup_expired_items()
    characters = await shops_collection.find().sort([("_id", 1)]).to_list(length=None)
    if not characters:
        await callback_query.answer("🌌 No items left in the Bazaar.", show_alert=True)
        return

    state = user_state.get(user_id, {"current_index": 0})
    current_index = state.get("current_index", 0)
    next_index = (current_index + 1) % len(characters)
    char = characters[next_index]
    caption = make_shop_caption(char)
    nonce = uuid.uuid4().hex
    keyboard = make_keyboard(next_index, nonce)

    # edit media
    try:
        if is_video_url(char["img_url"]):
            await callback_query.message.edit_media(InputMediaVideo(media=char["img_url"], caption=caption), reply_markup=keyboard)
        else:
            await callback_query.message.edit_media(InputMediaPhoto(media=char["img_url"], caption=caption), reply_markup=keyboard)
    except Exception as e:
        LOGGER.warning("Failed to edit media in next: %s", e)
        await callback_query.message.edit_caption(caption, reply_markup=keyboard)

    user_state[user_id] = {"current_index": next_index, "shop_message_id": callback_query.message.message_id}
    pending_confirm[nonce] = {"user_id": user_id, "index": next_index, "expires": datetime.utcnow() + timedelta(minutes=2)}
    await callback_query.answer()

@app.on_callback_query(filters.regex(r"^close_shop$"))
async def close_shop_cb(client, callback_query):
    try:
        await callback_query.message.delete()
    except Exception:
        pass
    await callback_query.answer("🛑 Shop closed.")

# ---------------- Add to Shop (with quantity & optional expiry minutes) ----------------
@app.on_message(filters.command("addshop"))
@require_power("add_character")
async def add_to_shop_cmd(client, message):
    # Usage: /addshop <id> <price> <quantity> [expiry_minutes]
    args = message.text.split()[1:]
    if len(args) < 3:
        await message.reply_text("Usage: /addshop [id] [price] [quantity] [expiry_minutes]")
        return

    char_id = args[0]
    try:
        price = int(args[1])
        quantity = int(args[2])
    except ValueError:
        await message.reply_text("Price and quantity must be numbers.")
        return

    expiry_minutes = int(args[3]) if len(args) >= 4 else None

    # fetch character data from 'collection' (assumed existing)
    character = await collection.find_one({"id": char_id})
    if not character:
        await message.reply_text("🚫 Character not found in the source collection.")
        return

    # prepare shop doc
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
    if expiry_minutes:
        shop_doc["expires_at"] = datetime.utcnow() + timedelta(minutes=expiry_minutes)

    await shops_collection.insert_one(shop_doc)
    await message.reply_text(f"✅ {character.get('name')} added to shop for {price} coins. Stock: {quantity}.")

# ---------------- Top Buyers Leaderboard ----------------
@app.on_message(filters.command("topbuyers"))
async def topbuyers_cmd(client, message):
    # aggregate top by total_spent (fallback to scanning if field absent)
    cursor = user_collection.find().sort([("total_spent", -1)]).limit(10)
    top = await cursor.to_list(length=10)
    if not top:
        await message.reply_text("No purchases yet.")
        return

    text = "🏆 Top Buyers Leaderboard\n\n"
    for i, u in enumerate(top, start=1):
        name = u.get("username") or u.get("name") or f"{u.get('id')}"
        text += f"{i}. {name} — Spent: {u.get('total_spent', 0)} coins\n"

    await message.reply_text(text)

# ---------------- Periodic cleanup task (optional) ----------------
# If you want background cleanup of expired pending_confirm keys, run this on startup.
async def _cleanup_pending_task():
    while True:
        now = datetime.utcnow()
        to_remove = [k for k,v in pending_confirm.items() if v["expires"] < now]
        for k in to_remove:
            pending_confirm.pop(k, None)
        await asyncio.sleep(30)

# Start cleanup task when app starts
@app.on_started
async def _on_started(client):
    client.loop.create_task(_cleanup_pending_task())
    LOGGER.info("Shop module started and cleanup task running.")
  
