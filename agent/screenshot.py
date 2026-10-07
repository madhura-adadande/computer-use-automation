import os
import base64
from datetime import datetime
from playwright.sync_api import Page

SCREENSHOT_DIR = "evidence/screenshots"

def take_screenshot(page: Page, label: str = "") -> str:
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{SCREENSHOT_DIR}/{timestamp}_{label}.png"
    page.screenshot(path=filename)
    return filename

def get_page_text(page: Page) -> str:
    try:
        return page.inner_text("body")
    except Exception:
        return ""

def get_page_state(page: Page) -> dict:
    return {
        "url": page.url,
        "title": page.title(),
        "text": get_page_text(page),
    }
