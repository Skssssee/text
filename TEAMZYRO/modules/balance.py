from TEAMZYRO import *
from pyrogram import Client, filters
from pyrogram.types import Message
import html, random

# --- Balance Helper ---
async def get_balance(user_id):
    user_data = await user_collection.find_one({'id': user_id}, {'balance': 1})
    if user_data:
        return user_data.get('balance', 0)
    return 0

# --- Balance Images (Spoiler) ---
BALANCE_IMAGES = [
    "https://files.catbox.moe/3saw6n.jpg",
    "https://files.catbox.moe/3ilay5.jpg",
    "https://files.catbox.moe/i28al7.jpg",
    "https://files.catbox.moe/k7t6y7.jpg",
    "https://files.catbox.moe/h0ftuw.jpg",
    "https://files.catbox.moe/syanmk.jpg",
    "https://files.catbox.moe/shslw1.jpg",
    "https://files.catbox.moe/xokoit.jpg",
    "https://files.catbox.moe/6w5fl4.jpg"
]

# ✅ BALANCE COMMAND
@app.on_message(filters.command("balance"))
async def balance(client: Client, message: Message):
    user_id = message.from_user.id
    user_balance = await get_balance(user_id)

    caption = (
        f"👤 {html.escape(message.from_user.first_name)}\n"
        f"💰 Balance: ||{user_balance} coins||"
    )

    photo_url = random.choice(BALANCE_IMAGES)

    await message.reply_photo(
        photo=photo_url,
        caption=caption,
        has_spoiler=True   # 👈 photo bhi spoiler me hoga
    )


# --- PAY COMMAND ---
@app.on_message(filters.command("pay"))
async def pay(client: Client, message: Message):
    sender_id = message.from_user.id
    args = message.command

    if len(args) < 3:
        await message.reply_text("Usage: /pay <amount> [@username/user_id] or reply to a user.")
        return

    # --- Amount check ---
    try:
        amount = int(args[1])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.reply_text("❌ Invalid amount. Please enter a positive number.")
        return

    recipient_id = None
    recipient_name = None

    # If replied to user
    if message.reply_to_message:
        recipient_id = message.reply_to_message.from_user.id
        recipient_name = message.reply_to_message.from_user.first_name

    # If username or ID given
    elif len(args) > 2:
        try:
            recipient_id = int(args[2])
        except ValueError:
            recipient_username = args[2].lstrip('@')
            user_data = await user_collection.find_one({'username': recipient_username}, {'id': 1, 'first_name': 1})
            if user_data:
                recipient_id = user_data['id']
                recipient_name = user_data.get('first_name', recipient_username)
            else:
                await message.reply_text("❌ Recipient not found.")
                return

    if not recipient_id:
        await message.reply_text("❌ Recipient not found. Reply to a user or provide a valid user ID/username.")
        return

    sender_balance = await get_balance(sender_id)
    if sender_balance < amount:
        await message.reply_text("❌ Insufficient balance.")
        return

    # --- Confirm/Cancel Buttons ---
    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"pay_confirm:{sender_id}:{recipient_id}:{amount}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"pay_cancel:{sender_id}:{recipient_id}:{amount}")
            ]
        ]
    )

    recipient_display = html.escape(recipient_name or str(recipient_id))
    await message.reply_text(
        f"⚠️ Are you sure you want to pay {amount} coins to {recipient_display}?",
        reply_markup=buttons
    )


# --- CALLBACK HANDLER ---
@app.on_callback_query(filters.regex(r"^pay_"))
async def pay_callback(client, callback_query):
    try:
        data = callback_query.data.split(":")
        action = data[0]          # "pay_confirm" or "pay_cancel"
        sender_id = int(data[1])
        recipient_id = int(data[2])
        amount = int(data[3])

        # Always answer callback (avoid stuck loading)
        await callback_query.answer()

        # Security check: only sender can confirm
        if callback_query.from_user.id != sender_id:
            await callback_query.answer("⚠️ You are not allowed to confirm this transaction!", show_alert=True)
            return

        # Cancel
        if action == "pay_cancel":
            await callback_query.message.edit_text("❌ Payment cancelled.")
            return

        # Confirm
        if action == "pay_confirm":
            sender_balance = await get_balance(sender_id)
            if sender_balance < amount:
                await callback_query.message.edit_text("❌ Transaction failed. Insufficient balance.")
                return

            # Update balances
            await user_collection.update_one({'id': sender_id}, {'$inc': {'balance': -amount}})
            await user_collection.update_one({'id': recipient_id}, {'$inc': {'balance': amount}}, upsert=True)

            updated_sender_balance = await get_balance(sender_id)
            updated_recipient_balance = await get_balance(recipient_id)

            recipient_data = await user_collection.find_one({'id': recipient_id}, {'first_name': 1})
            recipient_name = recipient_data.get('first_name', str(recipient_id)) if recipient_data else str(recipient_id)

            sender_display = html.escape(callback_query.from_user.first_name or str(sender_id))
            recipient_display = html.escape(recipient_name)

            # Notify sender
            await callback_query.message.edit_text(
                f"✅ You paid {amount} coins to {recipient_display}.\n"
                f"💰 Your New Balance: {updated_sender_balance} coins"
            )

            # Notify recipient
            try:
                await client.send_message(
                    chat_id=recipient_id,
                    text=f"🎉 You received {amount} coins from {sender_display}!\n"
                         f"💰 Your New Balance: {updated_recipient_balance} coins"
                )
            except:
                pass

    except Exception as e:
        await callback_query.answer("⚠️ Error in processing payment!", show_alert=True)
        print(f"PAY CALLBACK ERROR: {e}")


# --- KILL COMMAND (unchanged) ---
@app.on_message(filters.command("kill"))
@require_power("VIP")
async def kill_handler(client, message):
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    else:
        await message.reply_text("Please reply to a user's message to use the /kill command.")
        return

    command_args = message.text.split()

    if len(command_args) < 2:
        await message.reply_text("Please specify an option: `c` to delete character, `f` to delete full data, or `b` to delete balance.")
        return

    option = command_args[1]

    try:
        if option == 'f':
            await user_collection.delete_one({"id": user_id})
            await message.reply_text("The full data of the user has been deleted.")

        elif option == 'c':
            if len(command_args) < 3:
                await message.reply_text("Please specify a character ID to remove.")
                return

            char_id = command_args[2]
            user = await user_collection.find_one({"id": user_id})

            if user and 'characters' in user:
                characters = user['characters']
                updated_characters = [c for c in characters if c.get('id') != char_id]

                if len(updated_characters) == len(characters):
                    await message.reply_text(f"No character with ID {char_id} found in the user's collection.")
                    return

                await user_collection.update_one({"id": user_id}, {"$set": {"characters": updated_characters}})
                await message.reply_text(f"Character with ID {char_id} has been removed from the user's collection.")
            else:
                await message.reply_text(f"No characters found in the user's collection.")

        elif option == 'b':
            if len(command_args) < 3:
                await message.reply_text("Please specify an amount to deduct from balance.")
                return

            try:
                amount = int(command_args[2])
            except ValueError:
                await message.reply_text("Invalid amount. Please enter a valid number.")
                return

            user_data = await user_collection.find_one({"id": user_id}, {"balance": 1})
            if user_data and "balance" in user_data:
                current_balance = user_data["balance"]
                new_balance = max(0, current_balance - amount)
                
                await user_collection.update_one({"id": user_id}, {"$set": {"balance": new_balance}})
                await message.reply_text(f"{amount} has been deducted from the user's balance. New balance: {new_balance}")
            else:
                await message.reply_text("The user has no balance to deduct from.")

        else:
            await message.reply_text("Invalid option. Use `c` for character, `f` for full data, or `b {amount}` to deduct balance.")

    except Exception as e:
        print(f"Error in /kill command: {e}")
        await message.reply_text("An error occurred while processing the request. Please try again later.")
        




