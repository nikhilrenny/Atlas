"""VirusTotal v3 client — Phase 7 (safety).

Submits a URL for analysis and polls for the verdict. VirusTotal's free public API
tier is rate-limited (4 requests/min, 500/day as of 2026) — this client is meant for
on-demand checks of individual URLs, not bulk scanning. See
https://docs.virustotal.com/reference/url for the underlying API.
"""
import asyncio
import base64
import os

import httpx

API_BASE = "https://www.virustotal.com/api/v3"

EMPTY_RESULT = {"safe": True, "malicious": 0, "suspicious": 0, "harmless": 0, "undetected": 0, "scanned": False}


def _url_id(url: str) -> str:
    """VT identifies URLs by the unpadded base64 of the URL string."""
    return base64.urlsafe_b64encode(url.encode()).decode().strip("=")


class VirusTotalClient:
    def __init__(self):
        self.api_key = os.environ.get("VIRUSTOTAL_API_KEY")

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def check_url(self, url: str, submit_if_unknown: bool = True, poll_timeout_s: float = 20.0) -> dict:
        """Returns {"safe", "malicious", "suspicious", "harmless", "undetected", "scanned"}.
        If VT has no existing report and submit_if_unknown=True, submits the URL and
        polls briefly; otherwise returns scanned=False with zeroed counts rather than
        blocking on a fresh scan.
        """
        if not self.api_key:
            raise RuntimeError("VIRUSTOTAL_API_KEY not set")
        headers = {"x-apikey": self.api_key}
        async with httpx.AsyncClient(timeout=10, headers=headers) as client:
            r = await client.get(f"{API_BASE}/urls/{_url_id(url)}")
            if r.status_code == 404:
                if not submit_if_unknown:
                    return dict(EMPTY_RESULT)
                return await self._submit_and_poll(client, url, poll_timeout_s)
            r.raise_for_status()
            return self._parse_stats(r.json())

    async def _submit_and_poll(self, client: httpx.AsyncClient, url: str, timeout_s: float) -> dict:
        sub = await client.post(f"{API_BASE}/urls", data={"url": url})
        sub.raise_for_status()
        analysis_id = sub.json()["data"]["id"]

        elapsed, interval = 0.0, 3.0
        while elapsed < timeout_s:
            await asyncio.sleep(interval)
            elapsed += interval
            ar = await client.get(f"{API_BASE}/analyses/{analysis_id}")
            ar.raise_for_status()
            data = ar.json()
            if data["data"]["attributes"]["status"] == "completed":
                return self._stats_to_result(data["data"]["attributes"]["stats"])
        # VT is still processing past our poll budget — report unscanned rather than guess
        return dict(EMPTY_RESULT)

    def _parse_stats(self, data: dict) -> dict:
        return self._stats_to_result(data["data"]["attributes"]["last_analysis_stats"])

    def _stats_to_result(self, stats: dict) -> dict:
        return {
            "safe": stats.get("malicious", 0) == 0 and stats.get("suspicious", 0) == 0,
            "malicious": stats.get("malicious", 0),
            "suspicious": stats.get("suspicious", 0),
            "harmless": stats.get("harmless", 0),
            "undetected": stats.get("undetected", 0),
            "scanned": True,
        }


virustotal = VirusTotalClient()
