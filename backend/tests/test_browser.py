"""Manual smoke test for the browser engine — fetch, link extraction, form
extraction + filling, and screenshot, each isolated so one failure doesn't mask others.

Run from the backend directory with the venv active:
    python -m tests.test_browser
"""
import asyncio

from app.browser.engine import engine
from app.browser.extractor import extract_links, extract_forms
from app.browser.automation import fill_form


async def main():
    print("--- fetch (JS-rendered page) ---")
    try:
        result = await engine.fetch("https://example.com")
        print(f"title: {result['title']}")
        print(f"text (first 150 chars): {result['text'][:150]}")
    except Exception as e:
        print(f"FAILED: {e}")

    print("\n--- link extraction ---")
    try:
        async with engine.page() as page:
            await page.goto("https://example.com", wait_until="networkidle")
            links = await extract_links(page)
            print(f"found {len(links)} links: {links[:5]}")
    except Exception as e:
        print(f"FAILED: {e}")

    print("\n--- form extraction + fill (httpbin test form) ---")
    try:
        async with engine.page() as page:
            await page.goto("https://httpbin.org/forms/post", wait_until="networkidle")
            forms = await extract_forms(page)
            if forms:
                print(f"fields: {[f['name'] for f in forms[0]['fields']]}")
            await fill_form(page, {"custname": "Atlas Test", "custemail": "test@example.com"})
            value = await page.input_value("[name='custname']")
            print(f"filled custname -> {value}")
    except Exception as e:
        print(f"FAILED: {e}")

    print("\n--- screenshot ---")
    try:
        png = await engine.screenshot("https://example.com")
        print(f"screenshot size: {len(png)} bytes")
    except Exception as e:
        print(f"FAILED: {e}")

    await engine.stop()


if __name__ == "__main__":
    asyncio.run(main())
