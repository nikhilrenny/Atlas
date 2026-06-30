"""Form-filling automation, built on the same BrowserEngine used for fetching.

Kept deliberately dumb for now (fill by field `name`, optional submit) — this is the
seam the tool-builder phase will drive programmatically once it can read a form's
structure (via extractor.extract_forms) and decide what to type where.
"""
from playwright.async_api import Page


async def fill_form(page: Page, field_values: dict[str, str], submit: bool = False) -> None:
    """field_values maps a form field's `name` attribute to the value to set.
    Text/textarea inputs are typed; <select> elements use select_option."""
    for name, value in field_values.items():
        el = await page.query_selector(f"[name='{name}']")
        if el is None:
            continue
        tag = await el.evaluate("el => el.tagName.toLowerCase()")
        if tag == "select":
            await el.select_option(value)
        else:
            await el.fill(value)
    if submit:
        await page.keyboard.press("Enter")
