import { useEffect, useRef, useState } from "react";

const API = "http://127.0.0.1:8765/api";
const LEVEL_COLORS = { INFO: "var(--text-2)", WARNING: "var(--accent)", ERROR: "var(--danger)", DEBUG: "var(--text-3)" };

export default function ScriptsPanel({ onClose }) {
  const [entries, setEntries] = useState([]);
  const lastId = useRef(0);
  const bodyRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const res = await fetch(`${API}/dev/activity?after_id=${lastId.current}&limit=200`);
        const data = await res.json();
        if (cancelled || !data.entries?.length) return;
        lastId.current = data.entries[data.entries.length - 1].id;
        const body = bodyRef.current;
        const wasNearBottom = body && body.scrollHeight - body.scrollTop - body.clientHeight < 40;
        setEntries(prev => [...prev, ...data.entries].slice(-500));
        if (wasNearBottom) {
          requestAnimationFrame(() => { if (body) body.scrollTop = body.scrollHeight; });
        }
      } catch {
        // backend not reachable -- just skip this tick, next poll will retry
      }
    };
    poll();
    const interval = setInterval(poll, 1000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  return (
    <div className="scripts-panel">
      <div className="scripts-panel-header">
        <span>Scripts Mode</span>
        <button className="scripts-panel-close" onClick={onClose} aria-label="Close Scripts Mode">&times;</button>
      </div>
      <div className="scripts-panel-body" ref={bodyRef}>
        {entries.length === 0 && <p className="scripts-panel-empty">Waiting for activity\u2026</p>}
        {entries.map(e => (
          <div key={e.id} className="scripts-line">
            <span className="scripts-line-time">{new Date(e.ts * 1000).toLocaleTimeString()}</span>
            <span className="scripts-line-msg" style={{ color: LEVEL_COLORS[e.level] || "var(--text-2)" }}>{e.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
