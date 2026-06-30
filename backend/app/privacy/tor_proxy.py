"""Tor SOCKS5 proxy integration — Phase 6 (privacy).

Assumes a Tor client (Tor Browser, or the standalone `tor` service/Windows
service) is already running on the machine with its default SOCKS port. Atlas
does not launch or manage the Tor process itself — that's an external
dependency the user starts once, same way Ollama is treated as a system
service rather than something Atlas bundles or spawns.
"""
import socket

import httpx

TOR_SOCKS_HOST = "127.0.0.1"
TOR_SOCKS_PORT = 9050  # Tor default; Tor Browser uses 9150 instead
TOR_CHECK_URL = "https://check.torproject.org/api/ip"


def get_proxy_config(port: int = TOR_SOCKS_PORT) -> dict:
    """Returns the dict Playwright's launch()/new_context() `proxy` kwarg expects."""
    return {"server": f"socks5://{TOR_SOCKS_HOST}:{port}"}


def get_httpx_proxy_url(port: int = TOR_SOCKS_PORT) -> str:
    """httpx proxy URL form — requires the `socksio` package (httpx[socks])."""
    return f"socks5://{TOR_SOCKS_HOST}:{port}"


def is_port_open(port: int = TOR_SOCKS_PORT, timeout_s: float = 0.5) -> bool:
    """Cheap local check: is something listening on the Tor SOCKS port at all.

    This does NOT confirm it's actually Tor or that circuits are healthy — just
    that the port is open, which is enough to decide whether to attempt routing
    through it.
    """
    try:
        with socket.create_connection((TOR_SOCKS_HOST, port), timeout=timeout_s):
            return True
    except OSError:
        return False


async def check_exit_ip(port: int = TOR_SOCKS_PORT, timeout_s: float = 10.0) -> dict:
    """Confirms Tor is actually working by hitting the Tor Project's own IP-check
    API through the proxy. Returns {is_tor: bool, ip: str} or raises on failure.

    This is the real verification — is_port_open() only tells you a socket is
    listening, not that traffic is actually exiting through the Tor network.
    """
    proxy = get_httpx_proxy_url(port)
    async with httpx.AsyncClient(proxy=proxy, timeout=timeout_s) as client:
        resp = await client.get(TOR_CHECK_URL)
        resp.raise_for_status()
        return resp.json()
