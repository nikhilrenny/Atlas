import { useEffect, useRef, useState } from "react";

const API = "http://127.0.0.1:8765/api";

const STATUS_COLORS = {
  pending: "var(--text-3)",
  running: "var(--accent)",
  done: "var(--success)",
  failed: "var(--danger)",
  skipped: "var(--text-3)",
};

function StatusDot({ status }) {
  return <span className="agent-status-dot" style={{ background: STATUS_COLORS[status] || "var(--text-3)" }} />;
}

function StepRow({ step }) {
  return (
    <div className="agent-step">
      <StatusDot status={step.status} />
      <div className="agent-step-body">
        <p className="agent-step-title">
          <span className="agent-step-action">{step.action}</span> {step.target}
        </p>
        {step.error && <p className="agent-step-error">{step.error}</p>}
        {step.status === "done" && step.result != null && (
          <p className="agent-step-result">{typeof step.result === "string" ? step.result : JSON.stringify(step.result).slice(0, 200)}</p>
        )}
      </div>
    </div>
  );
}

function RunDetail({ run }) {
  if (!run) return null;
  return (
    <div className="agent-run-detail glass-card">
      <div className="agent-run-header">
        <StatusDot status={run.status} />
        <p className="agent-run-goal">{run.goal}</p>
      </div>
      {run.error && <p className="agent-step-error">{run.error}</p>}
      <div className="agent-steps-list">
        {run.steps.length === 0 && <p className="settings-empty">Planning…</p>}
        {run.steps.map(s => <StepRow key={s.id} step={s} />)}
      </div>
    </div>
  );
}

function ScheduleForm({ onCreate }) {
  const [goal, setGoal] = useState("");
  const [type, setType] = useState("interval");
  const [minutes, setMinutes] = useState(60);
  const [at, setAt] = useState("09:00");

  const submit = () => {
    if (!goal.trim()) return;
    const recurrence = type === "interval" ? { type: "interval", minutes: Number(minutes) || 60 } : { type: "daily", at };
    onCreate(goal.trim(), recurrence);
    setGoal("");
  };

  return (
    <div className="agent-schedule-form">
      <input placeholder="Recurring goal…" value={goal} onChange={e => setGoal(e.target.value)} />
      <select value={type} onChange={e => setType(e.target.value)}>
        <option value="interval">Every N minutes</option>
        <option value="daily">Daily at</option>
      </select>
      {type === "interval"
        ? <input type="number" min="1" value={minutes} onChange={e => setMinutes(e.target.value)} style={{ width: "80px" }} />
        : <input type="time" value={at} onChange={e => setAt(e.target.value)} />}
      <button className="btn-primary" onClick={submit}>Schedule</button>
    </div>
  );
}

export default function AgentsPage({ devMode, initialRunId }) {
  const [goal, setGoal] = useState("");
  const [running, setRunning] = useState(false);
  const [activeRun, setActiveRun] = useState(null);
  const [runs, setRuns] = useState([]);
  const [schedules, setSchedules] = useState([]);
  const pollRef = useRef(null);

  const loadRuns = () => fetch(`${API}/agents/runs`).then(r => r.json()).then(d => setRuns(d.runs || []));
  const loadSchedules = () => fetch(`${API}/agents/schedule`).then(r => r.json()).then(d => setSchedules(d.schedules || []));

  useEffect(() => { loadRuns(); loadSchedules(); }, []);

  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  const pollRun = (runId) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      const res = await fetch(`${API}/agents/runs/${runId}`);
      const run = await res.json();
      setActiveRun(run);
      if (run.status === "done" || run.status === "failed") {
        clearInterval(pollRef.current);
        setRunning(false);
        loadRuns();
      }
    }, 1200);
  };

  useEffect(() => {
    if (!initialRunId) return;
    setRunning(true);
    fetch(`${API}/agents/runs/${initialRunId}`).then(r => r.json()).then(setActiveRun);
    pollRun(initialRunId);
  }, [initialRunId]);

  const startRun = async () => {
    if (!goal.trim()) return;
    setRunning(true);
    setActiveRun(null);
    const res = await fetch(`${API}/agents/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal: goal.trim() }),
    });
    const run = await res.json();
    setActiveRun(run);
    pollRun(run.id);
    setGoal("");
  };

  const createSchedule = async (goalText, recurrence) => {
    await fetch(`${API}/agents/schedule`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal: goalText, recurrence }),
    });
    loadSchedules();
  };

  const deleteSchedule = async (id) => {
    await fetch(`${API}/agents/schedule/${id}`, { method: "DELETE" });
    loadSchedules();
  };

  const openRun = async (id) => {
    const res = await fetch(`${API}/agents/runs/${id}`);
    setActiveRun(await res.json());
  };

  return (
    <div className="toolbuilder-page">
      <div className="tb-header-card glass-card">
        <h2 className="tb-title">Agents</h2>
        <p className="tb-subtitle">Give Atlas a goal — it plans steps against your tools, browsing, and lookups, then runs them.</p>
        <div className="tb-build-row">
          <input
            value={goal}
            onChange={e => setGoal(e.target.value)}
            placeholder="e.g. 'check the weather in London and save it to memory'"
            onKeyDown={e => e.key === "Enter" && startRun()}
          />
          <button className="btn-primary" onClick={startRun} disabled={running}>{running ? "Working…" : "Run"}</button>
        </div>
      </div>

      {activeRun && <RunDetail run={activeRun} />}

      <div className="agent-section">
        <h3 className="notch-section-title">Recent runs</h3>
        <ul className="tb-list">
          {runs.length === 0 && <li className="tb-empty">No runs yet.</li>}
          {runs.map(r => (
            <li key={r.id} onClick={() => openRun(r.id)}>
              <span style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <StatusDot status={r.status} />
                {r.goal}
              </span>
              <span className="tb-pattern">{r.status}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="agent-section">
        <h3 className="notch-section-title">Scheduled goals</h3>
        <ScheduleForm onCreate={createSchedule} />
        <div className="agent-schedule-list">
          {schedules.length === 0 && <p className="tb-empty">No scheduled goals.</p>}
          {schedules.map(s => (
            <div className="agent-schedule-item" key={s.id}>
              <div>
                <p className="settings-row-label">{s.goal}</p>
                <p className="settings-row-hint">
                  {s.recurrence.type === "interval" ? `every ${s.recurrence.minutes}m` : `daily at ${s.recurrence.at}`}
                  {" · next: "}{new Date(s.next_run_at).toLocaleString()}
                </p>
              </div>
              <button className="tb-delete" onClick={() => deleteSchedule(s.id)}>delete</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
