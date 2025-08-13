from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.middlewares import AccessControl
from twitter.methods import parsing
import app.database.requests as rq
from twitter.runner import start_tasks, stop_tasks
import app.keyboards as kb

router = Router()

class AccountStates(StatesGroup):
    edit_posting = State()
    edit_liking = State()
    edit_replying = State()
    add_accounts = State()
    parsing = State()
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
    messages_to_delete = []

    post_msg = await bot.send_message(chat_id, "⏳ Инициализация постинга...")
    messages_to_delete.append(post_msg.message_id)

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
        post_msg.message_id
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

    post_interval = settings.get('posting', {'interval_hours'})
    text += (
        f"📤 Постинг:\n"
        f"• Интервал: {post_interval} час\n\n"
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

@router.message(F.text == "👾 Парсинг твитов")
async def parsing_tweets(message: Message, state: FSMContext):
    await state.set_state(AccountStates.parsing)
    await message.answer('Введите ссылку на аккаунт, твиты которого надо спарсить.')

@router.callback_query(F.data.in_(["toggle_posting_community_posting"]))
async def toggle_posting_callback(callback: CallbackQuery):
    tg_id = callback.from_user.id
    settings = await rq.get_user_settings(tg_id)

    posting_settings = settings.get('posting', {})

    community_enabled = posting_settings.get("community_posting", False)

    if callback.data == "toggle_posting_community_posting":
        new_community_enabled = not community_enabled
        await rq.edit_user_setting(tg_id, 'posting', {"community_posting": new_community_enabled})
        await callback.answer(f"Постинг в коммьюнити {'включен' if new_community_enabled else 'выключен'}")

    # Получаем обновлённые настройки
    updated_settings = await rq.get_user_settings(tg_id)
    keyboard = kb.posting_toggle_keyboard(updated_settings.get("posting", {}))

    # Обновляем клавиатуру в сообщении
    await callback.message.edit_reply_markup(reply_markup=keyboard)

@router.callback_query(F.data == "stop_button")
async def stop_button(callback: CallbackQuery):
    tg_id = callback.from_user.id
    chat_id = callback.message.chat.id  # ВАЖНО: берём chat_id из message
    bot = callback.bot

    await stop_tasks(tg_id, bot, chat_id)
    await callback.answer("Задачи остановлены")

@router.message(AccountStates.parsing)
async def start_parsing(message: Message):
    tg_id = message.from_user.id
    link = message.text
    accounts = await rq.get_user_accounts(tg_id)
    account = accounts[-1]
    result = await parsing(proxy=account.proxy, session=account.session, user_agent=account.user_agent, tg_id=tg_id, link=link)
    await message.answer(str(result))

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