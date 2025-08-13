import primp
from patchright.sync_api import sync_playwright
import time
import random

valid_versions = [f"chrome_{v}" for v in range(128, 134) if v != 132]
chosen_version = random.choice(valid_versions)

client = primp.Client(impersonate=chosen_version, impersonate_os="windows")  # windows, linux
user_agent = client.headers["user-agent"]

launch_args = [
    "--disable-blink-features=AutomationControlled",
    "--disable-popup-blocking",
    "--disable-default-apps"
]

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=launch_args,
        channel="chrome"
    )
    context = browser.new_context(
        locale="en-US",
        user_agent=user_agent,
        viewport={"width": 1280, "height": 800}
    )

    context.add_init_script("""
            Object.defineProperty(window, 'navigator', {
                value: new Proxy(navigator, {
                    has: (target, key) => key === 'webdriver' ? false : key in target,
                    get: (target, key) =>
                        key === 'webdriver' ? undefined : typeof target[key] === 'function' ? target[key].bind(target) : target[key]
                })
            });

        """)

    page = context.new_page()
    page.goto("https://bot.sannysoft.com/", timeout=60000)
    page.screenshot(path="screenshot.png", full_page=True)

    time.sleep(5)

    browser.close()