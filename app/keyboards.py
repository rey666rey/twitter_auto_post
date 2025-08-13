from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="🔥 Начать работу")],
        [KeyboardButton(text="✍️ Добавить аккаунты")],
        [KeyboardButton(text="📤 Редактировать расписание")],
        [KeyboardButton(text="👾 Парсинг твитов")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def posting_toggle_keyboard(posting: dict) -> InlineKeyboardMarkup:
    community_enabled = posting.get("community_posting")
    media_enabled = posting.get("media")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{'✅' if community_enabled else '❌'} Постинг в community {'вкл' if community_enabled else 'выкл'}",
            callback_data="toggle_posting_community_posting"
        )],
        [InlineKeyboardButton(
            text=f"{'✅' if media_enabled else '❌'} Медиа {'вкл' if media_enabled else 'выкл'}",
            callback_data="toggle_posting_media"
        )],
    ])

def edit_schedule_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="📤 Настроить постинг")],
        [KeyboardButton(text="⭐️ Загрузить список communities")],
        [KeyboardButton(text="⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def stop_button_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🛑 Стоп', callback_data="stop_button")]
    ])