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
TOKEN = os.getenv("TOKEN", "8018957937:AAFBWIwewR-nf0_EC10-Z_9HJWz5K64YGlI")
GLOG = os.getenv("GLOG", "gojo_waifu")
CHARA_CHANNEL_ID = os.getenv("CHARA_CHANNEL_ID", "gojo_waifu")
SUPPORT_CHAT_ID = os.getenv("SUPPORT_CHAT_ID", "-1002792716047")
mongo_url = os.getenv("MONGO_URL", "mongodb+srv://Gojowaifu:waifu123@gojowaifu.royysxq.mongodb.net/?retryWrites=true&w=majority&appName=Gojowaifu")

MUSJ_JOIN = os.getenv("MUSJ_JOIN", "https://t.me/+8KU5ZDxvZyw0N2U1")

# Modified to support both image and video URLs
START_MEDIA = os.getenv("START_MEDIA", "https://files.catbox.moe/7ccoub.jpg,https://files.catbox.moe/s8ggxy.jpg,https://files.catbox.moe/qqelwn.jpg,https://telegra.ph/file/1a3c152717eb9d2e94dc2.mp4").split(',')

PHOTO_URL = [
    os.getenv("PHOTO_URL_1", "https://files.catbox.moe/qqelwn.jpg"),
    os.getenv("PHOTO_URL_2", "https://files.catbox.moe/7ccoub.jpg")
]

STATS_IMG = ["https://files.catbox.moe/zpbvfn.jpg"]

SUPPORT_CHAT = os.getenv("SUPPORT_CHAT", "https://t.me/GOJO_NOBITA_II")
UPDATE_CHAT = os.getenv("UPDATE_CHAT", "https://t.me/GOJO_SUPPORT_GROUP_II")
SUDO = list(map(int, os.getenv("SUDO", "7450385463").split(',')))
OWNER_ID = int(os.getenv("OWNER_ID", "7553434931"))

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
