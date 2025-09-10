from TEAMZYRO import *
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, CallbackQuery
from itertools import groupby
import math
from html import escape
import random
from pyrogram import enums
from pyrogram.types import Message
from pyrogram.errors import ChatAdminRequired, UserNotParticipant, ChatWriteForbidden
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

async def fetch_user_characters(user_id):
    user = await user_collection.find_one({"id": user_id})
    if not user or 'characters' not in user:
        return None, 'You have not guessed any characters yet.'
    characters = [c for c in user['characters'] if 'id' in c]
    if not characters:
        return None, 'No valid characters found in your collection.'
    return characters, None

import asyncio  # Import asyncio for sleep function

@app.on_message(filters.command(["harem", "collection"]))
async def harem_handler(client, message):
    
    user_id = message.from_user.id
    page = 0
    user = await user_collection.find_one({"id": user_id})
    filter_rarity = user.get('filter_rarity', None) if user else None
    msg = await display_harem(client, message, user_id, page, filter_rarity, is_initial=True)
    
    # Delete the message after 3 minutes (180 seconds)
    await asyncio.sleep(180)
    await msg.delete()

async def display_harem(client, message, user_id, page, filter_rarity, is_initial=False, callback_query=None):
    try:
        characters, error = await fetch_user_characters(user_id)
        if error:
            await message.reply_text(error)
            return

        # Sort characters by anime and ID
        characters = sorted(characters, key=lambda x: (x.get('anime', ''), x.get('id', '')))

        # Filter by rarity if specified
        if filter_rarity:
            filtered_characters = [c for c in characters if c.get('rarity') == filter_rarity]
            if not filtered_characters:  # If no characters match the filter
                # Show "Remove Filter" button
                keyboard = [
                    [InlineKeyboardButton("Remove Filter", callback_data=f"remove_filter:{user_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await message.reply_text(
                    f"No characters found with rarity: **{filter_rarity}**. Click below to remove the filter.",
                    reply_markup=reply_markup
                )
                return
            characters = filtered_characters

        # Group characters by ID and count duplicates
        character_counts = {k: len(list(v)) for k, v in groupby(characters, key=lambda x: x['id'])}
        unique_characters = list({character['id']: character for character in characters}.values())
        total_pages = math.ceil(len(unique_characters) / 15)

        # Ensure page is within valid range
        if page < 0 or page >= total_pages:
            page = 0

        # Build harem message
        harem_message = f"<b>{escape(message.from_user.first_name)}'s Harem - Page {page+1}/{total_pages}</b>\n"
        if filter_rarity:
            harem_message += f"<b>Filtered by: {filter_rarity}</b>\n"

        # Get characters for the current page
        current_characters = unique_characters[page * 15:(page + 1) * 15]
        current_grouped_characters = {k: list(v) for k, v in groupby(current_characters, key=lambda x: x['anime'])}

        # Add character details to the message
        for anime, chars in current_grouped_characters.items():
            harem_message += f'\n<b>{anime} {len(chars)}/{await collection.count_documents({"anime": anime})}</b>\n'
            for character in chars:
                count = character_counts[character['id']]
                rarity_emoji = rarity_map2.get(character.get('rarity'), '')
                harem_message += f'◈⌠{rarity_emoji}⌡ {character["id"]} {character["name"]} ×{count}\n'

        # Add inline buttons for collection and video-only collection
        keyboard = [
            [
                InlineKeyboardButton("Collection", switch_inline_query_current_chat=f"collection.{user_id}"),
                InlineKeyboardButton("Animation Versia 🎥", switch_inline_query_current_chat=f"collection.{user_id}.AMV")
            ]
        ]

        if total_pages > 1:
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"harem:{page-1}:{user_id}:{filter_rarity or 'None'}"))
            if page < total_pages - 1:
                nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"harem:{page+1}:{user_id}:{filter_rarity or 'None'}"))
            keyboard.append(nav_buttons)

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Select a random character for the image/video
        image_character = None
        user = await user_collection.find_one({"id": user_id})
        if user and 'favorites' in user and user['favorites']:
            favorite_character_id = user['favorites'][0]
            image_character = next((c for c in characters if c['id'] == favorite_character_id), None)

        if not image_character:
            image_character = random.choice(characters) if characters else None

        # Send the harem message with media
        if is_initial:
            if image_character:
                if 'vid_url' in image_character:
                    await message.reply_video(
                        video=image_character['vid_url'],
                        caption=harem_message,
                        reply_markup=reply_markup,
                        parse_mode=enums.ParseMode.HTML
                    )
                elif 'img_url' in image_character:
                    await message.reply_photo(
                        photo=image_character['img_url'],
                        caption=harem_message,
                        reply_markup=reply_markup,
                        parse_mode=enums.ParseMode.HTML
                    )
                else:
                    await message.reply_text(harem_message, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
            else:
                await message.reply_text(harem_message, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
        else:
            # Handle callback query edits
            if image_character:
                if 'vid_url' in image_character:
                    await callback_query.message.edit_media(
                        media=InputMediaPhoto(image_character['vid_url'], caption=harem_message),
                        reply_markup=reply_markup
                    )
                elif 'img_url' in image_character:
                    await callback_query.message.edit_media(
                        media=InputMediaPhoto(image_character['img_url'], caption=harem_message),
                        reply_markup=reply_markup
                    )
                else:
                    await callback_query.message.edit_text(harem_message, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
            else:
                await callback_query.message.edit_text(harem_message, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)

    except Exception as e:
        print(f"Error: {e}")
        await message.reply_text("An error occurred. Please try again later.")

@app.on_callback_query(filters.regex(r"^remove_filter"))
async def remove_filter_callback(client, callback_query):
    try:
        _, user_id = callback_query.data.split(':')
        user_id = int(user_id)

        if callback_query.from_user.id != user_id:
            await callback_query.answer("It's not your Harem!", show_alert=True)
            return

        # Reset the filter to "All" in the database
        await user_collection.update_one({"id": user_id}, {"$set": {"filter_rarity": None}}, upsert=True)

        # Delete the current message
        await callback_query.message.delete()

        # Notify the user that the filter has been removed
        await callback_query.answer("Filter removed. Showing all rarities.", show_alert=True)
    except Exception as e:
        print(f"Error in remove_filter callback: {e}")

@app.on_callback_query(filters.regex(r"^harem"))
async def harem_callback(client, callback_query):
    try:
        data = callback_query.data
        _, page, user_id, filter_rarity = data.split(':')
        page = int(page)
        user_id = int(user_id)
        filter_rarity = None if filter_rarity == 'None' else filter_rarity

        if callback_query.from_user.id != user_id:
            await callback_query.answer("It's not your Harem!", show_alert=True)
            return

        await display_harem(client, callback_query.message, user_id, page, filter_rarity, is_initial=False, callback_query=callback_query)
    except Exception as e:
        print(f"Error in callback: {e}")


rarity_map = {
    1: "⚪️ Low",
    2: "🟠 Medium",
    3: "🔴 High",
    4: "🎩 Special Edition",
    5: "🪽 Elite Edition",
    6: "🪐 Exclusive",
    7: "💞 Valentine",
    8: "🎃 Halloween",
    9: "❄️ Winter",
    10: "🏖 Summer",
    11: "🎗 Royal",
    12: "💸 Luxury Edition",
    13: "🍃 echhi",
    14: "🌧️ Rainy Edition",
    15: "🎍 Festival"
}


@app.on_message(filters.command("hmode"))
async def hmode_handler(client, message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)

    # --- Case 1: User typed "/hmode rarityname" ---
    if len(args) > 1:
        rarity_input = args[1].strip().lower()

        rarity_lookup = {v.lower(): v for v in rarity_map.values()}

        if rarity_input in rarity_lookup:
            rarity_value = rarity_lookup[rarity_input]
            await user_collection.update_one(
                {"id": user_id},
                {"$set": {"filter_rarity": rarity_value}},
                upsert=True
            )
            await message.reply_text(
                f"✅ Rarity filter set to: <b>{rarity_value}</b>\n\n"
                "Open your collection with /harem to see filtered results.",
                parse_mode=enums.ParseMode.HTML
            )
            confirm = await message.reply_text("🎉 Your rarity set successfully!")
            await asyncio.sleep(3)
            await confirm.delete()
            return

        elif rarity_input in ["all", "none"]:
            await user_collection.update_one(
                {"id": user_id},
                {"$set": {"filter_rarity": None}},
                upsert=True
            )
            await message.reply_text(
                "✅ Rarity filter cleared. Showing all rarities.\n\n"
                "Open your collection with /harem to see filtered results."
            )
            confirm = await message.reply_text("🎉 Your rarity set successfully!")
            await asyncio.sleep(3)
            await confirm.delete()
            return

        else:
            available = ", ".join(rarity_map.values())
            await message.reply_text(
                f"❌ Invalid rarity: <b>{args[1]}</b>\n\n"
                f"Available: {available}, All",
                parse_mode=enums.ParseMode.HTML
            )
            return

    # --- Case 2: No rarity typed, show buttons ---
    keyboard, row = [], []
    for i, value in enumerate(rarity_map.values(), 1):
        row.append(
            InlineKeyboardButton(
                value,
                callback_data=f"set_rarity:{user_id}:{value}"  # 👈 user_id lock
            )
        )
        if i % 2 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton("All", callback_data=f"set_rarity:{user_id}:None")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(
        "🎭 Select a rarity to filter your harem:",
        reply_markup=reply_markup
    )


@app.on_callback_query(filters.regex(r"^set_rarity:"))
async def set_rarity_callback(client, callback_query):
    try:
        _, owner_id, rarity_value = callback_query.data.split(':')
        owner_id = int(owner_id)

        # ✅ Security check: only owner can press
        if callback_query.from_user.id != owner_id:
            await callback_query.answer("⚠️ Not your menu!", show_alert=True)
            return

        user_id = callback_query.from_user.id
        rarity_value = None if rarity_value == "None" else rarity_value

        await user_collection.update_one(
            {"id": user_id},
            {"$set": {"filter_rarity": rarity_value}},
            upsert=True
        )

        if rarity_value:
            await callback_query.message.edit_text(
                f"✅ Rarity filter set to: <b>{rarity_value}</b>\n\n"
                "Open your collection with /harem to see filtered results.",
                parse_mode=enums.ParseMode.HTML,
                reply_markup=callback_query.message.reply_markup
            )
        else:
            await callback_query.message.edit_text(
                "✅ Rarity filter cleared. Showing all rarities.\n\n"
                "Open your collection with /harem to see filtered results.",
                reply_markup=callback_query.message.reply_markup
            )

        await callback_query.answer("🎉 Your rarity set successfully!", show_alert=False)

    except Exception as e:
        print(f"Error in set_rarity callback: {e}")
        await callback_query.answer("❌ Error setting rarity filter", show_alert=True)
