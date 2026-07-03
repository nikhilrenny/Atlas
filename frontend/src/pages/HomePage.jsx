import { useState, useRef, useEffect } from "react";
import ToolPanel, { OutputPanel } from "../components/ToolPanel";

const API = "http://127.0.0.1:8765/api";

// Commands (~ # * / >) removed for now — all input goes through the AI intent
// pipeline below (build_from_prompt), which decides itself whether the request
// is a one-off lookup or something to save as a reusable tool.

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

export default function HomePage({ onNavigate, devMode }) {
  const [raw, setRaw]           = useState("");
  const [focused, setFocused]   = useState(false);
  const [working, setWorking]   = useState(false);
  const [result, setResult]     = useState(null); // {output_type, data, error}
  const [recentMem, setRecentMem] = useState([]);
  const [dropdownArmed, setDropdownArmed] = useState(false);
  const [devModels, setDevModels] = useState(null); // {provider: {available, models}}
  const [devPick, setDevPick] = useState(""); // "provider::model"
  const [devListOpen, setDevListOpen] = useState(false);
  const [answers, setAnswers] = useState({});
  const inputRef = useRef(null);

  useEffect(() => {
    fetch(`${API}/memory?limit=5`)
      .then(r => r.json())
      .then(d => setRecentMem(d.memories || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!devMode || devModels) return;
    fetch(`${API}/dev/models`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(d => {
        setDevModels(d);
        const first = Object.entries(d).find(([, v]) => v.available && v.models.length);
        if (first) setDevPick(`${first[0]}::${first[1].models[0]}`);
      })
      .catch(e => setDevModels({ _error: e.message }));
  }, [devMode, devModels]);

  const showDropdown = focused && !working && !result;

  useEffect(() => {
    if (!showDropdown) { setDropdownArmed(false); return; }
    const t = setTimeout(() => setDropdownArmed(true), 300);
    return () => clearTimeout(t);
  }, [showDropdown]);

  const placeholder = "Ask anything…";

  const handleKey = async (e) => {
    if (e.key !== "Enter" || !raw.trim()) return;
    e.preventDefault();
    await run();
  };

  const runBuild = async (promptText, answerText, roundNum) => {
    const [force_provider, force_model] = devMode && devPick ? devPick.split("::") : [undefined, undefined];
    setResult(null);
    setWorking(true);
    try {
      const res = await fetch(`${API}/toolbuilder/build_from_prompt`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: promptText, answers: answerText || null, round: roundNum, force_provider, force_model }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "failed");
      if (data.status === "answered") {
        setResult({ output_type: data.output_type, data: data.data });
      } else if (data.status === "agent_started") {
        onNavigate("agents", data.agent_run_id);
      } else if (data.status === "clarify") {
        setAnswers({});
        setResult({ clarify: data.questions, clarifyPrompt: promptText, clarifyRound: roundNum + 1 });
      } else if (data.status === "infeasible") {
        setResult({ error: data.reason });
      } else if (data.status === "ready") {
        setResult({ tool: data.tool });
      }
    } catch (err) {
      setResult({ error: err.message });
    } finally {
      setWorking(false);
    }
  };

  const run = async () => {
    // Dev-only shortcut: "£name" opens a hardcoded sample/demo page (e.g. "£kaizen").
    if (raw.trim().startsWith("£")) {
      onNavigate("sample", raw.trim().slice(1).trim());
      return;
    }
    if (!raw.trim()) return;
    await runBuild(raw.trim(), null, 0);
  };

  const submitClarifyAnswers = async () => {
    if (!result?.clarify) return;
    const answerText = result.clarify.map((q, i) => `${q.question} ${answers[i] || "(no answer)"}`).join("; ");
    await runBuild(result.clarifyPrompt, answerText, result.clarifyRound);
  };

  return (
    <div className="home">
      <p className="home-wordmark">ATLAS</p>

      <div className="cmd-wrap">
        <div className={`cmd-card ${focused ? "focused" : ""}`}>
          <div className="cmd-inner">
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

        {devMode && (
          <div className="dev-model-row">
            <span className="dev-model-badge">DEV</span>
            <div
              className="dev-model-pill"
              onClick={() => setDevListOpen(o => !o)}
            >
              <span>{devModels?._error ? `error: ${devModels._error}` : devPick ? devPick.replace("::", " · ") : devModels ? "no models available" : "loading models…"}</span>
              <svg viewBox="0 0 24 24" fill="none"><path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
            </div>
            {devListOpen && devModels && !devModels._error && (
              <>
                <div style={{ position: "fixed", inset: 0, zIndex: 29 }} onClick={() => setDevListOpen(false)} />
                <div className="dev-model-list">
                  {Object.entries(devModels).filter(([, info]) => info.available).map(([provider, info]) => (
                    <div key={provider}>
                      <p className="dev-model-group-label">{provider}</p>
                      {info.models.map(m => {
                        const value = `${provider}::${m}`;
                        return (
                          <div
                            key={value}
                            className={`dev-model-option ${devPick === value ? "active" : ""}`}
                            onClick={() => { setDevPick(value); setDevListOpen(false); }}
                          >
                            {m}
                          </div>
                        );
                      })}
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {showDropdown && (
          <div className={`cmd-dropdown ${dropdownArmed ? "" : "cmd-dropdown-arming"}`}>
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
            <p style={{ marginBottom: "0.6rem", fontWeight: 500 }}>A couple of things:</p>
            {result.clarify.map((q, i) => (
              <div key={i} className="tb-field" style={{ marginBottom: "0.6rem" }}>
                <span>{q.question}</span>
                {q.options?.length ? (
                  <div className="clarify-options">
                    {q.options.map(opt => (
                      <button
                        key={opt}
                        type="button"
                        className={`clarify-option ${answers[i] === opt ? "active" : ""}`}
                        onClick={() => setAnswers(a => ({ ...a, [i]: opt }))}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                ) : (
                  <input
                    value={answers[i] || ""}
                    onChange={e => setAnswers(a => ({ ...a, [i]: e.target.value }))}
                    onKeyDown={e => e.key === "Enter" && submitClarifyAnswers()}
                    autoFocus={i === 0}
                  />
                )}
              </div>
            ))}
            <button className="btn-primary" onClick={submitClarifyAnswers} disabled={working} style={{ marginTop: "0.3rem" }}>
              {working ? "Working…" : "Continue"}
            </button>
          </div>
        )}

        {result?.tool && (
          <div className="home-result">
            <ToolPanel
              manifest={result.tool}
              onDelete={async (id) => {
                await fetch(`${API}/toolbuilder/tools/${id}`, { method: "DELETE" });
                setResult(null);
              }}
              onTogglePin={async (id, pinned) => {
                await fetch(`${API}/toolbuilder/tools/${id}/pin`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ pinned }),
                });
                setResult(r => ({ tool: { ...r.tool, pinned } }));
              }}
            />
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
