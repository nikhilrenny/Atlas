import { useEffect, useState } from "react";
import ToolPanel, { OutputPanel } from "../components/ToolPanel";

const API = "http://127.0.0.1:8765/api";
const URL_PATTERN = /^(https?:\/\/)?[\w-]+(\.[\w-]+)+([/?#].*)?$/i;

function looksLikeUrl(value) {
  return URL_PATTERN.test(value.trim()) && !value.trim().includes(" ");
}

function normalizeUrl(value) {
  const v = value.trim();
  return /^https?:\/\//i.test(v) ? v : `https://${v}`;
}

export default function ToolBuilderPage({ initialPrompt = "", devMode = false }) {
  const [input, setInput] = useState(initialPrompt);
  const [tools, setTools] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [building, setBuilding] = useState(false);
  const [error, setError] = useState(null);

  // Dev mode: force a specific provider/model through classify+generate, same as HomePage.
  const [devModels, setDevModels] = useState(null);
  const [devPick, setDevPick] = useState("");
  const [devListOpen, setDevListOpen] = useState(false);

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

  // Prompt-path clarification state
  const [clarify, setClarify] = useState(null); // {prompt, questions, round}
  const [answers, setAnswers] = useState({});

  // Result of a one-off "lookup" intent build -- never saved as a tool
  const [lookupResult, setLookupResult] = useState(null); // {output_type, data}

  const loadTools = async () => {
    const res = await fetch(`${API}/toolbuilder/tools`);
    const body = await res.json();
    setTools(body.tools || []);
  };

  useEffect(() => { loadTools(); }, []);

  const onToolReady = async (tool) => {
    await loadTools();
    setActiveId(tool.id);
    setInput("");
    setClarify(null);
    setAnswers({});
    setLookupResult(null);
  };

  const buildFromUrl = async (url) => {
    const [force_provider, force_model] = devMode && devPick ? devPick.split("::") : [undefined, undefined];
    const res = await fetch(`${API}/toolbuilder/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, force_provider, force_model }),
    });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || "generation failed");
    await onToolReady(body);
  };

  const buildFromPrompt = async (prompt, answerText, round) => {
    const [force_provider, force_model] = devMode && devPick ? devPick.split("::") : [undefined, undefined];
    const res = await fetch(`${API}/toolbuilder/build_from_prompt`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, answers: answerText || null, round, force_provider, force_model }),
    });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || "build failed");

    if (body.status === "infeasible") {
      setError(body.reason);
      setClarify(null);
      return;
    }
    if (body.status === "clarify") {
      setClarify({ prompt, questions: body.questions, round: round + 1 });
      setAnswers({});
      return;
    }
    if (body.status === "answered") {
      setLookupResult({ output_type: body.output_type, data: body.data });
      setClarify(null);
      setInput("");
      return;
    }
    await onToolReady(body.tool);
  };

  const build = async () => {
    if (!input.trim()) return;
    setBuilding(true);
    setError(null);
    setLookupResult(null);
    try {
      if (looksLikeUrl(input)) {
        await buildFromUrl(normalizeUrl(input));
      } else {
        await buildFromPrompt(input.trim(), null, 0);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setBuilding(false);
    }
  };

  const submitAnswers = async () => {
    if (!clarify) return;
    setBuilding(true);
    setError(null);
    try {
      const answerText = clarify.questions.map((q, i) => `${q.question} ${answers[i] || "(no answer)"}`).join("; ");
      await buildFromPrompt(clarify.prompt, answerText, clarify.round);
    } catch (e) {
      setError(e.message);
    } finally {
      setBuilding(false);
    }
  };

  const deleteTool = async (id) => {
    await fetch(`${API}/toolbuilder/tools/${id}`, { method: "DELETE" });
    if (activeId === id) setActiveId(null);
    await loadTools();
  };

  const togglePin = async (id, pinned) => {
    await fetch(`${API}/toolbuilder/tools/${id}/pin`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pinned }),
    });
    await loadTools();
  };

  const active = tools.find((t) => t.id === activeId);
  const pinned = tools.filter((t) => t.pinned);

  return (
    <div className="toolbuilder-page">
      <div className="tb-header-card glass-card">
        <h2 className="tb-title">Tool Builder</h2>
        <p className="tb-subtitle">Paste a URL to turn a page into a tool, or describe what you want built.</p>

      {devMode && (
        <div className="dev-model-row" style={{ marginBottom: "0.9rem" }}>
          <span className="dev-model-badge">DEV</span>
          <div className="dev-model-pill" onClick={() => setDevListOpen(o => !o)}>
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
                        <div key={value} className={`dev-model-option ${devPick === value ? "active" : ""}`}
                          onClick={() => { setDevPick(value); setDevListOpen(false); }}>
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

      {!clarify && (
        <div className="tb-build-row">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="https://... or 'build me a weather widget'"
            onKeyDown={(e) => e.key === "Enter" && build()}
          />
          <button className="btn-primary" onClick={build} disabled={building}>{building ? "Working..." : "Build tool"}</button>
        </div>
      )}

      {clarify && (
        <div className="tb-clarify">
          <p>A couple of things to pin down before building:</p>
          {clarify.questions.map((q, i) => (
            <div key={i} className="tb-field">
              <span>{q.question}</span>
              {q.options?.length ? (
                <div className="clarify-options">
                  {q.options.map(opt => (
                    <button
                      key={opt}
                      type="button"
                      className={`clarify-option ${answers[i] === opt ? "active" : ""}`}
                      onClick={() => setAnswers((a) => ({ ...a, [i]: opt }))}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              ) : (
                <input
                  value={answers[i] || ""}
                  onChange={(e) => setAnswers((a) => ({ ...a, [i]: e.target.value }))}
                />
              )}
            </div>
          ))}
          <button className="btn-primary" onClick={submitAnswers} disabled={building}>{building ? "Working..." : "Continue"}</button>
        </div>
      )}

      {error && <p className="tb-error">{error}</p>}
      </div>

      {lookupResult && (
        <div className="tb-lookup-result">
          <OutputPanel outputType={lookupResult.output_type} data={lookupResult.data} />
        </div>
      )}

      {pinned.length > 0 && (
        <div className="tb-pinned">
          <h3>Pinned</h3>
          <p className="tb-stub-note">Quick-access list for now -- a real homescreen view is Phase 11.</p>
          <ul className="tb-list">
            {pinned.map((t) => (
              <li key={t.id} className={t.id === activeId ? "active" : ""} onClick={() => setActiveId(t.id)}>
                {t.name}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="tb-layout">
        <ul className="tb-list">
          {tools.map((t) => (
            <li key={t.id} className={t.id === activeId ? "active" : ""} onClick={() => setActiveId(t.id)}>
              {t.name}
              <span className="tb-pattern">{t.pattern}</span>
            </li>
          ))}
          {tools.length === 0 && <li className="tb-empty">No tools generated yet.</li>}
        </ul>

        {active && <ToolPanel key={active.id} manifest={active} onDelete={deleteTool} onTogglePin={togglePin} />}
      </div>
    </div>
  );
}
