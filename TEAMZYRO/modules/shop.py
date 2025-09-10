# store_module_working.py
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
ADMIN_LOG_CHAT_ID = -1002891249230  # Optional: admin log channel
Store_collection = db["store"]
user_state = {}         # user_id -> {"current_index": int, "shop_message_id": int}
pending_confirm = {}    # nonce -> {"user_id": int, "index": int, "expires": datetime}

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("store_module_working")

# ---------------- Helpers ----------------
def is_video_url(url: str) -> bool:
    return url.lower().endswith((".mp4", ".mkv", ".webm", ".mov"))

async def cleanup_expired_items():
    now = datetime.utcnow()
    await Store_collection.delete_many({"expires_at": {"$lte": now}})

def make_store_caption(character: dict) -> str:
    stock = character.get("quantity", 1)
    price = character.get("price", 0)
    return (
        f"🌟 **Cosmic Store** 🌟\n\n"
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
            InlineKeyboardButton("➡️ Next", callback_data=f"next_store")
        ],
        [
            InlineKeyboardButton("❌ Close", callback_data=f"close_store")
        ]
    ])

def make_confirm_keyboard(nonce: str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"buy_confirm:{nonce}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"buy_cancel:{nonce}")
        ]
    ])

# ---------------- Store Command ----------------
@app.on_message(filters.command(["store", "storemenu", "hstore"]))
async def show_store(client, message):
    user_id = message.from_user.id
    await cleanup_expired_items()

    characters = await Store_collection.find().sort([("_id", 1)]).to_list(length=None)
    if not characters:
        return await message.reply_text("🌌 The Cosmic Store is empty! No items available right now.")

    current_index = 0
    character = characters[current_index]

    caption = make_store_caption(character)
    nonce = uuid.uuid4().hex[:8]  # short nonce
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
        LOGGER.exception("Failed to send store item media: %s", e)
        return await message.reply_text("⚠️ Failed to display item (broken media).")

    user_state[user_id] = {"current_index": current_index, "shop_message_id": sent.message_id}
    pending_confirm[nonce] = {"user_id": user_id, "index": current_index, "expires": datetime.utcnow() + timedelta(minutes=2)}

# ---------------- Single Callback Handler ----------------
@app.on_callback_query()
async def store_callbacks(client, cq):
    data = cq.data
    user_id = cq.from_user.id

    LOGGER.info(f"Callback received: {data} from user {user_id}")

    # ---------------- Prepare Buy ----------------
    if data.startswith("prepare_buy:"):
        try:
            _, index_s, nonce = data.split(":")
            index = int(index_s)
        except:
            return await cq.answer("⚠️ Invalid action.", show_alert=True)

        info = pending_confirm.get(nonce)
        if not info or info["index"] != index:
            return await cq.answer("⚠️ Session expired.", show_alert=True)
        if info["expires"] < datetime.utcnow():
            pending_confirm.pop(nonce, None)
            return await cq.answer("⚠️ Session expired.", show_alert=True)
        if user_id != info["user_id"]:
            return await cq.answer("🚫 Only buyer can confirm.", show_alert=True)

        try:
            await cq.message.edit_caption(
                caption=cq.message.caption + "\n\n🔔 Confirm your payment to complete purchase.",
                reply_markup=make_confirm_keyboard(nonce)
            )
        except Exception as e:
            LOGGER.exception("Failed to show confirm keyboard: %s", e)
            return await cq.answer("⚠️ Something went wrong.", show_alert=True)

        return await cq.answer()

    # ---------------- Confirm Buy ----------------
    elif data.startswith("buy_confirm:"):
        try:
            _, nonce = data.split(":")
            info = pending_confirm.get(nonce)
            if not info: return await cq.answer("⚠️ Session expired.", show_alert=True)
            if user_id != info["user_id"]: return await cq.answer("🚫 Only buyer can confirm.", show_alert=True)
            if info["expires"] < datetime.utcnow(): pending_confirm.pop(nonce,None); return await cq.answer("⚠️ Session expired.", show_alert=True)

            index = info["index"]
            await cleanup_expired_items()
            characters = await Store_collection.find().sort([("_id",1)]).to_list(length=None)
            if index >= len(characters): pending_confirm.pop(nonce,None); return await cq.answer("❌ No longer available.", show_alert=True)

            character = characters[index]
            quantity = character.get("quantity",1)
            if quantity <=0:
                await Store_collection.delete_one({"_id": character["_id"]})
                pending_confirm.pop(nonce,None)
                return await cq.answer("❌ SOLD OUT!", show_alert=True)

            user = await user_collection.find_one({"id": user_id})
            if not user: return await cq.answer("🚫 Register first.", show_alert=True)
            price = int(character.get("price",0))
            balance = int(user.get("balance",0))
            if balance < price: return await cq.answer(f"💸 Need {price-balance} more coins.", show_alert=True)

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
                await Store_collection.update_one({"_id": character["_id"]},{"$inc":{"quantity":-1}})
                remaining = quantity-1
            else:
                await Store_collection.delete_one({"_id": character["_id"]})
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

            await cq.answer("🎉 Payment successfully completed!", show_alert=True)
            await cq.message.edit_caption("✅ Purchase complete! Check your DMs.", reply_markup=None)

            if ADMIN_LOG_CHAT_ID:
                try:
                    uname = f"@{cq.from_user.username}" if cq.from_user.username else cq.from_user.first_name
                    await client.send_message(ADMIN_LOG_CHAT_ID,
                        f"🛒 Purchase Log:\nUser: {uname} [{user_id}]\nItem: {character.get('name')} ({character.get('id')})\nPrice: {price}\nRemaining stock: {remaining}"
                    )
                except: pass

            pending_confirm.pop(nonce,None)
        except Exception as e:
            LOGGER.exception("Confirm buy failed: %s", e)
            return await cq.answer("⚠️ Could not complete purchase.", show_alert=True)

    # ---------------- Cancel Buy ----------------
    elif data.startswith("buy_cancel:"):
        try:
            _, nonce = data.split(":")
            info = pending_confirm.get(nonce)
            if not info: return await cq.answer("⚠️ Session expired.", show_alert=True)
            if user_id != info["user_id"]: return await cq.answer("🚫 Only buyer can cancel.", show_alert=True)
            pending_confirm.pop(nonce,None)
            await cq.answer("❌ Purchase cancelled.", show_alert=True)
            await cq.message.edit_caption("❌ Purchase cancelled.", reply_markup=None)
        except Exception as e:
            LOGGER.exception("Cancel buy failed: %s", e)

    # ---------------- Next ----------------
    elif data == "next_store":
        try:
            await cleanup_expired_items()
            characters = await Store_collection.find().sort([("_id",1)]).to_list(length=None)
            if not characters: return await cq.answer("🌌 No items left.", show_alert=True)

            state = user_state.get(user_id,{"current_index":0})
            current_index = state.get("current_index",0)
            next_index = (current_index+1) % len(characters)
            char = characters[next_index]

            caption = make_store_caption(char)
            nonce = uuid.uuid4().hex[:8]
            keyboard = make_keyboard(next_index, nonce)

            if is_video_url(char["img_url"]):
                await cq.message.edit_media(InputMediaVideo(media=char["img_url"],caption=caption), reply_markup=keyboard)
            else:
                await cq.message.edit_media(InputMediaPhoto(media=char["img_url"],caption=caption), reply_markup=keyboard)

            user_state[user_id] = {"current_index": next_index, "shop_message_id": cq.message.message_id}
            pending_confirm[nonce] = {"user_id": user_id, "index": next_index, "expires": datetime.utcnow()+timedelta(minutes=2)}
            await cq.answer()
        except Exception as e:
            LOGGER.exception("Next button failed: %s", e)
            await cq.answer("⚠️ Could not show next item.", show_alert=True)

    # ---------------- Close ----------------
    elif data == "close_store":
        try:
            await cq.message.delete()
        except Exception as e:
            LOGGER.warning("Failed to delete store message: %s", e)
        user_state.pop(user_id,None)
        await cq.answer("Store closed.", show_alert=False)

    else:
        await cq.answer("⚠️ Unknown action.", show_alert=True)

# ---------------- Add to Store ----------------
@app.on_message(filters.command("addstore"))
@require_power("add_character")
async def add_to_store_cmd(client, message):
    args = message.text.split()[1:]
    if len(args) < 3:
        return await message.reply_text("Usage: /addstore [id] [price] [quantity] [expiry_minutes]")

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

    await Store_collection.insert_one(shop_doc)
    await message.reply_text(f"✅ **{character.get('name')}** added to store for {price} coins. Stock: {quantity}.")

# ---------------- Cleanup Task ----------------
async def _cleanup_pending_task():
    while True:
        now = datetime.utcnow()
        to_remove = [k for k,v in pending_confirm.items() if v["expires"] < now]
        for k in to_remove:
            pending_confirm.pop(k, None)
        await asyncio.sleep(30)

@app.on_message(filters.private)
async def _on_started(client, message):
    if not hasattr(client, "_cleanup_started"):
        client.loop.create_task(_cleanup_pending_task())
        client._cleanup_started = True
        LOGGER.info("✅ Store module cleanup task running.")
        
