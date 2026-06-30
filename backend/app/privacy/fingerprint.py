"""Fingerprint stealth for Playwright contexts — Phase 6 (privacy).

Hand-rolled rather than a pulling in `playwright-stealth` or `playwright-extra`,
matching the project's lean-deps pattern (git via subprocess, media via raw
httpx). This covers the handful of signals that are actually checked by common
bot/fingerprint detectors and that a plain Playwright/Chromium session fails
by default:

  - navigator.webdriver === true        (the single biggest tell)
  - navigator.plugins.length === 0      (headless Chrome has none)
  - navigator.languages === []          (headless Chrome leaves this empty)
  - window.chrome missing               (headless Chrome omits the chrome object)
  - Permissions API notification quirk  (a known automation-only behavior)

This is NOT a guarantee against sophisticated fingerprinting (canvas/WebGL
hashing, TLS fingerprinting, behavioral analysis are all out of scope here) —
it raises the bar against the common checks, it doesn't make Atlas invisible.
"""
import random

# A short rotation of recent, real desktop Chrome UAs. Keeping this list small
# and current matters more than having many entries — a stale UA is itself a
# fingerprinting signal.
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
]

STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5].map(() => ({ name: 'Chrome PDF Plugin' })),
});

Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
});

window.chrome = window.chrome || { runtime: {} };

const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters)
);
"""


def random_context_kwargs() -> dict:
    """Random-but-plausible user_agent + viewport pairing for a new browser context."""
    return {
        "user_agent": random.choice(USER_AGENTS),
        "viewport": random.choice(VIEWPORTS),
        "locale": "en-US",
        "timezone_id": "America/New_York",
    }


async def apply_stealth(page) -> None:
    """Injects the stealth init script. Must run before any page navigation —
    call this on a freshly-created Page, before goto()."""
    await page.add_init_script(STEALTH_INIT_SCRIPT)
