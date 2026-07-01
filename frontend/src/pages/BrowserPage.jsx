import { useState } from "react";

const API = "http://127.0.0.1:8765/api";

export default function BrowserPage({ initialUrl = "" }) {
  const [url, setUrl] = useState(initialUrl.startsWith("http") ? initialUrl : initialUrl ? `https://${initialUrl}` : "");
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(null);
  const [error, setError] = useState(null);

  const fetch_ = async (target) => {
    const u = target || url;
    if (!u) return;
    setLoading(true); setError(null); setPage(null);
    try {
      const res = await fetch(`${API}/browser/fetch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: u.startsWith("http") ? u : `https://${u}`, store: false, block_unsafe: false }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "fetch failed");
      setPage(data);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  // auto-fetch if initialUrl provided
  useState(() => { if (initialUrl) fetch_(initialUrl.startsWith("http") ? initialUrl : `https://${initialUrl}`); }, []);

  return (
    <div>
      <div className="browser-bar">
        <input
          value={url}
          onChange={e => setUrl(e.target.value)}
          onKeyDown={e => e.key === "Enter" && fetch_()}
          placeholder="https://..."
          style={{ fontFamily: "'JetBrains Mono', monospace" }}
        />
        <button className="btn-primary" onClick={() => fetch_()} disabled={loading}>
          {loading ? "Loading…" : "Go"}
        </button>
      </div>
      {error && <p style={{ color: "var(--danger)", fontSize: "0.85rem", marginBottom: "0.75rem" }}>{error}</p>}
      {page && (
        <div className="browser-frame">
          <p style={{ fontSize: "0.72rem", color: "var(--text-3)", marginBottom: "0.75rem" }}>
            {page.title} — {page.url}
          </p>
          {page.text}
        </div>
      )}
      {!page && !loading && !error && (
        <div className="browser-frame" style={{ color: "var(--text-3)", display: "flex", alignItems: "center", justifyContent: "center" }}>
          Enter a URL and press Go
        </div>
      )}
    </div>
  );
}
