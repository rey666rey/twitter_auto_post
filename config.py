import os
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

BOT_TOKEN=os.getenv("BOT_TOKEN")
AUTHORIZED_USER_ID=1249561776

DEFAULT_SETTINGS = {
    "posting": {
        "media": 0,
        "community_posting": 0,
        "interval_hours": 3
}}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTO_DIR = os.path.join(BASE_DIR, 'content', 'photos')
TEMP_DIR = os.path.join(BASE_DIR, 'temp')

if not os.path.exists(TEMP_DIR):
    os.mkdir(TEMP_DIR)