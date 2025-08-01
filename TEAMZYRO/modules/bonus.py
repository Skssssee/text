import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime, timedelta

BOT_TOKEN = "Token daal nalle"

# ================= DATABASE =================
conn = sqlite3.connect("users.db", check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    coins INTEGER DEFAULT 0,
    daily TEXT,
    weekly TEXT
)""")
conn.commit()

def get_user(user_id):
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (user_id, coins) VALUES (?, ?)", (user_id, 0))
        conn.commit()
        return (user_id, 0, None, None)
    return user

def update_user(user_id, coins=None, daily=None, weekly=None):
    if coins is not None:
        c.execute("UPDATE users SET coins=? WHERE user_id=?", (coins, user_id))
    if daily is not None:
        c.execute("UPDATE users SET daily=? WHERE user_id=?", (daily, user_id))
    if weekly is not None:
        c.execute("UPDATE users SET weekly=? WHERE user_id=?", (weekly, user_id))
    conn.commit()

# ================= BUTTONS =================
def get_bonus_buttons(user_id):
    user = get_user(user_id)
    now = datetime.now()

    daily_text = "💰 Dᴀɪʟʏ Bᴏɴᴜs❣︎"
    weekly_text = "💎 Wᴇᴇᴋʟʏ Bᴏɴᴜs❣︎"

    if user[2] and datetime.fromisoformat(user[2]) > now:
        daily_text = "✅ Claimed"
    if user[3] and datetime.fromisoformat(user[3]) > now:
        weekly_text = "✅ Claimed"

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(daily_text, callback_data="daily_bonus")],
        [InlineKeyboardButton(weekly_text, callback_data="weekly_bonus")],
        [InlineKeyboardButton("🗑️ Cʟᴏsᴇ", callback_data="close_bonus")]
    ])

# ================= /start =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("💬 Cᴏɴᴛᴀᴄᴛ ᴍʏ ʟᴏʀᴅ", url="https://t.me/Izuku_Here")]]
    text = "⚡ Hey My Lord, I am active!\n\n🤖 *Always ready to serve you!*"

    await update.message.reply_photo(
        photo="https://files.catbox.moe/iavmgv.jpg",  # Apna image link
        caption=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= /bonus =================
async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎁 Cʟᴀɪᴍ ʏᴏᴜʀ ᴅᴀɪʟʏ ᴀɴᴅ ᴡᴇᴇᴋʟʏ ʙᴏɴᴜs ʙᴇʟᴏᴡ:",
        reply_markup=get_bonus_buttons(update.message.from_user.id)
    )

async def handle_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user = get_user(user_id)
    coins = user[1]
    now = datetime.now()

    if query.data == "daily_bonus":
        if user[2] and datetime.fromisoformat(user[2]) > now:
            await query.answer("❌ Already claimed! Come back later.", show_alert=True)
        else:
            coins += 100
            update_user(user_id, coins=coins, daily=(now + timedelta(hours=24)).isoformat())
            await query.answer(f"✨ 100 Coins Added!\nTotal: {coins} 💰", show_alert=True)

        await query.edit_message_reply_markup(reply_markup=get_bonus_buttons(user_id))

    elif query.data == "weekly_bonus":
        if user[3] and datetime.fromisoformat(user[3]) > now:
            await query.answer("❌ Already claimed! Try next week.", show_alert=True)
        else:
            coins += 1000
            update_user(user_id, coins=coins, weekly=(now + timedelta(days=7)).isoformat())
            await query.answer(f"💎 1000 Coins Added!\nTotal: {coins} 💰", show_alert=True)

        await query.edit_message_reply_markup(reply_markup=get_bonus_buttons(user_id))

    elif query.data == "close_bonus":
        await query.delete_message()
        # ================= /coins =================
async def coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.message.from_user.id)
    total = user[1]
    await update.message.reply_text(f"💰 Your Total Coins: {total}", parse_mode="Markdown")

# ================= BOT RUN =================
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("bonus", bonus))
app.add_handler(CommandHandler("coins", coins))
app.add_handler(CallbackQueryHandler(handle_bonus))

print("🔥 Bot is Running with Permanent Data...")
app.run_polling()
