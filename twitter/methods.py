import asyncio
import random
import pyotp
import primp
import math
import string
import os
from patchright.async_api import TimeoutError as PlaywrightTimeoutError
from urllib.parse import urlparse
from config import TEMP_DIR
from twitter.media_process import choose_file, unique_media
import app.database.requests as rq

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
        headless=True,
        args=launch_args
    )

    context = await browser.new_context(
        user_agent=user_agent,
        locale="en-US",
        viewport={"width": 1280, "height": 800},
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
    return browser, context, page

async def auth(nickname, password, proxy, token):
    async with async_playwright() as p:
        # Создаём user-agent
        valid_versions = [f"chrome_{v}" for v in range(128, 134) if v != 132]
        chosen_version = random.choice(valid_versions)
        client = primp.Client(impersonate=chosen_version, impersonate_os="windows")
        user_agent = client.headers["user-agent"]

        # Генерируем TOTP
        totp = pyotp.TOTP(token)

        browser, context, page = await create_page(p, proxy=proxy, session=None, user_agent=user_agent)

        try:
            await page.goto('https://x.com/', timeout=60000)

            login_button = page.get_by_test_id("loginButton")
            await login_button.scroll_into_view_if_needed()
            await click_random(login_button)

            await click_random(page.get_by_role("textbox", name="Phone, email, or username"))
            await human_type(page.get_by_role("textbox", name="Phone, email, or username"), text=nickname)

            await click_random(page.get_by_role("button", name="Next"))

            await click_random(page.get_by_role("textbox", name="Password Reveal password"))
            await human_type(page.get_by_role("textbox", name="Password Reveal password"), text=password)
            await page.get_by_role("textbox", name="Password Reveal password").press("Enter")

            await click_random(page.get_by_test_id("ocfEnterTextTextInput"))
            await human_type(page.get_by_test_id("ocfEnterTextTextInput"), text=totp.now())
            await click_random(page.get_by_role("button", name="Next"))

            # Ждём, чтобы страница полностью прогрузилась и сессия обновилась
            await asyncio.sleep(15)

            # Получаем состояние сессии (cookies, localStorage и т.д.)
            storage_state = await context.storage_state()

            # Обновляем в базе user_agent и session (куки и т.п.)
            await rq.update_account_fields(nickname, {
                "user_agent": user_agent,
                "session": storage_state
            })

        finally:
            await browser.close()

async def retry_step(step_func, retries=10, reload_page=None, step_name=""):
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

async def post(tg_id, proxy, session, user_agent, community: int, media: bool):
    async with async_playwright() as p:
        browser, context, page = await create_page(p, proxy=proxy, session=session, user_agent=user_agent)

        # шаг 1: заход на страницу
        async def goto_page():
            choice = {0: lambda: False, 1: lambda: random.choice([True, False]), 2: lambda: True}[community]()
            if choice:
                community_url = random.choice(await rq.get_user_communities(tg_id=tg_id))
                await page.goto(community_url, timeout=60000)
                return choice
            else:
                await page.goto("https://x.com/home", timeout=60000)
                return choice

        community_choice = await retry_step(lambda: goto_page(), reload_page=page, step_name="goto")

        tweet_text = await rq.get_random_tweet(tg_id)

        # шаг 2: открыть форму постинга
        await retry_step(
            lambda: page.get_by_test_id("SideNav_NewTweet_Button").wait_for(state="visible", timeout=60000), reload_page=None, step_name="wait_new_tweet_button"
        )
        await click_random(page.get_by_test_id("SideNav_NewTweet_Button"))
        await asyncio.sleep(2)

        # шаг 3: если надо — вступить в комьюнити
        if await page.get_by_text("Posting in a Community").is_visible():
            print("Мы не в комьюнити, присоединяемся")
            await click_random(page.get_by_role("button", name="Got it"))
            join_button = page.get_by_role("button").filter(has_text="Join")
            if await join_button.count() > 0:
                await click_random(join_button)
            agree_button = page.get_by_role("button", name="Agree and join")
            await retry_step(
                lambda: agree_button.wait_for(state="visible", timeout=60000), reload_page=page, step_name="wait_agree_join"
            )
            await click_random(agree_button)
            await click_random(page.get_by_test_id("SideNav_NewTweet_Button"))

        # шаг 4: ввести текст
        tweet_box = page.get_by_role("textbox", name="Post text")
        await retry_step(
            lambda: tweet_box.wait_for(state="visible", timeout=60000), reload_page=None, step_name="wait_tweet_box"
        )
        await human_type(tweet_box, text=tweet_text)

        # шаг 5: загрузка медиа
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

        # шаг 6: отправка поста
        await click_random(page.get_by_test_id("tweetButton"))
        await retry_step(
            lambda: page.get_by_text("Your post was sent", exact=False).wait_for(state="visible", timeout=60000), reload_page=page, step_name="wait_post_sent"
        )

        await context.close()
        await browser.close()

async def parsing(proxy, session, user_agent, tg_id, links):
    tweet_count = 0
    for link in links:
        async with async_playwright() as p:
            try:
                browser, context, page = await create_page(p, proxy=proxy, session=session, user_agent=user_agent)
                await page.goto(link, timeout=60000)

                await page.wait_for_selector("article", timeout=60000)  # Ждём появления твитов

                collected = set()
                last_height = await page.evaluate("() => document.body.scrollHeight")

                while True:
                    tweets = await page.locator("article div[data-testid='tweetText']").all_inner_texts()
                    for t in tweets:
                        collected.add(t.strip())

                    await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                    await asyncio.sleep(5)

                    new_height = await page.evaluate("() => document.body.scrollHeight")
                    if new_height == last_height:
                        break
                    last_height = new_height

                tweet_count += await rq.save_user_tweets(tg_id, list(collected))

                result = f"✅ Записано {tweet_count} уникальных твитов"
            except Exception as e:
                result = f'Ошибка парсинга: {e}'
                await browser.close()

    return result if result is not None else 0


