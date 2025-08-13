import os

BOT_TOKEN = "8470415898:AAFVoAJZ9ZIpoUMRf9uxsnXvpRobMKH90oE"
AUTHORIZED_USER_ID = 1249561776

DEFAULT_SETTINGS = {
    "posting": {
        "media": False,
        "community_posting": False,
        "interval_hours": 3
}}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTO_DIR = os.path.join(BASE_DIR, 'content', 'photos')
TEMP_DIR = os.path.join(BASE_DIR, 'temp')

if not os.path.exists(TEMP_DIR):
    os.mkdir(TEMP_DIR)