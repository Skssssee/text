from TEAMZYRO import *
import random
import asyncio
from telegram import Update
from telegram.ext import CallbackContext

log = "-1002792716047"

async def delete_message(chat_id, message_id, context):
    await asyncio.sleep(300)  # 5 minutes (300 seconds)
    try:
        await context.bot.delete_message(chat_id, message_id)
    except Exception as e:
        print(f"Error deleting message: {e}")

RARITY_WEIGHTS = {
    "⚪️ Low": (40, True),              # Most frequent
    "🟠 Medium": (20, True),           # Less frequent than Low
    "🔴 High": (12, True),             # Rare but obtainable
    "🎩 Special Edition": (8, True),   # Very rare
    "🪽 Elite Edition": (6, True),     # Extremely rare
    "🪐 Exclusive": (4, True),         # Ultra-rare
    "💞 Valentine": (2, False),         # Special Valentine's rarity
    "🎃 Halloween": (2, False),        # Halloween themed rarity (DISABLED)
    "❄️ Winter": (1.5, False),          # Winter themed rarity
    "🏖 Summer": (1.2, False),          # Summer-themed rarity
    "🎗 Royal": (0.5, False),           # Royal rarity (Bid only)
    "💸 Luxury Edition": (0.5, False)   # Luxury Edition (Shop only)
}

async def send_image(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id

    # Fetch all characters from MongoDB
    all_characters = list(await collection.find({"rarity": {"$in": [k for k, v in RARITY_WEIGHTS.items() if v[1]]}}).to_list(length=None))

    if not all_characters:
        await context.bot.send_message(chat_id, "No characters found with allowed rarities in the database.")
        return

    # Filter characters with valid rarity
    available_characters = [
        c for c in all_characters 
        if 'id' in c and c.get('rarity') is not None and RARITY_WEIGHTS.get(c['rarity'], (0, False))[1]
    ]

    if not available_characters:
        await context.bot.send_message(chat_id, "No available characters with the allowed rarities.")
        return

    # Weighted random selection
    cumulative_weights = []
    cumulative_weight = 0
    for character in available_characters:
        cumulative_weight += RARITY_WEIGHTS.get(character.get('rarity'), (1, False))[0]
        cumulative_weights.append(cumulative_weight)

    rand = random.uniform(0, cumulative_weight)
    selected_character = None
    for i, character in enumerate(available_characters):
        if rand <= cumulative_weights[i]:
            selected_character = character
            break

    if not selected_character:
        selected_character = random.choice(available_characters)

    # Clear first_correct_guesses if exists
    last_characters[chat_id] = character
    last_characters[chat_id]['timestamp'] = time.time()
    
    if chat_id in first_correct_guesses:
        del first_correct_guesses[chat_id]

    # Check if the character has a video URL
    if 'vid_url' in selected_character:
        sent_message = await context.bot.send_video(
            chat_id=chat_id,
            video=selected_character['vid_url'],
            caption=f"""✨ A {selected_character['rarity']} Character Appears! ✨
🔍 Use /guess to claim this mysterious character!
💫 Hurry, before someone else snatches them!""",
            parse_mode='Markdown'
        )
    else:
        sent_message = await context.bot.send_photo(
            chat_id=chat_id,
            photo=selected_character['img_url'],
            caption=f"""✨ A {selected_character['rarity']} Character Appears! ✨
🔍 Use /guess to claim this mysterious character!
💫 Hurry, before someone else snatches them!""",
            parse_mode='Markdown'
        )

    # Schedule message deletion after 5 minutes
    asyncio.create_task(delete_message(chat_id, sent_message.message_id, context))
