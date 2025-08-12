import os

BOT_TOKEN = "8470415898:AAFVoAJZ9ZIpoUMRf9uxsnXvpRobMKH90oE"
AUTHORIZED_USER_ID = 1249561776

DEFAULT_SETTINGS = {
    "posting": {
        "media": False,
        "community_posting": False,
        "interval_hours": 3
}}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # путь до текущего .py файла

COMMUNITIES_LIST = os.path.join(BASE_DIR, 'communities.txt')