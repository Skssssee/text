import asyncio
import html
from pyrogram import filters
from TEAMZYRO import app, user_collection, questions_collection

SUDO_USERS = [7553434931, 8189669345, 1741022717]

active_questions = {}  # user_id: {"answer": str, "bet": int, "reward": int, "msg": object}

# --- Add Question ---
@app.on_message(filters.command("add_que"))
async def add_question(client, message):
    user_id = message.from_user.id
    if user_id not in SUDO_USERS:
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
            f"✅ Question added!\n❓ {question}\n💡 Answer: {answer}\n💰 Reward: {coins} coins"
        )
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# --- Play Question ---
@app.on_message(filters.command("que"))
async def play_question(client, message):
    user_id = message.from_user.id
    args = message.text.split()
    
    if len(args) < 2 or not args[1].isdigit():
        return await message.reply_text("❌ Usage: /que [bet_amount]")

    bet_amount = int(args[1])

    # Fetch user
    user = await user_collection.find_one({"id": user_id})
    if not user:
        return await message.reply_text("⚠ You don't have a profile yet.")
    if user.get("balance", 0) < bet_amount:
        return await message.reply_text("❌ You don't have enough coins.")

    # Fetch random question
    q_list = await questions_collection.find().to_list(length=None)
    if not q_list:
        return await message.reply_text("⚠ No questions available. Admin must add some.")

    import random
    q = random.choice(q_list)

    question, correct_answer, reward = q["question"], q["answer"], q["coins"]

    # Deduct bet
    await user_collection.update_one({"id": user_id}, {"$inc": {"balance": -bet_amount}})

    sent = await message.reply_text(
        f"📝 **Question:** {html.escape(question)}\n"
        f"💰 Bet: {bet_amount}\n"
        f"⏳ Time Left: **10s**\n"
        f"🟢⚪⚪⚪⚪⚪⚪⚪⚪⚪\n\n"
        f"👉 Answer with `/ans <answer>`"
    )

    active_questions[user_id] = {"answer": correct_answer, "bet": bet_amount, "reward": reward, "msg": sent}

    async def countdown():
        total = 10
        for i in range(total - 1, -1, -1):
            await asyncio.sleep(1)
            if user_id not in active_questions:
                return

            filled = "🟢" * (total - i)
            empty = "⚪" * i
            bar = filled + empty
            try:
                await sent.edit_text(
                    f"📝 **Question:** {html.escape(question)}\n"
                    f"💰 Bet: {bet_amount}\n"
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
                f"⌛ Time's up! Correct answer: {correct_answer}\n💸 You lost {bet_amount} coins."
            )

    asyncio.create_task(countdown())  # ✅ create_task is preferred

# --- Answer Command ---
@app.on_message(filters.command("ans"))
async def answer_question(client, message):
    user_id = message.from_user.id
    if user_id not in active_questions:
        return await message.reply_text("⚠ No active question. Use `/que <bet>`.")

    args = message.text.split(" ", 1)
    if len(args) < 2:
        return await message.reply_text("❌ Usage: /ans [your_answer]")

    user_answer = args[1].strip().lower()
    qdata = active_questions[user_id]
    correct_answer, bet, reward = qdata["answer"], qdata["bet"], qdata["reward"]

    if user_answer == correct_answer:
        total_win = bet + reward
        await user_collection.update_one({"id": user_id}, {"$inc": {"balance": total_win}})
        await message.reply_text(
            f"🎉 Correct!\n✅ Answer: {correct_answer}\n💰 You won {reward} coins + your bet back!\n📦 Total Added: {total_win} coins"
        )
    else:
        await message.reply_text(
            f"❌ Wrong!\n✅ Correct answer: {correct_answer}\n💸 You lost {bet} coins."
        )

    del active_questions[user_id]
    
