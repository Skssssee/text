import asyncio
import html
import random
from pyrogram import filters
from TEAMZYRO import app, user_collection

questions_collection = db["questions"]

# --- Your Sudo IDs ---
SUDO_USERS = [7553434931, 8189669345, 1741022717]

# Add question command (sudo only)
@app.on_message(filters.command("add_que"))
async def add_question(client, message):
    if message.from_user.id not in SUDO_USERS:
        return await message.reply_text("❌ You are not allowed to add questions.")

    try:
        # Format: /add_que Question | Answer | Coins
        parts = message.text.split(" ", 1)
        if len(parts) < 2:
            return await message.reply_text("Usage: /add_que Question | Answer | Coins")

        data = parts[1].split("|")
        if len(data) != 3:
            return await message.reply_text("❌ Format wrong. Use: /add_que Question | Answer | Coins")

        question, answer, coins = data
        question = question.strip()
        answer = answer.strip().lower()
        coins = int(coins.strip())

        await questions_collection.insert_one({
            "question": question,
            "answer": answer,
            "coins": coins
        })

        await message.reply_text(
            f"✅ Question added by {message.from_user.mention}!\n\n"
            f"❓ {question}\n💡 Answer: {answer}\n💰 Reward: {coins} coins"
        )

    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")


# User plays question game
@app.on_message(filters.command("que"))
async def play_question(client, message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) < 2 or not args[1].isdigit():
        return await message.reply_text("❌ Usage: /que <bet_amount>")

    bet_amount = int(args[1])

    user = await user_collection.find_one({"id": user_id})
    if not user or user.get("balance", 0) < bet_amount:
        return await message.reply_text("❌ You don't have enough coins to place this bet.")

    # Pick a random question
    question_doc = await questions_collection.aggregate([{"$sample": {"size": 1}}]).to_list(length=1)
    if not question_doc:
        return await message.reply_text("⚠ No questions available. Admins must add some first.")

    question_doc = question_doc[0]
    question = question_doc["question"]
    correct_answer = question_doc["answer"]
    reward = question_doc["coins"]

    # Deduct bet from balance first
    await user_collection.update_one({"id": user_id}, {"$inc": {"balance": -bet_amount}})

    # Ask question
    await message.reply_text(
        f"📝 **Question:** {html.escape(question)}\n"
        f"💰 Bet: {bet_amount} coins\n"
        f"⏳ You have **10 seconds** to answer!"
    )

    try:
        # Wait for reply
        response = await client.listen(message.chat.id, filters=filters.user(user_id), timeout=10)
        user_answer = response.text.strip().lower()

        if user_answer == correct_answer:
            total_win = bet_amount + reward
            await user_collection.update_one({"id": user_id}, {"$inc": {"balance": total_win}})

            await response.reply_text(
                f"🎉 Correct!\n✅ Answer: {correct_answer}\n"
                f"💰 You won {reward} coins + your bet back!\n"
                f"📦 Total Added: {total_win} coins"
            )
        else:
            await response.reply_text(
                f"❌ Wrong Answer!\n✅ Correct was: {correct_answer}\n"
                f"💸 You lost your bet of {bet_amount} coins."
            )

    except asyncio.TimeoutError:
        await message.reply_text(
            f"⌛ Time's up! Correct answer was: {correct_answer}\n"
            f"💸 You lost {bet_amount} coins."
          )
      
