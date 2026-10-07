from playwright.sync_api import Page
from artifact.schema import Locator, LocatorStrategy

def find_element(page: Page, locator: Locator, timeout: int = 5000):
    strategy = locator.strategy
    value = locator.value
    fallbacks = locator.fallbacks

    el = _try_locate(page, strategy, value, timeout)
    if el:
        return el

    for fallback in fallbacks:
        s = LocatorStrategy(fallback.get("strategy", "css"))
        v = fallback.get("value", "")
        el = _try_locate(page, s, v, timeout)
        if el:
            print(f"[LOCATOR] Primary failed, fallback succeeded: {s}={v}")
            return el

    print(f"[LOCATOR] All strategies failed for: {value}")
    return None

def _try_locate(page: Page, strategy: LocatorStrategy, value: str, timeout: int):
    try:
        if strategy == LocatorStrategy.CSS:
            el = page.locator(value).first
        elif strategy == LocatorStrategy.XPATH:
            el = page.locator(f"xpath={value}").first
        elif strategy == LocatorStrategy.TEXT:
            el = page.get_by_text(value).first
        elif strategy == LocatorStrategy.NAME:
            el = page.locator(f"[name='{value}']").first
        elif strategy == LocatorStrategy.LABEL:
            el = page.get_by_label(value).first
        elif strategy == LocatorStrategy.PLACEHOLDER:
            el = page.get_by_placeholder(value).first
        elif strategy == LocatorStrategy.ARIA:
            el = page.get_by_role(value).first
        else:
            return None
        el.wait_for(timeout=timeout, state="visible")
        return el
    except Exception:
        return None
