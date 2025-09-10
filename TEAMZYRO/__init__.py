# ------------------------------ IMPORTS ---------------------------------
import logging
import os
from telegram.ext import Application
from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram import Client, filters as f
from pyrogram.types import x

# --------------------------- LOGGING SETUP ------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        logging.FileHandler("log.txt"),
        logging.StreamHandler(),
    ],
)

logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("telegram").setLevel(logging.ERROR)

def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)

# ---------------------------- CONSTANTS ---------------------------------
api_id = os.getenv("API_ID", "23343216")
api_hash = os.getenv("API_HASH", "1d66f21cd828dc22b80e3750719bd94a")
TOKEN = os.getenv("TOKEN", "")
GLOG = os.getenv("GLOG", "hug_your_waifu")
CHARA_CHANNEL_ID = os.getenv("CHARA_CHANNEL_ID", "hug_your_waifu")
SUPPORT_CHAT_ID = os.getenv("SUPPORT_CHAT_ID", "-1003091789166")
mongo_url = os.getenv("MONGO_URL", "mongodb+srv://Gojowaifu2:Gojowaifu2@cluster0.uvox90s.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

MUSJ_JOIN = os.getenv("MUSJ_JOIN", "https://t.me/@hug_your_waifu")

# Modified to support both image and video URLs
START_MEDIA = os.getenv("START_MEDIA", "https://files.catbox.moe/68jx8u.jpg").split(',')

PHOTO_URL = [
    os.getenv("PHOTO_URL_1", "https://files.catbox.moe/68jx8u.jpg"),
    os.getenv("PHOTO_URL_2", "https://files.catbox.moe/68jx8u.jpg")
]

STATS_IMG = ["https://files.catbox.moe/0zvwpt.jpg"]

SUPPORT_CHAT = os.getenv("SUPPORT_CHAT", "https://t.me/hug_your_waifu")
UPDATE_CHAT = os.getenv("UPDATE_CHAT", "https://t.me/hug_your_waifu")
SUDO = list(map(int, os.getenv("SUDO", "5715948933,5612652584").split(',')))
OWNER_ID = int(os.getenv("OWNER_ID", "6356015122"))

# --------------------- TELEGRAM BOT CONFIGURATION -----------------------
command_filter = f.create(lambda _, __, message: message.text and message.text.startswith("/"))
application = Application.builder().token(TOKEN).build()
ZYRO = Client("Shivu", api_id=api_id, api_hash=api_hash, bot_token=TOKEN)

# -------------------------- DATABASE SETUP ------------------------------
ddw = AsyncIOMotorClient(mongo_url)
db = ddw['hinata_waifu']

# Collections
user_totals_collection = db['gaming_totals']
group_user_totals_collection = db['gaming_group_total']
top_global_groups_collection = db['gaming_global_groups']
pm_users = db['gaming_pm_users']
destination_collection = db['gamimg_user_collection']
destination_char = db['gaming_anime_characters']
questions_collection = db["questions"]
group_collection = db["groups"]
waifu_collection = db["waifus"]

# -------------------------- GLOBAL VARIABLES ----------------------------
app = ZYRO
sudo_users = SUDO
collection = destination_char
user_collection = destination_collection

# --------------------------- STRIN ---------------------------------------
locks = {}
message_counters = {}
spam_counters = {}
last_characters = {}
sent_characters = {}
first_correct_guesses = {}
message_counts = {}
last_user = {}
warned_users = {}
user_cooldowns = {}
user_nguess_progress = {}
user_guess_progress = {}
normal_message_counts = {}  

# -------------------------- POWER SETUP --------------------------------
from TEAMZYRO.unit.zyro_ban import *
from TEAMZYRO.unit.zyro_sudo import *
from TEAMZYRO.unit.zyro_react import *
from TEAMZYRO.unit.zyro_log import *
from TEAMZYRO.unit.zyro_send_img import *
from TEAMZYRO.unit.zyro_rarity import *
# ------------------------------------------------------------------------

async def PLOG(text: str):
    await app.send_message(
       chat_id=GLOG,
       text=text
   )

# ---------------------------- END OF CODE ------------------------------
