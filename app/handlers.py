from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.middlewares import AccessControl
import app.database.requests as rq
from twitter.runner import start_tasks, stop_tasks
import app.keyboards as kb

router = Router()

class AccountStates(StatesGroup):
    edit_posting = State()
    edit_liking = State()
    edit_replying = State()
    add_accounts = State()
    cancel = State()

router.message.middleware(AccessControl())

@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    tg_id = message.from_user.id
    added = await rq.create_user_if_not_exists(tg_id)
    welcome_text = (
        "👋 <b>Привет! Добро пожаловать в Twitter Auto Post Bot!</b>\n\n"
        "Здесь ты можешь легко управлять своими аккаунтами:\n"
        "📤 Автоматический постинг\n"
        "❤️ Лайкинг интересных твитов\n"
        "💬 Реплаинг по расписанию\n\n"
        "⚙️ Чтобы начать, выбери нужную функцию в меню ниже и настрой параметры под себя.\n"
        "Если нужна помощь — просто напиши /help или нажми кнопку с инструкцией.\n\n"
        "Желаю продуктивной работы и множества лайков! 🚀"
    )
    welcome_back_text = (
        "👋 <b>С возвращением!</b>\n\n"
        "Все работает как часы ⏱\n"
        "Ты всегда можешь изменить расписание, добавить аккаунты или посмотреть статус задач в меню ниже.\n\n"
        "Удачного продвижения! 🚀"
    )
    if added:
        await message.answer(text=welcome_text, reply_markup=kb.main_menu_keyboard(), parse_mode='HTML')
    else:
        await message.answer(text=welcome_back_text, reply_markup=kb.main_menu_keyboard(), parse_mode='HTML')

@router.message(F.text == "🔥 Начать работу")
async def start_work(message: Message):
    tg_id = message.from_user.id
    chat_id = message.chat.id
    bot = message.bot
    settings = await rq.get_user_settings(tg_id)

    is_posting_enabled = settings.get('posting', {}).get('enabled', False)
    is_liking_enabled = settings.get('liking', {}).get('enabled', False)
    is_replying_enabled = settings.get('replying', {}).get('enabled', False)

    messages_to_delete = []
    post_msg = like_msg = reply_msg = None

    if is_posting_enabled:
        post_msg = await bot.send_message(chat_id, "⏳ Инициализация постинга...")
        messages_to_delete.append(post_msg.message_id)

    if is_liking_enabled:
        like_msg = await bot.send_message(chat_id, "⏳ Инициализация лайкинга...")
        messages_to_delete.append(like_msg.message_id)

    if is_replying_enabled:
        reply_msg = await bot.send_message(chat_id, "⏳ Инициализация реплаинга...")
        messages_to_delete.append(reply_msg.message_id)

    start_msg = await message.reply(
        "🚀 Задачи запущены и будут обновлять статусы в этих сообщениях.",
        reply_markup=kb.stop_button_keyboard()
    )
    messages_to_delete.append(start_msg.message_id)

    # Запускаем задачи и передаем список сообщений для удаления
    await start_tasks(
        tg_id,
        bot,
        chat_id,
        messages_to_delete,
        post_msg.message_id if post_msg else None,
        like_msg.message_id if like_msg else None,
        reply_msg.message_id if reply_msg else None
    )

@router.message(F.text == "📤 Редактировать расписание")
async def edit_schedule(message: Message):
    tg_id = message.from_user.id
    settings = await rq.get_user_settings(tg_id)
    accounts_count = await rq.get_account_count(tg_id)

    if not settings:
        await message.answer("⚠️ Настройки для вас не найдены.")
        return

    text = "⚙️ Ваши текущие настройки:\n\n"

    # Постинг
    posting = settings.get('posting', {})
    posting_enabled = posting.get('enabled', True)

    # Лайкинг
    liking = settings.get('liking', {})
    liking_enabled = liking.get('enabled', True)

    replying = settings.get('replying', {})
    replying_enabled = replying.get('enabled', True)

    if posting_enabled:
        post_interval = posting.get('interval_hours', 'не установлено')
        text += (
            f"📤 Постинг:\n"
            f"• Интервал: {post_interval} час\n\n"
        )

    if liking_enabled:
        like_min = liking.get('min_likes', 'не установлено')
        like_max = liking.get('max_likes', 'не установлено')
        like_interval = liking.get('interval_hours', 'не установлено')
        text += (
            f"❤️ Лайкинг:\n"
            f"• От: {like_min} лайков\n"
            f"• До: {like_max} лайков\n"
            f"• Интервал: {like_interval} час\n\n"
        )

    if replying_enabled:
        reply_count = replying.get('count', 'не установлено')
        reply_interval = replying.get('interval_hours', 'не установлено')
        text += (
            f"😘 Реплаинг:\n"
            f"• Кол-во постов: {reply_count}\n"
            f"• Интервал: {reply_interval} час\n\n"
        )

    text += (
        f"🗂 Привязанные аккаунты: {accounts_count}\n\n"
        f"🛠 Чтобы изменить любую настройку — выберите нужный пункт в меню."
    )

    await message.answer(text, reply_markup=kb.edit_schedule_keyboard())

@router.message(F.text == "⬅️ Назад")
async def go_back_to_main_menu(message: Message, state: FSMContext):
    await state.clear()  # выйти из любого состояния
    await message.answer(
        "🔙 Вы вернулись в главное меню. Выберите действие:",
        reply_markup=kb.main_menu_keyboard()
    )

@router.message(F.text == "📤 Настроить постинг")
async def edit_posting(message: Message, state:FSMContext):
    tg_id = message.from_user.id
    settings = await rq.get_user_settings(tg_id)
    await state.set_state(AccountStates.edit_posting)
    text=('📢 Введите число, означающее интервал в часах между публикациями:\n'
          'Пример: 1 — значит 1 пост каждый 1 час')
    await message.answer(text, reply_markup=kb.posting_toggle_keyboard(settings.get('posting', {})))

@router.message(F.text == "❤️ Настроить лайкинг")
async def edit_liking(message: Message, state:FSMContext):
    await state.set_state(AccountStates.edit_liking)
    tg_id = message.from_user.id
    settings = await rq.get_user_settings(tg_id)
    text = (
        "❤️ Введите три числа через пробел:\n\n"
        "🔢 Первое — количество постов, под которыми будут ставиться лайки\n"
        "⏰ Второе — интервал в часах между сессиями лайкинга\n\n"
        "Пример: 3 5 — значит бот будет ставить лайки свежим реплаям под 3 постами каждые 2 часа"
    )
    await message.answer(text, reply_markup=kb.liking_toggle_keyboard(settings.get('liking', {}).get('enabled')))

@router.message(F.text == "😘 Настроить реплаинг")
async def edit_replying(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    settings = await rq.get_user_settings(tg_id)
    await state.set_state(AccountStates.edit_replying)
    text=('📢 Введите два числа через пробел:\n\n'
          '📝 Первое — сколько реплаев вы хотите публиковать за один раз)\n'
          '⏰ Второе — интервал в часах между публикациями\n\n'
          'Пример: 3 2 — значит 3 поста каждые 2 часа')
    await message.answer(text, reply_markup = kb.replying_toggle_keyboard(settings.get('replying', {}).get('enabled')))

@router.message(F.text == "✍️ Добавить аккаунты")
async def add_accounts(message: Message, state: FSMContext):
    await state.set_state(AccountStates.add_accounts)
    text = (
        "👤 *Добавление аккаунтов*\n\n"
        "Пожалуйста, отправьте данные об аккаунтах *построчно* в следующем формате:\n\n"
        "`nickname:email:password:proxy:token`\n\n"
        "🔹 *nickname* — никнейм аккаунта\n"
        "🔹 *email* — почта (если не используется — повторите nickname)\n"
        "🔹 *password* — пароль от аккаунта\n"
        "🔹 *proxy* — прокси в формате `http://user:pass@ip:port`\n"
        "🔹 *token* — токен для двухфакторной авторизации (если не используется — оставьте пустым)\n\n"
        "📌 *Пример:*\n"
        "`testuser:test@mail.com:password123:http://user308399:a5wzym@104.234.228.254:9236:ABCDEFGH12345678`\n\n"
        "Можно отправить *несколько строк* сразу. Каждая строка — это один аккаунт."
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=kb.edit_schedule_keyboard())

@router.callback_query(F.data.in_(['toggle_posting', 'toggle_posting_ai', 'toggle_posting_media', "toggle_posting_community_posting"]))
async def toggle_posting_callback(callback: CallbackQuery):
    tg_id = callback.from_user.id
    settings = await rq.get_user_settings(tg_id)

    posting_settings = settings.get('posting', {})

    enabled = posting_settings.get('enabled', False)
    community_enabled = posting_settings.get("community_posting", False)
    ai_enabled = posting_settings.get('ai', False)
    media_enabled = posting_settings.get('media', False)

    if callback.data == 'toggle_posting':
        new_enabled = not enabled
        await rq.edit_user_setting(tg_id, 'posting', {'enabled': new_enabled})
        await callback.answer(f"Постинг {'включен' if new_enabled else 'выключен'}")

    elif callback.data == "toggle_posting_community_posting":
        new_community_enabled = not community_enabled
        await rq.edit_user_setting(tg_id, 'posting', {"community_posting": new_community_enabled})
        await callback.answer(f"Постинг в коммьюнити {'включен' if new_community_enabled else 'выключен'}")

    elif callback.data == 'toggle_posting_ai':
        new_ai_enabled = not ai_enabled
        await rq.edit_user_setting(tg_id, 'posting', {'ai': new_ai_enabled})
        await callback.answer(f"Нейросеть {'включена' if new_ai_enabled else 'выключена'}")

    elif callback.data == 'toggle_posting_media':
        new_media_enabled = not media_enabled
        await rq.edit_user_setting(tg_id, 'posting', {'media': new_media_enabled})
        await callback.answer(f"Медиа {'включена' if new_media_enabled else 'выключена'}")

    # Получаем обновлённые настройки
    updated_settings = await rq.get_user_settings(tg_id)
    keyboard = kb.posting_toggle_keyboard(updated_settings.get("posting", {}))

    # Обновляем клавиатуру в сообщении
    await callback.message.edit_reply_markup(reply_markup=keyboard)

@router.callback_query(F.data == "toggle_liking")
async def toggle_liking_callback(callback: CallbackQuery):
    tg_id = callback.from_user.id
    settings = await rq.get_user_settings(tg_id)
    current_enabled = settings.get('liking', {}).get('enabled')  # заменить на реальное значение из БД
    new_enabled = not current_enabled

    # Сохраняем новое состояние в БД
    await rq.edit_user_setting(tg_id, 'liking', {'enabled': new_enabled})

    # Обновляем кнопку с новым текстом
    keyboard = kb.liking_toggle_keyboard(new_enabled)

    # Обновляем сообщение с кнопкой
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer(f"Лайкинг {'включён' if new_enabled else 'выключен'}")

@router.callback_query(F.data == "toggle_replying")
async def toggle_replying_callback(callback: CallbackQuery):
    tg_id = callback.from_user.id
    settings = await rq.get_user_settings(tg_id)
    current_enabled = settings.get('replying', {}).get('enabled')  # заменить на реальное значение из БД
    new_enabled = not current_enabled

    # Сохраняем новое состояние в БД
    await rq.edit_user_setting(tg_id, 'replying', {'enabled': new_enabled})

    # Обновляем кнопку с новым текстом
    keyboard = kb.replying_toggle_keyboard(new_enabled)

    # Обновляем сообщение с кнопкой
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer(f"Реплаинг {'включён' if new_enabled else 'выключен'}")

@router.callback_query(F.data == "stop_button")
async def stop_button(callback: CallbackQuery):
    tg_id = callback.from_user.id
    chat_id = callback.message.chat.id  # ВАЖНО: берём chat_id из message
    bot = callback.bot

    await stop_tasks(tg_id, bot, chat_id)
    await callback.answer("Задачи остановлены")

@router.message(AccountStates.edit_posting)
async def save_posting_settings(message: Message, state: FSMContext):
    text = message.text.strip()

    try:
        post_interval = int(text)
        if post_interval <= 0:
            raise ValueError("Интервал должен быть положительным числом")

        await rq.edit_user_setting(
            message.from_user.id,
            category="posting",
            updates={'interval_hours': post_interval}
        )

        await message.answer(
            f"✅ Настройки постинга обновлены:\n\n"
            f"Интервал: {post_interval} час(а/ов)",
            reply_markup=kb.main_menu_keyboard()
        )

    except ValueError:
        await message.answer(
            "❌ Введите целое положительное число — например, 1, 2 или 5.",
            reply_markup=kb.main_menu_keyboard()
        )

    await state.clear()

@router.message(AccountStates.edit_liking)
async def save_liking_settings(message: Message, state: FSMContext):
    await state.clear()
    user_input = message.text.strip()
    parts = user_input.split()

    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        await message.answer("❌ Пожалуйста, введите ровно три числа через пробел. Попробуйте еще раз.", reply_markup=kb.main_menu_keyboard())
        return

    post_to_interact_count, interval_hours = map(int, parts)

    success = await rq.edit_user_setting(message.from_user.id, category="liking", updates={'post_to_interact_count': post_to_interact_count,
                                                                                         'interval_hours': interval_hours})

    if not success:
        await message.answer("❌ Пользователь не найден в базе данных.", reply_markup=kb.main_menu_keyboard())
        await state.clear()
        return

    await message.answer(f"❤️✅ Настройки лайкинга обновлены:\n\n"
                         f"🔢 Количество постов, под которыми будут ставиться лайки: {post_to_interact_count}\n"
                         f"⏰ Интервал: {interval_hours}", reply_markup=kb.main_menu_keyboard())

@router.message(AccountStates.add_accounts)
async def save_added_accounts(message: Message, state: FSMContext):
    await state.clear()
    raw_text = message.text.strip()
    lines = raw_text.splitlines()

    # Отфильтровываем пустые строки
    account_lines = [line for line in lines if line.strip()]

    if not account_lines:
        await message.answer("❌ Пожалуйста, отправьте хотя бы одну строку с аккаунтом в формате:\n\n`nickname:email:password:proxy:token`", parse_mode="Markdown")
        return

    # Сохраняем аккаунты
    added_count = await rq.add_or_update_accounts(tg_id=message.from_user.id, accounts_data=account_lines)

    if added_count == 0:
        await message.answer("❌ Не удалось сохранить ни один аккаунт. Убедитесь, что формат строк корректен.", reply_markup=kb.main_menu_keyboard())
    else:
        await message.answer(f"✅ Успешно добавлено или обновлено аккаунтов: {added_count}")

@router.message(AccountStates.edit_replying)
async def save_replying_settings(message: Message, state: FSMContext):
    await state.clear()
    user_input = message.text.strip()
    parts = user_input.split()

    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        await message.answer("❌ Пожалуйста, введите ровно два числа через пробел. Попробуйте еще раз.", reply_markup=kb.main_menu_keyboard())
        return

    post_count, post_interval = map(int, parts)

    success = await rq.edit_user_setting(message.from_user.id, category="replying", updates={'count': post_count,
                                                                                         'interval_hours': post_interval})

    if not success:
        await message.answer("❌ Пользователь не найден в базе данных.", reply_markup=kb.main_menu_keyboard())
        await state.clear()
        return

    await message.answer(f"✅ Настройки реплаинга обновлены:\n\n"
                         f"Количество реплаев: {post_count}\n"
                         f"Интервал: {post_interval} час(а/ов)", reply_markup=kb.main_menu_keyboard())