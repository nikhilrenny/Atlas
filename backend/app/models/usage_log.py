"""Cost + latency logging for the model router — closes out Phase 1.

Every call through ModelRouter._dispatch() gets timed and recorded as one JSON line in
data/usage_log.jsonl. This is the only metered cost data Atlas has (Ollama and NIM's free
tier are $0; Claude OAuth draws against the Pro subscription, not pay-per-token, so it's
logged at $0 too — only requests that actually fall back to Claude API key billing carry
a nonzero cost).

Pricing is current Anthropic per-MTok rates (input/output), checked June 2026:
    Haiku 4.5:  $1 / $5
    Sonnet 4.6: $3 / $15
Token counts come from the Anthropic SDK's response.usage when available (claude_api path
only — Ollama/NIM/OAuth don't return billable usage in a comparable form, so their cost is
fixed at $0 and only latency/char-length are tracked for them).
"""
import json
import time
from contextlib import contextmanager
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parents[3] / "data" / "usage_log.jsonl"

# $ per million tokens: (input, output)
PRICING_PER_MTOK = {
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "claude-sonnet-4-6": (3.0, 15.0),
}


def estimate_cost(model: str | None, input_tokens: int | None, output_tokens: int | None) -> float:
    """Returns $0.0 for unknown models or missing token counts (free/unmetered providers)."""
    if not model or input_tokens is None or output_tokens is None:
        return 0.0
    rates = PRICING_PER_MTOK.get(model)
    if not rates:
        return 0.0
    in_rate, out_rate = rates
    return (input_tokens / 1_000_000) * in_rate + (output_tokens / 1_000_000) * out_rate


class UsageLog:
    """Append-only JSONL writer. One record per _dispatch() call, success or failure."""

    def __init__(self, path: Path = LOG_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        *,
        provider: str,
        complexity: str,
        latency_ms: float,
        prompt_chars: int,
        response_chars: int = 0,
        model: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        error: str | None = None,
    ) -> None:
        entry = {
            "ts": time.time(),
            "provider": provider,
            "complexity": complexity,
            "model": model,
            "latency_ms": round(latency_ms, 1),
            "prompt_chars": prompt_chars,
            "response_chars": response_chars,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": estimate_cost(model, input_tokens, output_tokens),
            "error": error,
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def read_all(self) -> list[dict]:
        if not self.path.exists():
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def reset(self) -> None:
        """Truncates the log -- used by the Settings panel's 'reset usage log' action."""
        with open(self.path, "w", encoding="utf-8"):
            pass

    def summary(self) -> dict:
        """Quick aggregate: total cost, total calls, calls/cost broken down by provider."""
        rows = self.read_all()
        by_provider: dict[str, dict] = {}
        total_cost = 0.0
        for r in rows:
            p = r["provider"]
            bucket = by_provider.setdefault(p, {"calls": 0, "cost_usd": 0.0, "avg_latency_ms": 0.0})
            bucket["calls"] += 1
            bucket["cost_usd"] += r["cost_usd"]
            bucket["avg_latency_ms"] += r["latency_ms"]
            total_cost += r["cost_usd"]
        for bucket in by_provider.values():
            bucket["avg_latency_ms"] = round(bucket["avg_latency_ms"] / bucket["calls"], 1)
            bucket["cost_usd"] = round(bucket["cost_usd"], 6)
        return {"total_calls": len(rows), "total_cost_usd": round(total_cost, 6), "by_provider": by_provider}


@contextmanager
def timer():
    """Yields a callable that returns elapsed milliseconds since the `with` block started."""
    start = time.perf_counter()
    yield lambda: (time.perf_counter() - start) * 1000


usage_log = UsageLog()
