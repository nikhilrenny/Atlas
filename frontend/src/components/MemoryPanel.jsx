import { useEffect, useState } from "react";

const API = "http://127.0.0.1:8765/api";
const TYPE_LABELS = { lookup: "Lookup", tool_execution: "Tool run", page_visit: "Page visit", preference: "Preference" };
const TYPE_COLORS = { lookup: "#8ab4f8", tool_execution: "#81c995", page_visit: "#f28b82", preference: "#fdd663" };

function PreferencesSection() {
  const [prefs, setPrefs] = useState({});
  const [newKey, setNewKey] = useState("");
  const [newVal, setNewVal] = useState("");

  const load = async () => {
    const res = await fetch(`${API}/memory/preferences`);
    const body = await res.json();
    setPrefs(body.preferences || {});
  };

  useEffect(() => { load(); }, []);

  const save = async () => {
    if (!newKey.trim() || !newVal.trim()) return;
    await fetch(`${API}/memory/preferences`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: newKey.trim(), value: newVal.trim() }),
    });
    setNewKey(""); setNewVal("");
    load();
  };

  return (
    <div className="mem-section">
      <h4>Preferences</h4>
      {Object.keys(prefs).length === 0 && <p className="mem-empty">None inferred yet.</p>}
      <table className="mem-prefs-table">
        <tbody>
          {Object.entries(prefs).map(([k, v]) => (
            <tr key={k}>
              <td className="mem-pref-key">{k}</td>
              <td>{v.value}</td>
              <td className="mem-pref-meta">{v.source} · {Math.round(v.confidence * 100)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mem-pref-add">
        <input placeholder="key (e.g. location)" value={newKey} onChange={e => setNewKey(e.target.value)} />
        <input placeholder="value (e.g. London)" value={newVal} onChange={e => setNewVal(e.target.value)} onKeyDown={e => e.key === "Enter" && save()} />
        <button onClick={save}>Set</button>
      </div>
    </div>
  );
}

function MemoryItem({ memory, onDelete }) {
  const color = TYPE_COLORS[memory.type] || "#aaa";
  const label = TYPE_LABELS[memory.type] || memory.type;
  return (
    <div className="mem-item">
      <div className="mem-item-header">
        <span className="mem-type-badge" style={{ color }}>{label}</span>
        <span className="mem-item-date">{new Date(memory.created_at).toLocaleDateString()}</span>
        <button className="mem-item-delete" onClick={() => onDelete(memory.id)}>×</button>
      </div>
      <p className="mem-item-content">{memory.content}</p>
      {memory.tags.length > 0 && (
        <div className="mem-item-tags">{memory.tags.map(t => <span key={t} className="mem-tag">{t}</span>)}</div>
      )}
    </div>
  );
}

export default function MemoryPanel({ onClose, initialSearch = "" }) {
  const [memories, setMemories] = useState([]);
  const [filter, setFilter] = useState(initialSearch);
  const [typeFilter, setTypeFilter] = useState("");
  const [searching, setSearching] = useState(false);

  const loadMemories = async (q, type) => {
    setSearching(true);
    try {
      const url = q
        ? `${API}/memory/search?q=${encodeURIComponent(q)}&limit=20`
        : `${API}/memory?limit=50${type ? `&type=${type}` : ""}`;
      const res = await fetch(url);
      const body = await res.json();
      setMemories(body.memories || []);
    } finally {
      setSearching(false);
    }
  };

  useEffect(() => { loadMemories("", ""); }, []);

  const onDelete = async (id) => {
    await fetch(`${API}/memory/${id}`, { method: "DELETE" });
    setMemories(m => m.filter(x => x.id !== id));
  };

  return (
    <div className="mem-panel">
      <div className="mem-panel-header">
        <h3>Memory</h3>
        {onClose && <button className="mem-close" onClick={onClose}>×</button>}
      </div>

      <PreferencesSection />

      <div className="mem-section">
        <h4>Activity</h4>
        <div className="mem-search-row">
          <input
            placeholder="Search memories..."
            value={filter}
            onChange={e => { setFilter(e.target.value); loadMemories(e.target.value, typeFilter); }}
          />
          <select value={typeFilter} onChange={e => { setTypeFilter(e.target.value); loadMemories(filter, e.target.value); }}>
            <option value="">All types</option>
            {Object.entries(TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>

        {searching && <p className="mem-empty">Searching...</p>}
        {!searching && memories.length === 0 && <p className="mem-empty">No memories yet.</p>}
        <div className="mem-list">
          {memories.map(m => <MemoryItem key={m.id} memory={m} onDelete={onDelete} />)}
        </div>
      </div>
    </div>
  );
}
