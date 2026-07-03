import { useEffect, useState } from "react";

const API = "http://127.0.0.1:8765/api";

// Providers with real per-token $ billing -- these roll into the headline total.
const PAID_PREFIXES = ["claude_api", "dev:claude_api", "dev:openai", "openai"];
// Free-tier-of-a-subscription providers -- no $ cost, but still worth a call count
// since Claude Pro's usage caps aren't something Atlas can query directly.
const SUBSCRIPTION_PREFIXES = ["claude_oauth", "dev:claude_oauth"];

const LABELS = {
  claude_api_haiku: "Claude Haiku",
  claude_api_sonnet: "Claude Sonnet",
  claude_oauth: "Claude Pro",
  "dev:claude_api": "Claude API (dev)",
  "dev:claude_oauth": "Claude Pro (dev)",
  "dev:openai": "OpenAI (dev)",
  openai: "OpenAI",
};

function isPaid(provider) {
  return PAID_PREFIXES.some(p => provider.startsWith(p));
}
function isSubscription(provider) {
  return SUBSCRIPTION_PREFIXES.some(p => provider.startsWith(p));
}

export default function UsageWidget({ open, onToggle, onClose }) {
  const [usage, setUsage] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const res = await fetch(`${API}/dev/usage`);
        const data = await res.json();
        if (!cancelled) setUsage(data);
      } catch {
        // backend not reachable -- keep showing last known value
      }
    };
    poll();
    const interval = setInterval(poll, 5000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  if (!usage) return null;

  const paidRows = Object.entries(usage.by_provider).filter(([p]) => isPaid(p));
  const subRows = Object.entries(usage.by_provider).filter(([p]) => isSubscription(p));
  const totalCost = usage.total_cost_usd;

  return (
    <>
      {open && (
        <div style={{ position: "fixed", inset: 0, zIndex: 997 }} onClick={onClose} />
      )}
      <div className="usage-widget">
        <button className="usage-pill" onClick={onToggle}>
          <span className="usage-pill-dot" />
          ${totalCost.toFixed(4)}
        </button>
        {open && (
          <div className="usage-panel">
            <div className="usage-panel-title">Credit usage (this log)</div>
            {paidRows.length === 0 && subRows.length === 0 && (
              <div className="usage-empty">No paid or Pro calls logged yet.</div>
            )}
            {paidRows.map(([provider, stats]) => (
              <div className="usage-row" key={provider}>
                <span className="usage-row-label">{LABELS[provider] || provider}</span>
                <span className="usage-row-calls">{stats.calls} calls</span>
                <span className="usage-row-cost">${stats.cost_usd.toFixed(4)}</span>
              </div>
            ))}
            {subRows.map(([provider, stats]) => (
              <div className="usage-row usage-row-sub" key={provider}>
                <span className="usage-row-label">{LABELS[provider] || provider}</span>
                <span className="usage-row-calls">{stats.calls} calls</span>
                <span className="usage-row-cost">free (Pro)</span>
              </div>
            ))}
            <div className="usage-panel-footer">
              Pro usage counts calls only -- Anthropic doesn't expose remaining quota, so there's no $ or % to show.
            </div>
          </div>
        )}
      </div>
    </>
  );
}
