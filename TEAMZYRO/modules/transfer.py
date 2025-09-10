import random
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from TEAMZYRO import ZYRO as bot, user_collection, require_power

TRANSFER_IMAGES = [
    "https://files.catbox.moe/xokoit.jpg",
    "https://files.catbox.moe/6w5fl4.jpg",
    "https://files.catbox.moe/syanmk.jpg"
]

# Step 1: Command
@bot.on_message(filters.command("transfer"))
@require_power("VIP")
async def transfer_collection(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("⚠️ Usage: `/transfer user_id`", quote=True)
        return

    target_id = int(message.command[1])
    sender_id = message.from_user.id

    # Check sender
    sender = await user_collection.find_one({"id": sender_id})
    if not sender:
        await message.reply_text("❌ You don't have a collection to transfer.")
        return

    # Check target
    target = await user_collection.find_one({"id": target_id})
    if not target:
        await message.reply_text("❌ Target user not found.")
        return

    # Ask for confirmation with random image
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"transfer_confirm:{sender_id}:{target_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data="transfer_cancel")
            ],
            [InlineKeyboardButton("🔒 Close", callback_data="transfer_close")]
        ]
    )

    await message.reply_photo(
        photo=random.choice(TRANSFER_IMAGES),
        caption=f"⚠️ Are you sure you want to transfer **all your collection** to `{target_id}`?",
        reply_markup=keyboard
    )

# Step 2: Callback Handler
@bot.on_callback_query(filters.regex(r"^transfer_(confirm|cancel|close)(:.*)?$"))
async def transfer_callback(client: Client, callback_query: CallbackQuery):
    data = callback_query.data.split(":")
    action = data[0].replace("transfer_", "")

    if action == "cancel":
        await callback_query.message.edit_caption("❌ Transfer cancelled.")
        return

    if action == "close":
        await callback_query.message.delete()
        return

    if action == "confirm":
        if len(data) < 3:
            await callback_query.answer("⚠️ Invalid data.", show_alert=True)
            return

        sender_id = int(data[1])
        target_id = int(data[2])

        sender = await user_collection.find_one({"id": sender_id})
        target = await user_collection.find_one({"id": target_id})

        if not sender or not target:
            await callback_query.answer("❌ User not found.", show_alert=True)
            return

        # Get collections
        waifus = sender.get("waifu_collection", [])
        amvs = sender.get("amv_collection", [])

        if not waifus and not amvs:
            await callback_query.answer("⚠️ You have no collection to transfer.", show_alert=True)
            return

        # Transfer collections
        await user_collection.update_one(
            {"id": target_id},
            {"$push": {
                "waifu_collection": {"$each": waifus},
                "amv_collection": {"$each": amvs}
            }}
        )

        # Clear sender collections
        await user_collection.update_one(
            {"id": sender_id},
            {"$set": {"waifu_collection": [], "amv_collection": []}}
        )

        # Popup confirmation
        await callback_query.answer("🎉 Your all collection transferred successfully!", show_alert=True)

        # Update message
        await callback_query.message.edit_caption("✅ Transfer completed successfully!")

        # Send DM to target
        try:
            sender_name = callback_query.from_user.first_name
            sender_username = f"@{callback_query.from_user.username}" if callback_query.from_user.username else ""
            await client.send_message(
                target_id,
                f"🎁 `{sender_name}` {sender_username} [{sender_id}] has transferred their **entire collection** to you!"
            )
        except Exception:
            pass
