import asyncio
import app.database.requests as rq
import twitter.methods as tweet
from aiogram import Bot
from typing import Callable, Optional
import time

class ScheduledTask:
    def __init__(self, func: Callable, name: str, interval: int | float, message_id: int):
        self.func = func
        self.name = name
        self.interval = int(interval)
        self.message_id = message_id

async def work_posting_only(tg_id: int, bot: Bot, chat_id: int, message_id: int):
    accounts = await rq.get_user_accounts(tg_id)
    if not accounts:
        await bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                    text="Постинг: ⚠️ Нет аккаунтов для постинга")
        return
    for account in accounts:
        nickname = account.nickname
        try:
            if not account.session:
                await tweet.auth(account.nickname, account.password, account.proxy, account.token)
                # Обновляем данные после логина
                account = await rq.get_account_by_nickname(account.nickname)
                await bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                            text=f"Постинг: ✅ {nickname}: Успешный вход")
            else:
                await bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                            text=f"Постинг: ℹ️ {nickname}: Уже залогинен")
            settings = await rq.get_user_settings(tg_id)
            community_status = settings.get('posting', {}).get('community_posting')
            await tweet.post(tg_id=tg_id, proxy=account.proxy, session=account.session, user_agent=account.user_agent, community = community_status)
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                        text=f"Постинг: ✅ {nickname}: Пост отправлен")
        except Exception as e:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                        text=f"❌ Постинг: {nickname}: Ошибка — {e}")
            raise

        await asyncio.sleep(2)  # Хуманизация

async def task_worker(tg_id: int, bot: Bot, chat_id: int, queue: asyncio.Queue, messages_to_delete):
    tasks = []

    # Инициализируем список задач из очереди
    while not queue.empty():
        scheduled_task = await queue.get()
        tasks.append({
            'task': scheduled_task,
            'last_run': 0,
            'last_text': ''
        })

    try:
        while tasks:
            now = int(time.time())
            tasks_to_remove = []

            for item in tasks:
                task = item['task']
                last_run = item ['last_run']
                time_since_last_run = now - last_run
                time_until_next = task.interval - time_since_last_run

                if time_since_last_run >= task.interval:
                    try:
                        print(f"🚀 Запуск задачи: {task.name}")
                        result_text = await task.func(tg_id, bot, chat_id, task.message_id)
                    except Exception as e:
                        print(f"⚠️ Ошибка в {task.name}: {e}")
                        tasks_to_remove.append(item)  # Отмечаем задачу для удаления
                        start_msg_id = messages_to_delete[-1]
                        await bot.delete_message(chat_id, start_msg_id)
                        continue  # Переходим к следующей задаче
                    else:
                        item['last_run'] = int(time.time())
                        next_minutes = task.interval // 60
                        new_text = (f"{result_text[:4000]}\n\n" if result_text else "") + \
                                   f"✅ {task.name} завершён. Следующий запуск через {next_minutes} мин."

                        if new_text != item['last_text']:
                            await bot.edit_message_text(
                                chat_id=chat_id,
                                message_id=task.message_id,
                                text=new_text
                            )
                            item['last_text'] = new_text

                else:
                    # Показываем таймер только для активных задач
                    mins_left = time_until_next // 60
                    secs_left = time_until_next % 60
                    wait_text = f"⏳ Задача {task.name} запустится через {mins_left} мин {secs_left} сек"

                    if wait_text != item['last_text']:
                        await bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=task.message_id,
                            text=wait_text
                        )
                        item['last_text'] = wait_text

            # Удаляем задачи, которые упали с ошибкой
            for item in tasks_to_remove:
                tasks.remove(item)

            # Если задач не осталось — выходим из цикла
            if not tasks:
                print(f"Все задачи для пользователя {tg_id} завершены или остановлены.")
                break

            await asyncio.sleep(1)

    except asyncio.CancelledError:
        print(f"task_worker для пользователя {tg_id} отменён")
        raise

# Глобальное хранилище активных воркеров
active_workers: dict[int, dict] = {}

async def start_tasks(
    tg_id: int,
    bot: Bot,
    chat_id: int,
    messages_to_delete: list[int],  # Передаем список всех сообщений для удаления
    post_msg_id: Optional[int] = None
):
    settings = await rq.get_user_settings(tg_id)
    if not settings:
        print(f"Нет настроек для пользователя {tg_id}")
        return

    post_interval = settings.get('posting', {}).get('interval_hours', 1) * 3600

    queue = asyncio.Queue()

    await queue.put(ScheduledTask(work_posting_only, "Постинг", post_interval, post_msg_id))

    # Запускаем воркер
    worker_task = asyncio.create_task(task_worker(tg_id, bot, chat_id, queue, messages_to_delete))

    # Сохраняем в глобальный словарь
    active_workers[tg_id] = {
        "task": worker_task,
        "messages": messages_to_delete
    }


async def stop_tasks(tg_id: int, bot: Bot, chat_id: int):
    worker_info = active_workers.get(tg_id)
    if not worker_info:
        print(f"Нет активных задач для пользователя {tg_id}.")
        return

    print(f"Остановка задач для пользователя {tg_id}...")

    # Удаляем все связанные сообщения
    for msg_id in worker_info["messages"]:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception as e:
            print(f"Не удалось удалить сообщение {msg_id}: {e}")

    await bot.send_message(chat_id, "✅ Работа остановлена.")

    # Останавливаем задачу
    worker_task = worker_info["task"]
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        print(f"Задачи для пользователя {tg_id} успешно остановлены.")

    del active_workers[tg_id]