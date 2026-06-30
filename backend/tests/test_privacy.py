"""Manual smoke test for the privacy module — Tor port/exit-IP check, and a stealth
browser fetch via the engine.

Requires: a Tor client running locally on port 9050 for the Tor checks to pass (Tor
checks degrade gracefully and just report tor_port_open=False if not running — they
are not hard failures of this test). `pip install socksio` (or rerun
`pip install -r requirements.txt`) before running.

Run from the backend directory with the venv active:
    python -m tests.test_privacy
"""
import asyncio

from app.privacy import tor_proxy
from app.browser.engine import engine as browser_engine


async def main():
    print("--- tor: port check ---")
    port_open = tor_proxy.is_port_open()
    print(f"port_open={port_open}")

    if port_open:
        print("\n--- tor: exit IP verification ---")
        try:
            result = await tor_proxy.check_exit_ip()
            print(result)
        except Exception as e:
            print(f"FAILED: {e}")
    else:
        print("(skipping exit-IP check — Tor not running on 127.0.0.1:9050)")

    print("\n--- stealth fetch (no tor) ---")
    try:
        result = await browser_engine.fetch("https://example.com", stealth=True)
        print(f"title={result['title']!r}, html_len={len(result['html'])}")
    except Exception as e:
        print(f"FAILED: {e}")

    if port_open:
        print("\n--- stealth + tor fetch ---")
        try:
            result = await browser_engine.fetch("https://example.com", tor=True, stealth=True)
            print(f"title={result['title']!r}, html_len={len(result['html'])}")
        except Exception as e:
            print(f"FAILED: {e}")

    await browser_engine.stop()


if __name__ == "__main__":
    asyncio.run(main())
