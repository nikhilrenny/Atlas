"""Structured extraction helpers — links and form fields from a live Playwright Page.

This is the raw material both for form-filling automation (this phase) and for the
tool-builder phase later, which classifies a page's pattern from exactly this kind of
structured data before writing a manifest + implementation for it.
"""
from playwright.async_api import Page


async def extract_links(page: Page) -> list[dict]:
    """Returns every visible <a href> on the page as {text, href}."""
    return await page.eval_on_selector_all(
        "a[href]",
        "els => els.map(e => ({text: e.innerText.trim(), href: e.href}))",
    )


async def extract_forms(page: Page) -> list[dict]:
    """Returns each <form>'s action/method and its input/select/textarea fields —
    everything fill_form() needs to populate the form automatically."""
    return await page.eval_on_selector_all(
        "form",
        """
        forms => forms.map(f => ({
            action: f.action,
            method: f.method,
            fields: Array.from(f.querySelectorAll('input,select,textarea')).map(el => ({
                name: el.name,
                type: el.type || el.tagName.toLowerCase(),
                placeholder: el.placeholder || null,
                required: el.required,
            }))
        }))
        """,
    )
