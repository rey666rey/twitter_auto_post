import asyncio
import random
import pyotp
import primp
import math
import string
from urllib.parse import urlparse
from config import COMMUNITIES_LIST
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
        headless=False,
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

async def post(tg_id, proxy, session, user_agent, community:bool):
    async with async_playwright() as p:
        browser, context, page = await create_page(p, proxy=proxy, session=session, user_agent=user_agent)
        try:
            if community:
                with open(COMMUNITIES_LIST, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    lines = [line.strip() for line in lines if line.strip()]
                community = random.choice(lines) if lines else ''
                await page.goto(community, timeout=60000)
            else:
                await page.goto('https://x.com/home', timeout=60000)

            tweet_text = await rq.get_random_tweet(tg_id)

            await click_random(page.get_by_test_id('SideNav_NewTweet_Button'))
            await asyncio.sleep(2)
            not_in_community = await page.get_by_text("Posting in a Community").is_visible()

            if not_in_community:
                print('Мы не в комьюнити, присоединяемся')
                await click_random(page.get_by_role("button", name="Got it"))
                join_button = page.get_by_role("button").filter(has_text='Join')
                if await join_button.count() > 0:
                    await click_random(join_button)
                agree_button = page.get_by_role("button", name="Agree and join")
                await agree_button.wait_for(state='visible')
                await click_random(agree_button)
                await click_random(page.get_by_test_id('SideNav_NewTweet_Button'))

            tweet_box = page.get_by_role("textbox", name="Post text")
            await tweet_box.wait_for(state="visible")
            await human_type(tweet_box, text=tweet_text)
            await click_random(page.get_by_test_id('tweetButton'))
            await asyncio.sleep(1)
            post_was_sent = page.get_by_text("Your post was sent", exact=False)
            await post_was_sent.wait_for(state="visible")
        finally:
            await context.close()
            await browser.close()

async def parsing(proxy, session, user_agent, tg_id, link):
    async with async_playwright() as p:
        try:
            browser, context, page = await create_page(p, proxy=proxy, session=session, user_agent=user_agent)
            await page.goto(link, timeout=60000)

            await page.wait_for_selector("article")  # Ждём появления твитов

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

            print(collected)
            tweet_count = await rq.save_user_tweets(tg_id, list(collected))

            result = f"✅ Записано {tweet_count} уникальных твитов"
        except Exception as e:
            result = e
            await browser.close()

    return result if result is not None else 0


