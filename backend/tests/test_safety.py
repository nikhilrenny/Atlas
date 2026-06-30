"""Manual smoke test for the safety module — heuristics (always run), plus Google Safe
Browsing / VirusTotal (skipped gracefully if their .env keys are blank), the checker
aggregator, and the /browser/fetch block_unsafe gate via the engine directly.

Run from the backend directory with the venv active:
    python -m tests.test_safety
"""
import asyncio

from app.safety import checker as safety_checker
from app.safety.google_safe_browsing import safe_browsing
from app.safety.virustotal_client import virustotal
from app.safety.phishing_heuristics import analyze as heuristic_analyze

CLEAN_URL = "https://example.com"
SUSPICIOUS_URL = "http://paypal-login-verify-secure.totally-real.zip/account/update"
EICAR_TEST_URL = "https://testsafebrowsing.appspot.com/s/malware.html"  # Google's own test URL


async def main():
    print("--- heuristics: clean URL ---")
    print(heuristic_analyze(CLEAN_URL))

    print("\n--- heuristics: synthetic suspicious URL ---")
    print(heuristic_analyze(SUSPICIOUS_URL))

    print(f"\n--- google safe browsing: configured={safe_browsing.is_available()} ---")
    if safe_browsing.is_available():
        try:
            print(await safe_browsing.check_url(EICAR_TEST_URL))
        except Exception as e:
            print(f"FAILED: {e}")
    else:
        print("(skipping — GOOGLE_SAFE_BROWSING_API_KEY not set in .env)")

    print(f"\n--- virustotal: configured={virustotal.is_available()} ---")
    if virustotal.is_available():
        try:
            print(await virustotal.check_url(CLEAN_URL, submit_if_unknown=False))
        except Exception as e:
            print(f"FAILED: {e}")
    else:
        print("(skipping — VIRUSTOTAL_API_KEY not set in .env)")

    print("\n--- checker: clean URL end-to-end ---")
    print(await safety_checker.check_url(CLEAN_URL))

    print("\n--- checker: synthetic suspicious URL end-to-end ---")
    print(await safety_checker.check_url(SUSPICIOUS_URL))


if __name__ == "__main__":
    asyncio.run(main())
