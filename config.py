import os

BOT_TOKEN = "7720751225:AAE1KaKbDsER3TX0M-KXaMGMeMHQPjxk3PA"
AUTHORIZED_USER_ID = 1249561776

DEFAULT_SETTINGS = {
    "posting": {
        "enabled": True,
        "media": False,
        "ai": False,
        "community_posting": False,
        "interval_hours": 3
    },
    "liking": {
        "enabled": True,
        'post_to_interact_count': 3,
        "interval_hours": 3
    },
    "replying": {
        "enabled": True,
        "count": 1,
        "interval_hours": 5
}}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # путь до текущего .py файла
PHOTO_DIR = os.path.join(BASE_DIR, 'content', 'photos')
VIDEO_DIR = os.path.join(BASE_DIR, 'content', 'videos')
TXT_PATH = os.path.join(BASE_DIR, 'tweets.txt')
TEMP_DIR = os.path.join(BASE_DIR, 'temp')
COMMUNITIES_LIST = os.path.join(BASE_DIR, 'communities.txt')

TWEET_PROMPT = ['beautie how was ur day', 'what r u wearin rn', 'tell me how horny you are', 'are u wet?', 'what do i need to do to see ur naked?', 'tease me', 'tell me something horny']
