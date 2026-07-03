import { useEffect, useState } from "react";

const API = "http://127.0.0.1:8765/api";

const TOGGLES = [
  { key: "prefer_free", label: "Prefer free routing", hint: "Try Claude Pro (OAuth) before paid API on mid/high complexity." },
  { key: "default_tor", label: "Tor by default", hint: "Browser fetch/screenshot route through Tor unless overridden per-call." },
  { key: "default_stealth", label: "Stealth fingerprint by default", hint: "Randomised fingerprint on every browse unless overridden per-call." },
  { key: "default_block_unsafe", label: "Block unsafe URLs by default", hint: "403 on a \"dangerous\" safety verdict before navigating." },
];

function Toggle({ checked, onChange }) {
  return (
    <button
      className={`settings-toggle ${checked ? "settings-toggle-on" : ""}`}
      onClick={() => onChange(!checked)}
      role="switch"
      aria-checked={checked}
    >
      <span className="settings-toggle-knob" />
    </button>
  );
}

function ProviderRow({ label, info }) {
  if (!info) return null;
  return (
    <div className="settings-diag-row">
      <span className={`settings-diag-dot ${info.available ? "up" : "down"}`} />
      <span className="settings-diag-label">{label}</span>
      <span className="settings-diag-meta">{info.available ? (info.models?.length ? `${info.models.length} model(s)` : "available") : "unavailable"}</span>
    </div>
  );
}

// AI model providers only -- security/utility APIs (Safe Browsing, VirusTotal)
// get their own place later, this is strictly "where do my models come from."
const PROVIDER_LINKS = [
  { name: "Anthropic (Claude API)", url: "https://console.anthropic.com" },
  { name: "Claude Pro (account)", url: "https://claude.ai/settings/usage" },
  { name: "NVIDIA NIM", url: "https://build.nvidia.com" },
  { name: "OpenAI", url: "https://platform.openai.com" },
  { name: "ElevenLabs", url: "https://elevenlabs.io/app/usage" },
  { name: "RunwayML", url: "https://app.runwayml.com" },
  { name: "Ideogram", url: "https://ideogram.ai" },
  { name: "Ollama (local)", url: "https://ollama.com/library" },
];

export default function SettingsPanel({ onClose }) {
  const [settings, setSettings] = useState(null);
  const [diag, setDiag] = useState(null);
  const [diagLoading, setDiagLoading] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);
  const [status, setStatus] = useState("");

  useEffect(() => {
    fetch(`${API}/settings`).then(r => r.json()).then(setSettings).catch(() => {});
  }, []);

  const patch = async (key, value) => {
    setSettings(s => ({ ...s, [key]: value })); // optimistic
    try {
      const res = await fetch(`${API}/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ [key]: value }),
      });
      const body = await res.json();
      setSettings(body);
    } catch {
      // leave optimistic value -- next open will resync from the server
    }
  };

  const loadDiagnostics = async () => {
    setDiagLoading(true);
    try {
      const res = await fetch(`${API}/settings/diagnostics`);
      setDiag(await res.json());
    } catch {
      setDiag({ _error: "backend unreachable" });
    } finally {
      setDiagLoading(false);
    }
  };

  const clearMemory = async () => {
    if (!confirmClear) { setConfirmClear(true); return; }
    const res = await fetch(`${API}/memory/clear`, { method: "DELETE" });
    const body = await res.json();
    setStatus(`Cleared ${body.cleared} memory record(s).`);
    setConfirmClear(false);
  };

  const resetUsage = async () => {
    await fetch(`${API}/dev/usage/reset`, { method: "POST" });
    setStatus("Usage log reset.");
  };

  return (
    <div className="settings-modal-backdrop" onClick={onClose}>
      <div className="settings-modal-card" onClick={e => e.stopPropagation()}>
        <button className="settings-modal-close" onClick={onClose} aria-label="Close">&times;</button>
        <h3 className="settings-title">Settings</h3>

        <div className="settings-section">
          <h4>Model routing & defaults</h4>
          {!settings && <p className="settings-empty">Loading…</p>}
          {settings && TOGGLES.slice(0, 1).map(t => (
            <div className="settings-row" key={t.key}>
              <div>
                <p className="settings-row-label">{t.label}</p>
                <p className="settings-row-hint">{t.hint}</p>
              </div>
              <Toggle checked={settings[t.key]} onChange={(v) => patch(t.key, v)} />
            </div>
          ))}
        </div>

        <div className="settings-section">
          <h4>Privacy & safety defaults</h4>
          {settings && TOGGLES.slice(1).map(t => (
            <div className="settings-row" key={t.key}>
              <div>
                <p className="settings-row-label">{t.label}</p>
                <p className="settings-row-hint">{t.hint}</p>
              </div>
              <Toggle checked={settings[t.key]} onChange={(v) => patch(t.key, v)} />
            </div>
          ))}
        </div>

        <div className="settings-section">
          <h4>Data & memory</h4>
          <div className="settings-actions">
            <button className="btn-ghost" onClick={resetUsage}>Reset usage log</button>
            <button className={`btn-ghost ${confirmClear ? "settings-danger-confirm" : ""}`} onClick={clearMemory}>
              {confirmClear ? "Click again to confirm" : "Clear all memory"}
            </button>
          </div>
          {status && <p className="settings-status">{status}</p>}
        </div>

        <div className="settings-section">
          <h4>AI models</h4>
          <div className="settings-provider-grid">
            {PROVIDER_LINKS.map(p => (
              <a key={p.name} className="settings-provider-link" href={p.url} target="_blank" rel="noopener noreferrer">
                <span>{p.name}</span>
                <svg viewBox="0 0 24 24" fill="none"><path d="M7 17 17 7M9 7h8v8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>
              </a>
            ))}
          </div>
        </div>

        <div className="settings-section">
          <h4>System diagnostics</h4>
          {!diag && (
            <button className="btn-ghost" onClick={loadDiagnostics} disabled={diagLoading}>
              {diagLoading ? "Checking…" : "Run diagnostics"}
            </button>
          )}
          {diag?._error && <p className="settings-status">{diag._error}</p>}
          {diag && !diag._error && (
            <>
              <ProviderRow label="Ollama" info={diag.ollama} />
              <ProviderRow label="NVIDIA NIM" info={diag.nim} />
              <ProviderRow label="Claude API" info={diag.claude_api} />
              <ProviderRow label="Claude Pro (OAuth)" info={diag.claude_oauth} />
              <ProviderRow label="OpenAI" info={diag.openai} />
              {diag.gpu ? (
                <div className="settings-gpu">
                  <p className="settings-row-label">{diag.gpu.name}</p>
                  <p className="settings-row-hint">
                    {diag.gpu.memory_used_mb} / {diag.gpu.memory_total_mb} MB VRAM · {diag.gpu.utilization_pct}% util
                  </p>
                </div>
              ) : (
                <p className="settings-row-hint">GPU info unavailable (nvidia-smi not found or not an NVIDIA machine).</p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
