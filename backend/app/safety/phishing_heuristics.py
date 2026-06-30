"""Lightweight URL heuristics — Phase 7 (safety).

No ML model, no third-party call — a fast, local, zero-cost first pass that catches
the cheapest phishing/scam tells (IP-literal hosts, punycode/homograph domains,
suspicious TLDs, a brand keyword present but not the actual registrable domain,
excessive subdomain nesting, '@' tricks in the URL, credential-bait keyword stacking).
Runs on every check regardless of whether the Google/VirusTotal API keys are
configured, so Atlas always has *some* signal with zero external dependencies.
"""
import re
from urllib.parse import urlparse

SUSPICIOUS_TLDS = {"zip", "mov", "top", "xyz", "click", "country", "gq", "cf", "tk", "ml"}

BRAND_KEYWORDS = {
    "paypal", "amazon", "apple", "microsoft", "google", "netflix", "bankofamerica",
    "chase", "wellsfargo", "facebook", "instagram", "coinbase", "binance",
}

CREDENTIAL_BAIT_WORDS = {"login", "signin", "verify", "secure", "update", "confirm", "account", "billing"}

IP_LITERAL_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


def _registrable_label(host: str) -> str:
    """Crude eTLD+1 first label (e.g. 'paypal' from 'secure.paypal.com.evil.net' would
    incorrectly return 'evil' here — that's fine, the false negative is acceptable for
    a zero-dependency heuristic; the external APIs are the real safety net)."""
    parts = host.split(".")
    return parts[-2].lower() if len(parts) >= 2 else host.lower()


def analyze(url: str) -> dict:
    """Returns {"score": 0-100 (higher = more suspicious), "reasons": [...]}."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    full_url_lower = url.lower()
    reasons = []
    score = 0

    if IP_LITERAL_RE.match(host):
        reasons.append("Host is a raw IP address, not a domain name")
        score += 30

    if "xn--" in host:
        reasons.append("Punycode domain — possible homograph/lookalike attack")
        score += 35

    authority = url.split("://", 1)[-1].split("/", 1)[0]
    if "@" in authority:
        reasons.append("'@' in the authority section can hide the real destination host")
        score += 30

    tld = host.rsplit(".", 1)[-1] if "." in host else ""
    if tld in SUSPICIOUS_TLDS:
        reasons.append(f"TLD '.{tld}' is disproportionately used for scam/spam domains")
        score += 15

    if host.count(".") >= 4:
        reasons.append("Unusually deep subdomain nesting, a common cloaking trick")
        score += 15

    registrable = _registrable_label(host)
    for brand in BRAND_KEYWORDS:
        if brand in full_url_lower and brand != registrable:
            reasons.append(f"References brand '{brand}' but the domain itself is not {brand}'s own domain")
            score += 25
            break

    bait_hits = sum(1 for w in CREDENTIAL_BAIT_WORDS if w in full_url_lower)
    if bait_hits >= 2:
        reasons.append("Multiple credential-bait keywords in the URL (login/verify/secure/...)")
        score += 10 * min(bait_hits, 3)

    return {"score": min(score, 100), "reasons": reasons}
