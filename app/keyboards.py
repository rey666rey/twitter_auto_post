from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
# from app.database.requests import get_all_nicknames

# async def get_nickname_keyboard() -> ReplyKeyboardMarkup:
#     nicknames = await get_all_nicknames()
#     buttons = [[KeyboardButton(text=nickname)] for nickname in nicknames]
#     return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="🔥 Начать работу")],
        [KeyboardButton(text="✍️ Добавить аккаунты")],
        [KeyboardButton(text="📤 Редактировать расписание")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def edit_schedule_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="📤 Настроить постинг")],
        [KeyboardButton(text="❤️ Настроить лайкинг")],
        [KeyboardButton(text="😘 Настроить реплаинг")],
        [KeyboardButton(text="⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def liking_toggle_keyboard(enabled: bool) -> InlineKeyboardMarkup:
    text = "✅ Лайкинг включён" if enabled else "❌ Лайкинг выключен"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data="toggle_liking")]
    ])

def posting_toggle_keyboard(posting: dict) -> InlineKeyboardMarkup:
    enabled = posting.get("enabled", False)
    community_enabled = posting.get("community_posting", False)
    ai_enabled = posting.get("ai", False)
    media_enabled = posting.get("media", False)

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{'✅' if enabled else '❌'} Постинг {'вкл' if enabled else 'выкл'}",
            callback_data="toggle_posting"
        )],
        [InlineKeyboardButton(
            text=f"{'✅' if community_enabled else '❌'} Постинг в community {'вкл' if community_enabled else 'выкл'}",
            callback_data="toggle_posting_community_posting"
        )],
        [InlineKeyboardButton(
            text=f"{'✅' if ai_enabled else '❌'} Нейросеть {'вкл' if ai_enabled else 'выкл'}",
            callback_data="toggle_posting_ai"
        )],
        [InlineKeyboardButton(
            text=f"{'✅' if media_enabled else '❌'} Медиа {'вкл' if media_enabled else 'выкл'}",
            callback_data="toggle_posting_media"
        )],
    ])

def replying_toggle_keyboard(enabled: bool) -> InlineKeyboardMarkup:
    text = "✅ Реплаинг включён" if enabled else "❌ Реплаинг выключен"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data="toggle_replying")]
    ])

def stop_button_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🛑 Стоп', callback_data="stop_button")]
    ])