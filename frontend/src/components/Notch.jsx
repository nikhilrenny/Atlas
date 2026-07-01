import { useEffect, useState } from "react";

const API = "http://127.0.0.1:8765/api";

const DOT_COLORS = { lookup: "#6366F1", tool_execution: "#10B981", page_visit: "#F59E0B" };

export default function Notch({ onNavigate }) {
  const [open, setOpen]   = useState(false);
  const [tools, setTools] = useState([]);
  const [activity, setActivity] = useState([]);
  const [runningId, setRunningId] = useState(null);
  const [runResult, setRunResult] = useState(null);

  useEffect(() => {
    if (!open) return;
    fetch(`${API}/toolbuilder/tools`)
      .then(r => r.json())
      .then(d => setTools((d.tools || []).filter(t => t.pinned)));
    fetch(`${API}/memory?limit=8`)
      .then(r => r.json())
      .then(d => setActivity(d.memories || []));
  }, [open]);

  const quickRun = async (tool) => {
    setRunningId(tool.id);
    setRunResult(null);
    try {
      const inputs = Object.fromEntries(
        tool.inputs.filter(f => f.default != null).map(f => [f.name, f.default])
      );
      const res = await fetch(`${API}/toolbuilder/tools/${tool.id}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ inputs }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setRunResult({ id: tool.id, data: data.data, output_type: data.output_type });
    } catch (e) {
      setRunResult({ id: tool.id, error: e.message });
    } finally {
      setRunningId(null);
    }
  };

  return (
    <>
      {open && (
        <div
          style={{ position: "fixed", inset: 0, zIndex: 98 }}
          onClick={() => setOpen(false)}
        />
      )}

      {open && (
        <div className="notch-overlay" onClick={e => e.stopPropagation()}>
          <div className="notch-handle" />

          {tools.length > 0 && (
            <>
              <p className="notch-section-title">Pinned tools</p>
              <div className="notch-tools-grid">
                {tools.map(t => (
                  <div key={t.id} className="notch-tool-card" onClick={() => quickRun(t)}>
                    <p className="notch-tool-name">{t.name}</p>
                    <p className="notch-tool-pattern">{t.pattern}</p>
                    {runningId === t.id && <p style={{ fontSize: "0.72rem", color: "var(--text-3)", marginTop: "0.3rem" }}>Running…</p>}
                    {runResult?.id === t.id && runResult.error && (
                      <p style={{ fontSize: "0.72rem", color: "var(--danger)", marginTop: "0.3rem" }}>{runResult.error}</p>
                    )}
                    {runResult?.id === t.id && runResult.data != null && (
                      <p style={{ fontSize: "0.72rem", color: "var(--success)", marginTop: "0.3rem" }}>
                        {String(runResult.data).slice(0, 80)}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}

          {tools.length === 0 && (
            <p style={{ fontSize: "0.82rem", color: "var(--text-3)", marginBottom: "1.25rem" }}>
              No pinned tools yet — pin a tool from the Tool Builder to run it here.
            </p>
          )}

          <p className="notch-section-title">Recent activity</p>
          <div className="notch-activity-list">
            {activity.length === 0 && <p className="mem-empty">No activity yet.</p>}
            {activity.map(m => (
              <div key={m.id} className="notch-activity-item">
                <div className="notch-activity-dot" style={{ background: DOT_COLORS[m.type] || "#ccc" }} />
                <span>{m.content.slice(0, 90)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="notch-anchor">
        <div className={`notch-pill ${open ? "open" : ""}`} onClick={() => setOpen(o => !o)}>
          <div className="notch-pill-dot" />
          <div className="notch-pill-dot" />
          <div className="notch-pill-dot" />
        </div>
      </div>
    </>
  );
}
