"""Safety checker aggregator — Phase 7.

Combines Google Safe Browsing, VirusTotal, and local heuristics into one verdict.
Both external APIs are optional (silently skipped if their key isn't configured in
.env); heuristics always run. A URL is "dangerous" if either external API reports a
real hit or heuristics score very high, "suspicious" on a moderate heuristic score or
a VirusTotal "suspicious" vendor flag, "safe" otherwise.
"""
import asyncio

from app.safety.google_safe_browsing import safe_browsing
from app.safety.virustotal_client import virustotal
from app.safety.phishing_heuristics import analyze as heuristic_analyze

HEURISTIC_SUSPICIOUS_THRESHOLD = 30
HEURISTIC_DANGEROUS_THRESHOLD = 60


async def check_url(url: str, deep_scan: bool = False) -> dict:
    """deep_scan=True lets VirusTotal submit+poll for URLs it has no report on yet
    (slower, up to ~20s); deep_scan=False only reads VT's existing report (instant)."""
    heuristics = heuristic_analyze(url)

    tasks = {}
    if safe_browsing.is_available():
        tasks["google_safe_browsing"] = safe_browsing.check_url(url)
    if virustotal.is_available():
        tasks["virustotal"] = virustotal.check_url(url, submit_if_unknown=deep_scan)

    results = {}
    if tasks:
        completed = await asyncio.gather(*tasks.values(), return_exceptions=True)
        for name, outcome in zip(tasks.keys(), completed):
            results[name] = {"error": str(outcome)} if isinstance(outcome, Exception) else outcome

    gsb_hit = bool(results.get("google_safe_browsing", {}).get("threats"))
    vt = results.get("virustotal", {}) or {}
    vt_hit = vt.get("malicious", 0) > 0

    if gsb_hit or vt_hit or heuristics["score"] >= HEURISTIC_DANGEROUS_THRESHOLD:
        verdict = "dangerous"
    elif heuristics["score"] >= HEURISTIC_SUSPICIOUS_THRESHOLD or vt.get("suspicious", 0) > 0:
        verdict = "suspicious"
    else:
        verdict = "safe"

    return {
        "url": url,
        "verdict": verdict,
        "heuristics": heuristics,
        "google_safe_browsing": results.get("google_safe_browsing"),
        "virustotal": results.get("virustotal"),
    }
