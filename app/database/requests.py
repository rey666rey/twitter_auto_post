from sqlalchemy import select, func, update
from app.database.models import async_session, Account, User
from config import DEFAULT_SETTINGS
from sqlalchemy.orm.attributes import flag_modified
import re
import random

async def get_user_accounts(tg_id: int) -> list[Account]:
    """
    Получает все аккаунты, привязанные к пользователю по Telegram ID.

    :param tg_id: Telegram ID пользователя
    :return: список моделей Account
    """
    async with async_session() as session:
        result = await session.execute(
            select(Account)
            .join(User)
            .where(User.tg_id == tg_id)
        )
        accounts = result.scalars().all()
        return accounts

async def get_account_by_nickname(nickname: str) -> Account | None:
    async with async_session() as session:
        result = await session.execute(select(Account).where(Account.nickname == nickname))
        return result.scalar_one_or_none()

async def update_account_fields(nickname: str, fields: dict) -> bool:
    async with async_session() as session:
        result = await session.execute(select(Account).where(Account.nickname == nickname))
        account = result.scalar_one_or_none()
        if not account:
            return False
        await session.execute(
            update(Account)
            .where(Account.nickname == nickname)
            .values(fields)
        )
        await session.commit()
        return True

async def create_user_if_not_exists(tg_id: int):
    async with async_session() as session:
        user = await session.get(User, str(tg_id))
        if user is None:
            new_user = User(
                id=str(tg_id),
                tg_id=tg_id,
                settings=DEFAULT_SETTINGS.copy()  # копия дефолтных настроек
            )
            session.add(new_user)
            await session.commit()
            return True

async def get_user_settings(tg_id: int) -> dict | None:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.tg_id == tg_id)
        )
        user = result.scalar_one_or_none()
        if user:
            return user.settings
        return None

async def edit_user_setting(tg_id: int, category: str, updates: dict) -> bool:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if not user:
            return False
        settings = dict(user.settings or {})
        if category not in settings:
            settings[category] = {}
        settings[category].update(updates)
        user.settings = settings
        flag_modified(user, "settings")

        session.add(user)
        await session.commit()
        return True

async def add_or_update_accounts(tg_id: int, accounts_data: list[str]) -> int:
    account_line_regex = re.compile(r"^(?P<nickname>[^:]+):(?P<email>[^:]+):(?P<password>[^:]+):(?P<proxy>https?://[^:]+:[^@]+@[^:]+:\d+):(?P<token>.+)$")
    processed = 0

    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if not user:
            return 0

        for line in accounts_data:
            match = account_line_regex.match(line.strip())
            if not match:
                continue  # пропускаем, если формат неверный

            data = match.groupdict()

            existing_account = await session.get(Account, data["nickname"])

            if existing_account:
                existing_account.email = data["email"]
                existing_account.password = data["password"]
                existing_account.proxy = data["proxy"]
                existing_account.token = data["token"]
                existing_account.user = user
            else:
                new_account = Account(
                    nickname=data["nickname"],
                    email=data["email"],
                    password=data["password"],
                    proxy=data["proxy"],
                    token=data["token"],
                    user=user
                )
                session.add(new_account)

            processed += 1

        await session.commit()

    return processed

async def save_user_tweets(tg_id: int, new_tweets: list) -> int:
    """
    Сохраняет новые твиты пользователя и возвращает количество уникальных добавленных твитов.
    """
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(select(User).where(User.tg_id == tg_id))
            user = result.scalar_one_or_none()

            if not user:
                print(f"⚠️ Пользователь с tg_id={tg_id} не найден")
                return 0

            existing_tweets = user.tweets or []
            if isinstance(existing_tweets, dict):
                existing_tweets = list(existing_tweets.values())

            existing_set = set(existing_tweets)
            new_set = set(new_tweets)

            # Определяем, что реально новое
            unique_new = new_set - existing_set

            # Объединяем
            combined = list(existing_set | new_set)
            user.tweets = combined

            return len(unique_new)

async def get_random_tweet(tg_id: int) -> str | None:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if not user or not user.tweets:
            return None

        tweets_collection = user.tweets
        if isinstance(tweets_collection, dict):
            tweets_list = list(tweets_collection.values())
        elif isinstance(tweets_collection, list):
            tweets_list = tweets_collection
        else:
            return None

        if not tweets_list:
            return None

        tweet = random.choice(tweets_list)

        # Декодируем unicode-escape
        # Если tweet — строка с unicode escape последовательностями
        broken_text = tweet.encode('windows-1252').decode('utf-8')
        decoded_tweet = broken_text.encode('utf-8').decode('unicode-escape')

        return decoded_tweet

async def get_saved_tweets(tg_id: int) -> dict | None:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.tg_id == tg_id)
        )
        user = result.scalar_one_or_none()
        if user:
            return user.tweets
        return None

async def get_account_count(tg_id: int) -> int:
    """
    Возвращает количество аккаунтов, привязанных к пользователю.

    :param tg_id: Telegram ID пользователя
    :return: количество аккаунтов
    """
    async with async_session() as session:
        result = await session.execute(
            select(func.count(Account.nickname))
            .join(User)
            .where(User.tg_id == tg_id)
        )
        count = result.scalar()
        return count or 0