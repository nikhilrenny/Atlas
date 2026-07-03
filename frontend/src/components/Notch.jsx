import { useEffect, useState } from "react";
import ToolPanel from "./ToolPanel";

const API = "http://127.0.0.1:8765/api";

const DOT_COLORS = { lookup: "#6366F1", tool_execution: "#10B981", page_visit: "#F59E0B" };

export default function Notch({ onNavigate, open, onToggle, onClose }) {
  const [tools, setTools] = useState([]);
  const [activity, setActivity] = useState([]);
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    if (!open) return;
    fetch(`${API}/toolbuilder/tools`)
      .then(r => r.json())
      .then(d => setTools((d.tools || []).filter(t => t.pinned)));
    fetch(`${API}/memory?limit=8`)
      .then(r => r.json())
      .then(d => setActivity(d.memories || []));
  }, [open]);

  const expandedTool = tools.find(t => t.id === expandedId);

  return (
    <>
      {open && (
        <div
          style={{ position: "fixed", inset: 0, zIndex: 98 }}
          onClick={onClose}
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
                  <div
                    key={t.id}
                    className={`notch-tool-card ${expandedId === t.id ? "notch-tool-card-active" : ""}`}
                    onClick={() => setExpandedId(id => (id === t.id ? null : t.id))}
                  >
                    <p className="notch-tool-name">{t.name}</p>
                    <p className="notch-tool-pattern">{t.pattern}</p>
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
        <div className={`notch-pill ${open ? "open" : ""}`} onClick={onToggle}>
          <div className="notch-pill-dot" />
          <div className="notch-pill-dot" />
          <div className="notch-pill-dot" />
        </div>
      </div>

      {expandedTool && (
        <div className="notch-tool-modal-backdrop" onClick={() => setExpandedId(null)}>
          <div className="notch-tool-modal-card" onClick={e => e.stopPropagation()}>
            <button className="notch-tool-modal-close" onClick={() => setExpandedId(null)} aria-label="Close">&times;</button>
            <ToolPanel manifest={expandedTool} />
          </div>
        </div>
      )}
    </>
  );
}
