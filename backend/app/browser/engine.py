"""Playwright-based browser engine — handles JS-rendered pages reliably (unlike
BeautifulSoup/Scrapy), and doubles as the automation layer for form-filling now and
anonymous browsing (Tor + stealth) later.

One shared Playwright + Browser process is kept alive across requests; each call to
page() opens a fresh, isolated browser *context* (separate cookies/storage) so unrelated
fetches never bleed into each other, without paying the cost of relaunching the browser
binary every time.
"""
import asyncio
from contextlib import asynccontextmanager

from playwright.async_api import async_playwright, Browser, Playwright

from app.privacy import fingerprint, tor_proxy


class BrowserEngine:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._lock = asyncio.Lock()

    async def start(self):
        async with self._lock:
            if self._browser is None:
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(headless=self.headless)

    async def stop(self):
        async with self._lock:
            if self._browser is not None:
                await self._browser.close()
                self._browser = None
            if self._playwright is not None:
                await self._playwright.stop()
                self._playwright = None

    @asynccontextmanager
    async def page(self, tor: bool = False, stealth: bool = False, **context_kwargs):
        """Yields a fresh Page in its own isolated context. The context (not just the
        page) is closed on exit so cookies/storage don't leak between fetches.

        tor: route this context's traffic through the local Tor SOCKS proxy
            (app.privacy.tor_proxy). Caller is responsible for having Tor running.
        stealth: apply fingerprint randomization + the stealth init script
            (app.privacy.fingerprint) so this context doesn't trip the common
            headless-Chrome checks.
        Remaining context_kwargs are passed straight to browser.new_context(),
        and override any defaults stealth=True would otherwise set.
        """
        await self.start()

        if stealth:
            context_kwargs = {**fingerprint.random_context_kwargs(), **context_kwargs}
        if tor:
            context_kwargs = {**context_kwargs, "proxy": tor_proxy.get_proxy_config()}

        context = await self._browser.new_context(**context_kwargs)
        try:
            page = await context.new_page()
            if stealth:
                await fingerprint.apply_stealth(page)
            try:
                yield page
            finally:
                await page.close()
        finally:
            await context.close()

    async def fetch(
        self, url: str, wait_until: str = "networkidle", timeout_ms: int = 30000,
        tor: bool = False, stealth: bool = False,
    ) -> dict:
        """Navigates to a URL and returns rendered HTML, plain text, and title."""
        async with self.page(tor=tor, stealth=stealth) as page:
            await page.goto(url, wait_until=wait_until, timeout=timeout_ms)
            return {
                "url": url,
                "title": await page.title(),
                "html": await page.content(),
                "text": await page.inner_text("body"),
            }

    async def screenshot(
        self, url: str, full_page: bool = True, timeout_ms: int = 30000,
        tor: bool = False, stealth: bool = False,
    ) -> bytes:
        async with self.page(tor=tor, stealth=stealth) as page:
            await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            return await page.screenshot(full_page=full_page)


engine = BrowserEngine()
