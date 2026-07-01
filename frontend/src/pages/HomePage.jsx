import { useState, useRef, useEffect } from "react";
import { OutputPanel } from "../components/ToolPanel";

const API = "http://127.0.0.1:8765/api";

const COMMANDS = {
  "~": { label: "Tool Builder", placeholder: "Describe a tool to build…" },
  "#": { label: "Memory",       placeholder: "Search your memory…" },
  "*": { label: "Run tool",     placeholder: "Tool name…" },
  "/": { label: "Browse",       placeholder: "URL to open…" },
  ">": { label: "IDE",          placeholder: "Describe what to code…" },
};

function parseInput(raw) {
  const first = raw[0];
  if (COMMANDS[first]) return { prefix: first, body: raw.slice(1).trimStart() };
  return { prefix: null, body: raw };
}

function CommandHints() {
  return (
    <div className="cmd-command-list">
      {Object.entries(COMMANDS).map(([k, v]) => (
        <div key={k} className="cmd-command-item">
          <span className="cmd-command-key">{k}</span>
          <span className="cmd-command-desc">{v.label}</span>
        </div>
      ))}
    </div>
  );
}

function cleanMemoryContent(content) {
  // Strip "Ran tool 'X' with {...} → ..." down to just the tool name + result
  const toolMatch = content.match(/^Ran tool '([^']+)' with \{[^}]*\} → (.+)/);
  if (toolMatch) return `▷ ${toolMatch[1]} → ${toolMatch[2].slice(0, 40)}`;
  // Strip "Lookup: X → result"
  const lookupMatch = content.match(/^Lookup: (.+?) →/);
  if (lookupMatch) return `⌕ ${lookupMatch[1].slice(0, 60)}`;
  // Strip "Visited: title (url)"
  const visitMatch = content.match(/^Visited: ([^(]+)/);
  if (visitMatch) return `⊕ ${visitMatch[1].trim().slice(0, 60)}`;
  return content.slice(0, 60);
}

export default function HomePage({ onNavigate }) {
  const [raw, setRaw]           = useState("");
  const [focused, setFocused]   = useState(false);
  const [working, setWorking]   = useState(false);
  const [result, setResult]     = useState(null); // {output_type, data, error}
  const [recentMem, setRecentMem] = useState([]);
  const inputRef = useRef(null);

  const { prefix, body } = parseInput(raw);
  const command = COMMANDS[prefix];

  useEffect(() => {
    fetch(`${API}/memory?limit=5`)
      .then(r => r.json())
      .then(d => setRecentMem(d.memories || []))
      .catch(() => {});
  }, []);

  const placeholder = command
    ? command.placeholder
    : "Ask anything, or use ~ # * / > for commands…";

  const handleKey = async (e) => {
    if (e.key !== "Enter" || !raw.trim()) return;
    e.preventDefault();
    await run();
  };

  const run = async () => {
    const { prefix, body } = parseInput(raw);
    if (!body && !prefix) return;
    setResult(null);

    if (prefix === "~") { onNavigate("toolbuilder", body); return; }
    if (prefix === "/") { onNavigate("browser", body || raw.slice(1).trim()); return; }
    if (prefix === ">") { onNavigate("ide", body); return; }
    if (prefix === "#") { onNavigate("memory", body); return; }
    if (prefix === "*") { onNavigate("run_tool", body); return; }

    // default: lookup
    setWorking(true);
    try {
      const res = await fetch(`${API}/toolbuilder/build_from_prompt`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: raw.trim() }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "failed");
      if (data.status === "answered") {
        setResult({ output_type: data.output_type, data: data.data });
      } else if (data.status === "clarify") {
        setResult({ clarify: data.questions });
      } else if (data.status === "infeasible") {
        setResult({ error: data.reason });
      } else if (data.status === "ready") {
        onNavigate("toolbuilder", "");
      }
    } catch (err) {
      setResult({ error: err.message });
    } finally {
      setWorking(false);
    }
  };

  const showDropdown = focused && !working && !result;

  return (
    <div className="home">
      <p className="home-wordmark">ATLAS</p>

      <div className="cmd-wrap">
        <div className={`cmd-card ${focused ? "focused" : ""}`}>
          <div className="cmd-inner">
            {prefix && <span className="cmd-prefix-badge">{prefix} {command?.label}</span>}
            <input
              ref={inputRef}
              className="cmd-input"
              value={raw}
              onChange={e => { setRaw(e.target.value); setResult(null); }}
              onFocus={() => setFocused(true)}
              onBlur={() => setTimeout(() => setFocused(false), 150)}
              onKeyDown={handleKey}
              placeholder={placeholder}
              autoFocus
            />
            {working
              ? <span className="cmd-hint">working…</span>
              : raw && <span className="cmd-hint" style={{ cursor: "pointer", color: "var(--accent)" }} onClick={run}>↵</span>
            }
            <button
              type="button"
              className="cmd-voice-btn"
              data-tooltip="Coming soon"
              aria-label="Voice search (coming soon)"
              disabled
            >
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 15a3.5 3.5 0 0 0 3.5-3.5v-5a3.5 3.5 0 0 0-7 0v5A3.5 3.5 0 0 0 12 15Z" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M6.5 11a5.5 5.5 0 0 0 11 0" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M12 16.5V19M9 19h6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          </div>
        </div>

        {showDropdown && (
          <div className="cmd-dropdown">
            {recentMem.length > 0 && (
              <>
                <p className="cmd-section-label">Recent</p>
                {recentMem.map(m => (
                  <div key={m.id} className="cmd-suggestion"
                    onClick={() => { setRaw(m.content.replace(/^(Lookup|Visited|Ran tool[^:]+):\s*/i, "").split("→")[0].trim()); inputRef.current?.focus(); }}>
                    <div className="cmd-suggestion-icon">
                      {m.type === "lookup" ? "⌕" : m.type === "page_visit" ? "⊕" : "▷"}
                    </div>
                    <span className="cmd-suggestion-text">{cleanMemoryContent(m.content)}</span>
                    <span className="cmd-suggestion-meta">{new Date(m.created_at).toLocaleDateString()}</span>
                  </div>
                ))}
              </>
            )}
            <p className="cmd-section-label">Commands</p>
            <CommandHints />
          </div>
        )}

        {working && (
          <div className="home-result">
            <div className="home-result-working">
              <div className="spinner" />
              Thinking…
            </div>
          </div>
        )}

        {result?.error && (
          <div className="home-result" style={{ color: "var(--danger)" }}>{result.error}</div>
        )}

        {result?.clarify && (
          <div className="home-result">
            <p style={{ marginBottom: "0.5rem", fontWeight: 500 }}>A couple of things:</p>
            {result.clarify.map((q, i) => <p key={i} style={{ color: "var(--text-3)", fontSize: "0.82rem" }}>· {q}</p>)}
          </div>
        )}

        {result?.data != null && (
          <div className="home-result">
            <OutputPanel outputType={result.output_type} data={result.data} />
          </div>
        )}
      </div>
    </div>
  );
}
