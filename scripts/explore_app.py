"""One-off: log into the live app and screenshot the main screens for demo planning."""
from playwright.sync_api import sync_playwright
import pathlib

OUT = pathlib.Path(__file__).parent / "output" / "explore"
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto("https://crosslisteu.com/login")
    page.fill("#email", "dkresellacademy@gmail.com")
    page.fill("#password", "95rwPSLgHxncWDV")
    page.click("button[type=submit], form button")
    page.wait_for_timeout(3000)
    page.screenshot(path=str(OUT / "01_after_login.png"))
    print("URL after login:", page.url)

    # Try navigating the sidebar - dump nav items.
    items = page.eval_on_selector_all(".nav-item, [data-view], .sidebar a, .sidebar [onclick]", "els => els.map(e => e.outerHTML.slice(0,200))")
    for it in items[:40]:
        print(it)

    browser.close()
