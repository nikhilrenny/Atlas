"""Google Safe Browsing v4 client — Phase 7 (safety).

Checks a URL against Google's threat lists (malware, social engineering, unwanted
software, potentially harmful applications) via the Lookup API
(https://developers.google.com/safe-browsing/v4/lookup-api). Free, but requires an
API key from Google Cloud Console with the Safe Browsing API enabled.
"""
import os

import httpx

API_URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find"

THREAT_TYPES = [
    "MALWARE",
    "SOCIAL_ENGINEERING",
    "UNWANTED_SOFTWARE",
    "POTENTIALLY_HARMFUL_APPLICATION",
]


class SafeBrowsingClient:
    def __init__(self):
        self.api_key = os.environ.get("GOOGLE_SAFE_BROWSING_API_KEY")

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def check_url(self, url: str) -> dict:
        """Returns {"safe": bool, "threats": [...]} — threats is empty if clean.
        Raises RuntimeError if no API key is configured."""
        if not self.api_key:
            raise RuntimeError("GOOGLE_SAFE_BROWSING_API_KEY not set")
        payload = {
            "client": {"clientId": "atlas", "clientVersion": "0.1.0"},
            "threatInfo": {
                "threatTypes": THREAT_TYPES,
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": url}],
            },
        }
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(API_URL, params={"key": self.api_key}, json=payload)
            r.raise_for_status()
            data = r.json()
        matches = data.get("matches", [])
        return {
            "safe": not matches,
            "threats": [m["threatType"] for m in matches],
        }


safe_browsing = SafeBrowsingClient()
