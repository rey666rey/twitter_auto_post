import asyncio
import random
import pyotp
import primp
import os
import math
import string
import re
from urllib.parse import urlparse
from config import TWEET_PROMPT, TXT_PATH, TEMP_DIR, COMMUNITIES_LIST
import twitter.tweet as write
import app.database.requests as rq

from patchright.async_api import async_playwright, Locator, Page
from twitter.make_unique import choose_file, unique_media

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
    """
    Скроллит мышкой в случайной точке внутри элемента.

    :param page: объект Page
    :param locator: элемент, внутри которого будет происходить прокрутка
    :param direction: 'down' или 'up'
    :param steps: количество шагов прокрутки
    """
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

async def create_page(p, proxy: str, session, user_agent: str):
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

async def making_replies(proxy, session, user_agent, target_post_count):
    async with async_playwright() as p:
        browser, context, page = await create_page(p, proxy, session, user_agent)
        await page.goto('https://x.com/home', timeout=60000)
        await page.wait_for_selector("article", timeout=10000)

        post_counter = 0
        seen_articles = set()

        while post_counter < target_post_count:
            await page.get_by_label('Home timeline', exact=True).press('PageDown')
            await page.wait_for_timeout(2000)  # дать время подгрузиться новым твитам

            tweet_articles = await page.locator("article").all()

            for article in tweet_articles:
                # Чтобы избежать дублирования
                article_id = await article.evaluate("el => el.innerText.slice(0, 50)")
                if article_id in seen_articles:
                    continue
                seen_articles.add(article_id)

                try:
                    # Нажимаем кнопку "Reply" внутри article
                    reply_button = article.get_by_role("button", name="Reply")
                    await click_random(reply_button)

                    # Извлекаем текст твита
                    tweet_text_parts = await article.locator('div[lang] span').all_inner_texts()
                    tweet_text = "\n".join([t.strip() for t in tweet_text_parts if t.strip()])

                    # Генерируем ответ
                    reply_text = write.query_lm_studio(prompt=tweet_text)

                    # Вставляем и публикуем
                    await human_type(page.get_by_role('textbox', name='Post text'), text=reply_text)
                    await click_random(page.get_by_test_id('tweetButton'))

                    post_counter += 1
                    print(f"✅ Ответ отправлен на твит #{post_counter}")
                    await page.wait_for_timeout(3000)

                    if post_counter >= target_post_count:
                        break

                except Exception as e:
                    print(f"⚠️ Ошибка при ответе на твит #{post_counter + 1}: {e}")
                    continue

async def post(proxy, session, user_agent, community:bool, media: bool, neuro_tweets: bool):
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
            if neuro_tweets:
                tweet_text=write.query_lm_studio(random.choice(TWEET_PROMPT))
            else:
                tweet_text = write.choose_one_string_from_txt(TXT_PATH)

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
            if media:
                media_path = choose_file('photos', 1)[-1]
                random_number = random.randint(1000, 9999)
                extension = os.path.splitext(media_path)[1].lower()
                unique_media_path = os.path.join(TEMP_DIR, f'temporary_{random_number}{extension}')
                unique_media(media_path, unique_media_path)
                await asyncio.sleep(3)
                inputs = page.locator('input[type="file"][data-testid="fileInput"]')
                await inputs.nth(1).set_input_files(unique_media_path)
                await asyncio.sleep(3)
            await click_random(page.get_by_test_id('tweetButton'))
            await asyncio.sleep(1)
            post_was_sent = page.get_by_text("Your post was sent", exact=False)
            await post_was_sent.wait_for(state="visible")
        finally:
            await context.close()
            await browser.close()

async def liking(proxy, session, user_agent, target_hours, post_count):
    async with async_playwright() as p:
        browser, context, page = await create_page(p, proxy=proxy, session=session, user_agent=user_agent)
        await page.goto("https://x.com/home", timeout=60000)

        container = page.get_by_test_id("primaryColumn")
        attempt = 0
        seen_posts = set()

        # Паттерн: часы или минуты
        time_pattern = re.compile(r"^([0-9]+)\s?(h|hours? ago|m|minutes? ago)$")

        for _ in range(post_count):
            found = False
            while not found:
                attempt += 1
                matches = await container.get_by_role("link").all()

                for m in matches:
                    text = (await m.inner_text()).strip()
                    match = time_pattern.match(text)
                    if match:
                        num, unit = match.groups()
                        num = int(num)
                        # Часы <= target_hours или минуты
                        if (unit.startswith("h") and num <= target_hours) or unit.startswith("m"):
                            post_id = await m.get_attribute("href")
                            if post_id not in seen_posts:
                                seen_posts.add(post_id)
                                print(f"⚡ Пост '{text}' найден на попытке #{attempt}")
                                await click_random(m)
                                await asyncio.sleep(3)

                                # Собираем кнопки лайков двумя способами
                                like_buttons_tid = await page.get_by_test_id("like").all()
                                like_buttons_role = await page.get_by_role("button").filter(
                                    has_text=re.compile(r"Like$", re.I)
                                ).all()

                                all_buttons = like_buttons_tid + like_buttons_role

                                for btn in all_buttons:
                                    # Получаем атрибуты для определения количества лайков
                                    aria_label = await btn.get_attribute("aria-label") or ""
                                    name_attr = await btn.get_attribute("name") or ""
                                    label = aria_label or name_attr

                                    # Ищем число лайков в тексте (например: "3 likes")
                                    likes_match = re.search(r"(\d+)\s+likes?", label, re.I)
                                    if likes_match:
                                        likes_count = int(likes_match.group(1))
                                    else:
                                        # Если число лайков не найдено, считаем 0
                                        likes_count = 0

                                    aria_pressed = await btn.get_attribute("aria-pressed")

                                    if likes_count < 10 and aria_pressed != "true":
                                        if await btn.is_visible():
                                            await click_random(btn)
                                            print(f"❤️ Лайк поставлен (текущее количество лайков: {likes_count})")
                                            await asyncio.sleep(random.uniform(1, 3))

                                await asyncio.sleep(2)
                                await click_random(page.get_by_test_id("app-bar-back"))
                                found = True
                                break

                    if not found:
                        await scroll_random(page, locator=container, direction="down", steps=5)
        await context.close()
        await browser.close()




