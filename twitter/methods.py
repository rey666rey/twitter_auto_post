import asyncio
import random
import pyotp
import primp
import math
import string
import os
import re
from patchright.async_api import TimeoutError as PlaywrightTimeoutError
from urllib.parse import urlparse
from config import TEMP_DIR
from twitter.media_process import choose_file, unique_media, convert_to_mp4_ffmpeg
import app.database.requests as rq

from dotenv import load_dotenv

load_dotenv()

HEADLESS = os.getenv("HEADLESS", 'true').lower() == "true"

from patchright.async_api import async_playwright, Locator, Page

async def click_random(locator: Locator, manual_radius: float = None):
    box = await locator.bounding_box()  # <-- обязательно await
    if box is None:
        raise Exception("Bounding box not found")

    width, height = box["width"], box["height"]
    cx, cy = width / 2, height / 2
    radius = manual_radius if manual_radius is not None else min(width, height) / 2

    # Выбираем случайную точку внутри окружности
    angle = random.uniform(0, 2 * math.pi)
    r = radius * math.sqrt(random.uniform(0, 1))
    rand_x = cx + r * math.cos(angle)
    rand_y = cy + r * math.sin(angle)

    await locator.click(position={"x": rand_x, "y": rand_y})  # <-- обязательно await

async def human_type(locator: Locator, text: str, min_delay=0.05, max_delay=0.15, mistake_chance=0.05):
    await locator.click()
    for char in text:
        # Иногда делаем ошибку
        if random.random() < mistake_chance:
            wrong_char = random.choice(string.ascii_letters + string.punctuation + string.digits)
            await locator.type(wrong_char)
            await asyncio.sleep(random.uniform(min_delay, max_delay))
            await locator.press("Backspace")
            await asyncio.sleep(random.uniform(min_delay, max_delay))

        # Вводим правильный символ
        await locator.type(char)
        await asyncio.sleep(random.uniform(min_delay, max_delay))

async def scroll_random(page: Page, locator: Locator, direction: str = 'down', steps: int = 10):
    box = await locator.bounding_box()
    if box is None:
        raise Exception("Bounding box not found")

    width, height = box["width"], box["height"]
    left, top = box["x"], box["y"]
    cx, cy = width / 2, height / 2
    radius = min(width, height) / 2.5  # Можно подстроить радиус

    # Случайная точка в окружности
    angle = random.uniform(0, 2 * math.pi)
    r = radius * math.sqrt(random.uniform(0, 1))
    x = left + cx + r * math.cos(angle)
    y = top + cy + r * math.sin(angle)

    # Наводим курсор в эту точку
    await page.mouse.move(x, y)

    for _ in range(steps):
        delta = random.randint(100, 300)
        if direction == 'up':
            delta = -delta
        await page.mouse.wheel(0, delta)
        await asyncio.sleep(random.uniform(0.05, 0.15))  # Естественная задержка

async def create_page(p, proxy, session, user_agent: str):
    launch_args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-popup-blocking",
        "--disable-default-apps"
    ]

    if proxy:
        parsed = urlparse(proxy)
        proxy_dict = {
            "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}",
            "username": parsed.username,
            "password": parsed.password
        }
    else:
        proxy_dict = None

    browser = await p.chromium.launch(
        proxy=proxy_dict,
        headless=HEADLESS,
        args=launch_args
    )

    context = await browser.new_context(
        user_agent=user_agent,
        locale="en-US",
        viewport={"width": 1280, "height": 800},
        record_video_dir=TEMP_DIR,
        record_video_size={"width": 640, "height": 480},
        storage_state=session
    )

    await context.add_init_script("""
        Object.defineProperty(window, 'navigator', {
            value: new Proxy(navigator, {
                has: (target, key) => key === 'webdriver' ? false : key in target,
                get: (target, key) =>
                    key === 'webdriver' ? undefined : typeof target[key] === 'function' ? target[key].bind(target) : target[key]
            })
        });
    """)

    page = await context.new_page()
    video_path = await page.video.path()
    video_path = convert_to_mp4_ffmpeg(video_path)

    return browser, context, page, video_path

async def retry_step(step_func, retries=3, reload_page=None, step_name=""):
    """Выполняет шаг с ретраями.
       step_func — это асинхронная функция без аргументов.
       reload_page — передаётся page, если при ошибке нужно сделать reload().
    """
    for attempt in range(1, retries+1):
        try:
            return await step_func()
        except PlaywrightTimeoutError as e:
            print(f"⚠️ Timeout на шаге {step_name} (попытка {attempt}/{retries}): {e}")
            if attempt < retries:
                if reload_page:
                    await reload_page.reload(timeout=60000)
                await asyncio.sleep(2)
                continue
            else:
                raise

async def auth(nickname, password, proxy, token):
    video_path = None
    try:
        async with async_playwright() as p:
            # Создаём user-agent
            valid_versions = [f"chrome_{v}" for v in range(128, 134) if v != 132]
            chosen_version = random.choice(valid_versions)
            client = primp.Client(impersonate=chosen_version, impersonate_os="windows")
            user_agent = client.headers["user-agent"]

            # Генерируем TOTP
            totp = pyotp.TOTP(token)

            browser, context, page, video_path = await create_page(p, proxy=proxy, session=None, user_agent=user_agent)

            # Заход на сайт
            await retry_step(lambda: page.goto("https://x.com/", timeout=60000),
                             reload_page=page, step_name="goto /")

            # Логин
            await retry_step(lambda: page.get_by_test_id("loginButton").wait_for(state="visible", timeout=30000),
                             reload_page=page, step_name="loginButton visible")
            await retry_step(lambda: click_random(page.get_by_test_id("loginButton")),
                             reload_page=page, step_name="click loginButton")

            # username
            await retry_step(lambda: page.get_by_role("textbox", name="Phone, email, or username").wait_for(timeout=30000),
                             reload_page=page, step_name="username field visible")
            await retry_step(lambda: click_random(page.get_by_role("textbox", name="Phone, email, or username")),
                             reload_page=page, step_name="click username")
            await retry_step(lambda: human_type(page.get_by_role("textbox", name="Phone, email, or username"), text=nickname),
                             reload_page=page, step_name="type username")
            await retry_step(lambda: click_random(page.get_by_role("button", name="Next")),
                             reload_page=page, step_name="click next (after username)")

            # password
            await retry_step(lambda: page.get_by_role("textbox", name="Password Reveal password").wait_for(timeout=30000),
                             reload_page=page, step_name="password field visible")
            await retry_step(lambda: click_random(page.get_by_role("textbox", name="Password Reveal password")),
                             reload_page=page, step_name="click password")
            await retry_step(lambda: human_type(page.get_by_role("textbox", name="Password Reveal password"), text=password),
                             reload_page=page, step_name="type password")
            await retry_step(lambda: page.get_by_role("textbox", name="Password Reveal password").press("Enter"),
                             reload_page=page, step_name="press enter password")

            # 2FA
            await retry_step(lambda: page.get_by_test_id("ocfEnterTextTextInput").wait_for(timeout=30000),
                             reload_page=page, step_name="2FA field visible")
            await retry_step(lambda: click_random(page.get_by_test_id("ocfEnterTextTextInput")),
                             reload_page=page, step_name="click 2FA")
            await retry_step(lambda: human_type(page.get_by_test_id("ocfEnterTextTextInput"), text=totp.now()),
                             reload_page=page, step_name="type 2FA")
            await retry_step(lambda: click_random(page.get_by_role("button", name="Next")),
                             reload_page=page, step_name="click next (after 2FA)")

            # Ждём загрузки
            await asyncio.sleep(15)

            # Получаем сессию
            storage_state = await context.storage_state()

            # Обновляем в базе
            await rq.update_account_fields(nickname, {
                "user_agent": user_agent,
                "session": storage_state
            })
    except Exception as e:
        print(e)
    finally:
        await browser.close()
        return video_path

async def post(tg_id, proxy, session, user_agent, community: int, media: bool):
    """
    Асинхронная функция для публикации поста.
    Всегда возвращает video_path, даже если произошла ошибка.
    """
    video_path = None
    browser = None
    context = None

    try:
        async with async_playwright() as p:
            # создаём страницу и получаем video_path
            browser, context, page, video_path = await create_page(
                p, proxy=proxy, session=session, user_agent=user_agent
            )

            tweet_text = await rq.get_random_tweet(tg_id)

            # --- выбор комьюнити ---
            community_choice = {0: False, 1: lambda: random.choice([True, False]), 2: True}[community]
            if callable(community_choice):
                community_choice = community_choice()

            used_communities = []

            if community_choice:
                communities_urls = [c for c in await rq.get_user_communities(tg_id=tg_id) if c not in used_communities]
                community_url = random.choice(communities_urls)
                await retry_step(lambda: page.goto(community_url, timeout=60000), reload_page=page, step_name='going to community')

                while True:
                    await retry_step(lambda: page.locator("button", has_text=re.compile(r"^(Joined|Join)$")).wait_for(state="visible", timeout=60000),
                                     reload_page=page, step_name="Wait for Join/Joined button")
                    joined_button = page.locator("button", has_text="Joined")
                    is_joined = await joined_button.is_visible()
                    if is_joined:
                        break
                    else:
                        join_button = page.locator("button", has_text="Join")
                        if await join_button.is_visible():
                            await click_random(join_button)
                            await asyncio.sleep(2)
                            agree_button = page.get_by_role("button", name="Agree and join")
                            sorry_button = page.get_by_text('Sorry, you can’t join right now')
                            removed_button = page.get_by_text("You've been removed from this Community")
                            if await agree_button.is_visible():
                                await retry_step(lambda: agree_button.wait_for(state="visible", timeout=60000),
                                                 reload_page=page, step_name="wait_agree_join")
                                await click_random(agree_button)
                                await asyncio.sleep(1)
                            elif await sorry_button.is_visible() or await removed_button.is_visible():
                                used_communities.append(community_url)
                                communities_urls = [c for c in await rq.get_user_communities(tg_id=tg_id) if c not in used_communities]
                                community_url = random.choice(communities_urls)
                                await page.goto(community_url, timeout=60000)
                                continue
            else:
                await retry_step(lambda: page.goto("https://x.com/home", timeout=60000),
                                 reload_page=page, step_name='going to home page')

            # --- ввод текста ---
            await retry_step(lambda: page.get_by_test_id("SideNav_NewTweet_Button").wait_for(state="visible", timeout=60000),
                             reload_page=None, step_name="wait_new_tweet_button")
            await click_random(page.get_by_test_id("SideNav_NewTweet_Button"))
            await asyncio.sleep(2)

            tweet_box = page.get_by_role("textbox", name="Post text")
            await retry_step(lambda: tweet_box.wait_for(state="visible", timeout=60000),
                             reload_page=None, step_name="wait_tweet_box")
            await human_type(tweet_box, text=tweet_text)

            # --- загрузка медиа ---
            if media:
                media_path = choose_file(1)[-1]
                random_number = random.randint(1000, 9999)
                extension = os.path.splitext(media_path)[1].lower()
                unique_media_path = os.path.join(TEMP_DIR, f"temporary_{random_number}{extension}")
                unique_media(media_path, unique_media_path)

                await asyncio.sleep(3)
                inputs = page.locator('input[type="file"][data-testid="fileInput"]')
                if community_choice:
                    await inputs.nth(0).set_input_files(unique_media_path)
                else:
                    await inputs.nth(1).set_input_files(unique_media_path)

                os.remove(unique_media_path)
                await asyncio.sleep(3)

            # --- отправка поста ---
            await click_random(page.get_by_test_id("tweetButton"))
            await retry_step(lambda: page.get_by_text("Your post was sent", exact=False).wait_for(state="visible", timeout=60000),
                             reload_page=page, step_name="wait_post_sent")

    except Exception as e:
        # логируем ошибку, но не прерываем возврат video_path
        print(f"[post()] Произошла ошибка: {e}")

    finally:
        # безопасное закрытие ресурсов
        if context:
            try:
                await context.close()
            except Exception as e:
                print(f"Ошибка при закрытии context: {e}")
        if browser:
            try:
                await browser.close()
            except Exception as e:
                print(f"Ошибка при закрытии browser: {e}")

    # возвращаем video_path даже если была ошибка
    return video_path


async def parsing(proxy, session, user_agent, tg_id, links):
    tweet_count = 0
    video_path = None
    try:
        async with async_playwright() as p:
            # создаём страницу; даже если create_page упадёт, video_path уже есть
            browser, context, page, video_path = await create_page(
                p, proxy=proxy, session=session, user_agent=user_agent
            )
            for link in links:
                # Заходим на страницу
                await retry_step(lambda: page.goto(link, timeout=60000),
                                 reload_page=page, step_name=f"goto {link}")

                # Ждём появления хотя бы одного твита
                await retry_step(lambda: page.wait_for_selector("article", timeout=60000),
                                 reload_page=page, step_name="wait article")

                collected = set()
                last_height = await page.evaluate("() => document.body.scrollHeight")

                while True:
                    # Собираем тексты твитов
                    try:
                        tweets = await page.locator("article div[data-testid='tweetText']").all_inner_texts()
                        for t in tweets:
                            collected.add(t.strip())
                    except PlaywrightTimeoutError as e:
                        print(f"⚠️ Ошибка при сборе твитов: {e}")
                        break

                    # Скроллим
                    await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                    await asyncio.sleep(5)

                    new_height = await page.evaluate("() => document.body.scrollHeight")
                    if new_height == last_height:
                        break
                    last_height = new_height

                tweet_count += await rq.save_user_tweets(tg_id, list(collected))

    except Exception as e:
        print(video_path, e, sep='\n\n')
    finally:
        tweet_count = len(tweet_count)
        # безопасное закрытие
        if context:
            try:
                await context.close()
            except Exception as e:
                print(f"Ошибка при закрытии context: {e}")
        if browser:
            try:
                await browser.close()
            except Exception as e:
                print(f"Ошибка при закрытии browser: {e}")

# возвращаем video_path всегда, даже если были ошибки
    return video_path, tweet_count
