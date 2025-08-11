from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Awaitable, Dict, Any
from config import AUTHORIZED_USER_ID
from app.database.models import async_session  # твоя фабрика сессий

class AccessControl(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if event.from_user.id != AUTHORIZED_USER_ID:
            await event.answer("❌ Доступ запрещён.")
            return

        async with async_session() as session:
            data["session"] = session  # передаём сессию дальше в хэндлер
            return await handler(event, data)
