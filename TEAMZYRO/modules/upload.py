import os
import requests
from pyrogram import Client, filters
from pymongo import ReturnDocument
from gridfs import GridFS
from TEAMZYRO import application, CHARA_CHANNEL_ID, SUPPORT_CHAT, OWNER_ID, collection, user_collection, db, SUDO, rarity_map, ZYRO, require_power

# Wrong format instruction
WRONG_FORMAT_TEXT = """Wrong ❌ format...  eg. /upload reply to photo muzan-kibutsuji Demon-slayer 3

format:- /upload reply character-name anime-name rarity-number

use rarity number accordingly rarity Map

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
    14: "🌧️ Rainy Edition"
}
"""

# Find next available ID
async def find_available_id():
    cursor = collection.find().sort('id', 1)
    ids = []

    async for doc in cursor:
        if 'id' in doc:
            ids.append(int(doc['id']))

    ids.sort()
    for i in range(1, len(ids) + 2):
        if i not in ids:
            return str(i).zfill(2)
    return str(len(ids) + 1).zfill(2)

# Upload to Catbox
def upload_to_catbox(file_path=None, file_url=None, expires=None, secret=None):
    url = "https://catbox.moe/user/api.php"
    with open(file_path, "rb") as file:
        response = requests.post(
            url,
            data={"reqtype": "fileupload"},
            files={"fileToUpload": file}
        )
        if response.status_code == 200 and response.text.startswith("https"):
            return response.text
        else:
            raise Exception(f"Error uploading to Catbox: {response.text}")

import asyncio
upload_lock = asyncio.Lock()

@ZYRO.on_message(filters.command(["gupload"]))
@require_power("add_character")
async def ul(client, message):
    global upload_lock

    if upload_lock.locked():
        await message.reply_text("Another upload is in progress. Please wait until it is completed.")
        return

    async with upload_lock:
        reply = message.reply_to_message
        if reply and (reply.photo or reply.document or reply.video):
            args = message.text.split()
            if len(args) != 4:
                await client.send_message(chat_id=message.chat.id, text=WRONG_FORMAT_TEXT)
                return

            character_name = args[1].replace('-', ' ').title()
            anime = args[2].replace('-', ' ').title()
            rarity = int(args[3])

            if rarity not in rarity_map:
                await message.reply_text("Invalid rarity value. Please use a valid one from the rarity map.")
                return

            rarity_text = rarity_map[rarity]
            available_id = await find_available_id()

            character = {
                'name': character_name,
                'anime': anime,
                'rarity': rarity_text,
                'rarity_number': rarity,
                'id': available_id
            }

            processing_message = await message.reply("<ᴘʀᴏᴄᴇꜱꜱɪɴɢ>....")
            path = await reply.download()
            try:
                catbox_url = upload_to_catbox(path)

                if reply.photo or reply.document:
                    character['img_url'] = catbox_url
                elif reply.video:
                    character['vid_url'] = catbox_url
                    thumbnail_path = await client.download_media(reply.video.thumbs[0].file_id)
                    thumbnail_url = upload_to_catbox(thumbnail_path)
                    character['thum_url'] = thumbnail_url
                    os.remove(thumbnail_path)

                caption_text = (
                    f"Character Name: {character_name}\n"
                    f"Anime Name: {anime}\n"
                    f"Rarity: {rarity_text}\n"
                    f"ID: {available_id}\n"
                    f"Added by [{message.from_user.first_name}](tg://user?id={message.from_user.id})"
                )

                if reply.photo or reply.document:
                    await client.send_photo(chat_id=CHARA_CHANNEL_ID, photo=catbox_url, caption=caption_text)
                elif reply.video:
                    await client.send_video(chat_id=CHARA_CHANNEL_ID, video=catbox_url, caption=caption_text)

                await collection.insert_one(character)
                await message.reply_text(
                    f"➲ ᴀᴅᴅᴇᴅ ʙʏ» [{message.from_user.first_name}](tg://user?id={message.from_user.id})\n"
                    f"➥ Character ID: {available_id}\n"
                    f"➥ Rarity: {rarity_text}"
                )
            except Exception as e:
                await message.reply_text(f"Character Upload Unsuccessful. Error: {str(e)}")
            finally:
                os.remove(path)
        else:
            await message.reply_text("Please reply to a photo, document, or video.")
