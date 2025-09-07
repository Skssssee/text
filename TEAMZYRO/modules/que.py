import asyncio
import html
from pyrogram import filters
from TEAMZYRO import app, user_collection, questions_collection

# --- Your Sudo IDs ---
SUDO_USERS = [7553434931, 8189669345, 1741022717]

# In-memory state
active_questions = {}  # {user_id: {"answer": str, "bet": int, "reward": int, "msg": object}}


# --- Add Question (sudo only) ---
@app.on_message(filters.command("add_que"))
async def add_question(client, message):
    if message.from_user.id not in SUDO_USERS:
        return await message.reply_text("❌ You are not allowed to add questions.")

    try:
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


# --- Play Question ---
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

    # Pick random question
    question_doc = await questions_collection.aggregate([{"$sample": {"size": 1}}]).to_list(length=1)
    if not question_doc:
        return await message.reply_text("⚠ No questions available. Admins must add some first.")

    q = question_doc[0]
    question, correct_answer, reward = q["question"], q["answer"], q["coins"]

    # Deduct bet
    await user_collection.update_one({"id": user_id}, {"$inc": {"balance": -bet_amount}})

    # Send question
    sent = await message.reply_text(
        f"📝 **Question:** {html.escape(question)}\n"
        f"💰 Bet: {bet_amount} coins\n"
        f"⏳ Time Left: **10s**\n"
        f"🟢⚪⚪⚪⚪⚪⚪⚪⚪⚪\n\n"
        f"👉 Answer with `/ans <answer>`"
    )

    # Save state
    active_questions[user_id] = {
        "answer": correct_answer,
        "bet": bet_amount,
        "reward": reward,
        "msg": sent,
    }

    # Countdown with progress bar
    async def countdown():
        total = 10
        for i in range(total - 1, -1, -1):
            await asyncio.sleep(1)
            if user_id not in active_questions:
                return  # answered already

            # Progress bar
            filled = "🟢" * (total - i)
            empty = "⚪" * i
            bar = filled + empty

            try:
                await sent.edit_text(
                    f"📝 **Question:** {html.escape(question)}\n"
                    f"💰 Bet: {bet_amount} coins\n"
                    f"⏳ Time Left: **{i}s**\n"
                    f"{bar}\n\n"
                    f"👉 Answer with `/ans <answer>`"
                )
            except:
                pass

        # Timeout
        if user_id in active_questions:
            del active_questions[user_id]
            await sent.reply_text(
                f"⌛ Time's up! Correct answer was: {correct_answer}\n"
                f"💸 You lost {bet_amount} coins."
            )

    asyncio.create_task(countdown())


# --- Answer Command ---
@app.on_message(filters.command("ans"))
async def answer_question(client, message):
    user_id = message.from_user.id
    if user_id not in active_questions:
        return await message.reply_text("⚠ You don't have any active question. Use `/que <bet>` to play.")

    args = message.text.split(" ", 1)
    if len(args) < 2:
        return await message.reply_text("❌ Usage: /ans <your_answer>")

    user_answer = args[1].strip().lower()
    question_data = active_questions[user_id]

    correct_answer = question_data["answer"]
    bet = question_data["bet"]
    reward = question_data["reward"]

    if user_answer == correct_answer:
        total_win = bet + reward
        await user_collection.update_one({"id": user_id}, {"$inc": {"balance": total_win}})
        await message.reply_text(
            f"🎉 Correct!\n✅ Answer: {correct_answer}\n"
            f"💰 You won {reward} coins + your bet back!\n"
            f"📦 Total Added: {total_win} coins"
        )
    else:
        await message.reply_text(
            f"❌ Wrong Answer!\n✅ Correct was: {correct_answer}\n"
            f"💸 You lost your bet of {bet} coins."
        )

    # Remove user from active state
    del active_questions[user_id]
    
