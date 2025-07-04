from pyrogram import filters
from TEAMZYRO import app
from pymongo import MongoClient
from pyrogram.types import Message

# MongoDB Setup
MONGO_URL = "mongodb+srv://Gojowaifu:waifu123@gojowaifu.royysxq.mongodb.net/?retryWrites=true&w=majority&appName=Gojowaifu"
mongo = MongoClient(MONGO_URL)
db = mongo["waifu_bot"]
users = db["users"]

TOKEN_RATE = 100  # 100 coins = 1 token

@app.on_message(filters.command("convert"))
async def convert_coins(client, message: Message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) != 2 or not args[1].isdigit():
        return await message.reply("❌ Usage: `/convert 100`", quote=True)

    coins_to_convert = int(args[1])
    user_data = users.find_one({"_id": user_id})

    if not user_data:
        users.insert_one({"_id": user_id, "coins": 0, "tokens": 0})
        user_data = users.find_one({"_id": user_id})

    current_coins = int(user_data.get("coins", 0))
current_tokens = int(user_data.get("tokens", 0))

await message.reply(
    f"🧪 DEBUG:\ncoins in db = {current_coins}\nuser entered = {coins_to_convert}",
    quote=True
        )

    if coins_to_convert > current_coins:
        return await message.reply("❌ You don't have that many coins!", quote=True)

    tokens_earned = coins_to_convert // TOKEN_RATE
    if tokens_earned == 0:
        return await message.reply("❌ Not enough coins to convert even 1 token!", quote=True)

    coins_after = current_coins - coins_to_convert
    new_tokens = current_tokens + tokens_earned

    users.update_one(
        {"_id": user_id},
        {"$set": {"coins": coins_after, "tokens": new_tokens}}
    )

    await message.reply(
        f"✅ Converted {coins_to_convert} coins into {tokens_earned} token(s).\n"
        f"🪙 Remaining Coins: {coins_after}\n🎟 Total Tokens: {new_tokens}",
        quote=True
    )
