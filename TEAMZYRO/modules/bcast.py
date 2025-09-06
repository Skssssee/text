import asyncio
from pyrogram import filters
from pyrogram.errors import PeerIdInvalid, FloodWait
from TEAMZYRO import user_collection, group_collection, app, require_power  

# 👆 NOTE: yaha group_collection rakha hai (make sure aapke DB me groups isi naam se save ho rahe hain)

@app.on_message(filters.command("bcast"))
@require_power("bcast")
async def broadcast(_, message):
    replied_message = message.reply_to_message
    if not replied_message:
        await message.reply_text("❌ Please reply to a message to broadcast it.")
        return

    # Send initial progress message
    progress_message = await message.reply_text("📢 Starting broadcast...")

    success_count = 0
    fail_count = 0
    user_success = 0
    group_success = 0
    message_count = 0

    # --- Forward function ---
    async def forward_message(target_id):
        nonlocal success_count, fail_count, message_count
        try:
            await replied_message.copy(target_id)  # ✅ copy works better than forward (avoids restrictions)
            success_count += 1
            message_count += 1
        except PeerIdInvalid:
            fail_count += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await forward_message(target_id)
        except Exception as e:
            print(f"Error broadcasting to {target_id}: {e}")
            fail_count += 1

        # Slow down after every 7 messages
        if message_count % 7 == 0:
            await asyncio.sleep(2)

    # --- Progress update ---
    async def update_progress():
        try:
            await progress_message.edit_text(
                f"📢 Broadcast in progress...\n"
                f"👤 Users sent: {user_success}\n"
                f"👥 Groups sent: {group_success}\n"
                f"❌ Failed: {fail_count}"
            )
        except Exception:
            pass

    # --- Send to Users ---
    user_cursor = user_collection.find({})
    async for user in user_cursor:
        user_id = user.get("id")
        if user_id:
            await forward_message(user_id)
            user_success += 1

            if user_success % 100 == 0:
                await update_progress()

    # --- Send to Groups ---
    group_cursor = group_collection.find({})
    unique_group_ids = set()
    async for group in group_cursor:
        group_id = group.get("group_id")
        if group_id and group_id not in unique_group_ids:
            unique_group_ids.add(group_id)
            await forward_message(group_id)
            group_success += 1

            if group_success % 50 == 0:
                await update_progress()

    # --- Final Report ---
    await progress_message.edit_text(
        f"✅ Broadcast completed!\n"
        f"👤 Users sent: {user_success}\n"
        f"👥 Groups sent: {group_success}\n"
        f"❌ Failed: {fail_count}"
        )
    
