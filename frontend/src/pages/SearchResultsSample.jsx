import { useState } from "react";

// Hardcoded sample data — no API calls, no model routing.
// Only "kaizen" produces results, so this is purely a UI/layout exercise.
const SAMPLE_RESULTS = {
  web: [
    {
      title: "Kaizen: the Toyota philosophy of continuous improvement",
      source: "toyota-global.com",
      url: "toyota-global.com/kaizen-philosophy",
      detail: "Kaizen means \u201cchange for the better\u201d \u2014 small, continuous improvements made by everyone, rather than rare, sweeping overhauls. Toyota built its entire production system around this idea.",
      extra: "Every associate is expected to suggest changes, no matter how small \u2014 a retimed footstep, a relabeled bin, a shorter reach. None of it looks dramatic on its own. Compounded over years, it reshaped how Toyota builds cars.",
      date: "Updated 2 months ago",
      related: [
        "The Toyota Production System, explained end to end",
        "Andon cords: stopping the line the moment a defect appears",
        "Muda, mura, muri \u2014 the three types of waste Kaizen targets",
      ],
    },
    {
      title: "What is a Gemba walk, and why engineers use them",
      source: "leanproduction.com",
      url: "leanproduction.com/gemba-walks",
      detail: "A Gemba walk means going to where the actual work happens \u2014 the factory floor, the codebase, the deployed system \u2014 instead of reviewing it secondhand. It surfaces problems that reports miss.",
      extra: "Managers who skip the walk end up solving problems described secondhand, which usually means solving the wrong problem. A five-minute walk past the actual work often tells you more than a week of status reports.",
      date: "Updated 5 months ago",
      related: [
        "A checklist for running your first Gemba walk",
        "Why remote teams struggle to do Gemba walks well",
        "Gemba walks vs. stand-ups: what each one is actually for",
      ],
    },
    {
      title: "5S: the workplace organization system behind Kaizen",
      source: "kaizen.com",
      url: "kaizen.com/5s-system",
      detail: "5S stands for Sort, Set in order, Shine, Standardize, Sustain. It's a five-step method for organizing a workspace so waste and clutter become visible, then stay gone.",
      extra: "Most teams start with Sort and Set in order because the payoff is immediate and visible. Shine, Standardize, and Sustain are what keep the first two from decaying back into clutter within a month.",
      date: "Updated 1 year ago",
      related: [
        "5S for software: applying it to repos and dev environments",
        "How to audit a workspace against the 5S standard",
        "Where 5S came from, and how it spread beyond manufacturing",
      ],
    },
  ],
  tools: [
    { name: "Kaizen board", detail: "Already built · tracks small process changes over time", pinned: true, kind: "journal" },
    { name: "5S checklist", detail: "Not built yet · scores a workspace against 5S", pinned: false, kind: "checklist" },
  ],
  memory: [
    { text: "You noted wanting a short retro after each Atlas phase, Kaizen-style", when: "3 days ago" },
    { text: "Visited leanproduction.com while researching Phase 7 review process", when: "1 week ago" },
  ],
};

const FIVE_S_ITEMS = [
  { key: "sort", label: "Sort — remove anything that isn't needed" },
  { key: "setInOrder", label: "Set in order — give what's left an obvious home" },
  { key: "shine", label: "Shine — clean and inspect the space" },
  { key: "standardize", label: "Standardize — write down how it should look" },
  { key: "sustain", label: "Sustain — check it still holds a week later" },
];

function ResultColumn({ title, children }) {
  return (
    <div className="search-col">
      <p className="search-col-title">{title}</p>
      <div className="search-col-body">{children}</div>
    </div>
  );
}

export default function SearchResultsSample() {
  const [raw, setRaw] = useState("");
  const [expandedWeb, setExpandedWeb] = useState(null);
  const [bigWeb, setBigWeb] = useState(null);
  const [bigSite, setBigSite] = useState(false);
  const [openTool, setOpenTool] = useState(null);
  const [journalText, setJournalText] = useState("");
  const [checklist, setChecklist] = useState({ sort: false, setInOrder: false, shine: false, standardize: false, sustain: false });
  const query = raw.trim().toLowerCase();
  const expanded = query === "kaizen";

  const handleWebClick = (i) => {
    if (bigWeb === i) { setBigWeb(null); setBigSite(false); return; }
    if (expandedWeb === i) { setExpandedWeb(null); setBigWeb(i); return; }
    setExpandedWeb(i);
  };

  const toggleChecklist = (key) => setChecklist((c) => ({ ...c, [key]: !c[key] }));

  return (
    <div className="home">
      <p className="home-wordmark">ATLAS</p>

      <div className="cmd-wrap">
        <div className={`cmd-card ${raw ? "focused" : ""}`}>
          <div className="cmd-inner">
            <input
              className="cmd-input"
              value={raw}
              onChange={(e) => setRaw(e.target.value)}
              placeholder="Try typing kaizen…"
              autoFocus
            />
          </div>
        </div>

        {expanded && (
          <div className="search-expand">
            <p className="search-meta">3 web results · 2 tools · 2 memories</p>
            <div className="search-grid">
              <ResultColumn title="Web">
                {SAMPLE_RESULTS.web.map((r, i) => {
                  const isOpen = expandedWeb === i;
                  return (
                    <div
                      className={`search-card search-card-clickable ${isOpen ? "search-card-expanded" : ""}`}
                      key={i}
                      onClick={() => handleWebClick(i)}
                    >
                      <p className="search-card-title">{r.title}</p>
                      <p className="search-card-sub">{r.source}</p>
                      {isOpen && (
                        <div className="search-card-detail">
                          <p>{r.detail}</p>
                          <p className="search-card-detail-meta">{r.date} · click again to expand</p>
                        </div>
                      )}
                    </div>
                  );
                })}
              </ResultColumn>

              <ResultColumn title="Tools">
                {SAMPLE_RESULTS.tools.map((t, i) => (
                  <div
                    className="search-card search-card-clickable"
                    key={i}
                    onClick={() => setOpenTool(i)}
                  >
                    <p className="search-card-title">{t.name}</p>
                    <p className="search-card-sub">{t.detail}</p>
                  </div>
                ))}
              </ResultColumn>

              <ResultColumn title="Memory">
                {SAMPLE_RESULTS.memory.map((m, i) => (
                  <div className="search-card" key={i}>
                    <p className="search-card-title">{m.text}</p>
                    <p className="search-card-sub">{m.when}</p>
                  </div>
                ))}
              </ResultColumn>
            </div>
          </div>
        )}

        {raw && !expanded && (
          <div className="search-expand">
            <p className="search-meta">No sample data for "{raw}" — try "kaizen"</p>
          </div>
        )}
      </div>

      {bigWeb !== null && (
        <div className="search-overlay-backdrop" onClick={() => { setBigWeb(null); setBigSite(false); }}>
          <div className={`search-overlay-card ${bigSite ? "fullsite" : ""}`} onClick={(e) => e.stopPropagation()}>
            {bigSite ? (
              <>
                <div className="search-site-nav">
                  <span className="search-site-logo">{SAMPLE_RESULTS.web[bigWeb].source}</span>
                  <div className="search-site-nav-links">
                    <span>Company</span>
                    <span>Newsroom</span>
                    <span>Sustainability</span>
                  </div>
                </div>
                <div className="search-site-hero">
                  <span className="search-site-hero-badge">Our picks</span>
                  <p className="search-site-hero-date">{SAMPLE_RESULTS.web[bigWeb].date}</p>
                  <p className="search-site-hero-title">{SAMPLE_RESULTS.web[bigWeb].title}</p>
                </div>
                <div className="search-site-grid">
                  <div className="search-site-tile" style={{ backgroundImage: "url('https://picsum.photos/400/300?random=11')" }} />
                  <div className="search-site-tile" style={{ backgroundImage: "url('https://picsum.photos/400/300?random=12')" }} />
                  <div className="search-site-tile" style={{ backgroundImage: "url('https://picsum.photos/400/300?random=13')" }} />
                  <div className="search-site-tile" style={{ backgroundImage: "url('https://picsum.photos/400/300?random=14')" }} />
                </div>
              </>
            ) : (
              <>
                <p className="search-article-title">{SAMPLE_RESULTS.web[bigWeb].title}</p>
                <p className="search-article-byline">
                  <span className="search-site-link" onClick={() => setBigSite(true)}>{SAMPLE_RESULTS.web[bigWeb].source}</span> · {SAMPLE_RESULTS.web[bigWeb].date}
                </p>
                <div className="search-article-body">
                  <p>{SAMPLE_RESULTS.web[bigWeb].detail}</p>
                  <p>{SAMPLE_RESULTS.web[bigWeb].extra}</p>
                </div>
                <div className="search-article-related">
                  <p className="search-overlay-related-title">You might also like</p>
                  {SAMPLE_RESULTS.web[bigWeb].related.map((r, i) => (
                    <span className="search-article-related-link" key={i}>{r}</span>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {openTool !== null && (
        <div className="search-overlay-backdrop" onClick={() => setOpenTool(null)}>
          <div className="search-overlay-card" onClick={(e) => e.stopPropagation()}>
            <div className="search-overlay-header">
              <p className="search-overlay-title">{SAMPLE_RESULTS.tools[openTool].name}</p>
              <p className="search-overlay-source">{SAMPLE_RESULTS.tools[openTool].detail}</p>
            </div>

            {SAMPLE_RESULTS.tools[openTool].kind === "journal" && (
              <>
                <p className="search-tool-desc">
                  A place to log small process changes as they happen — no forms, just write what changed and why.
                </p>
                <textarea
                  className="search-tool-journal"
                  value={journalText}
                  onChange={(e) => setJournalText(e.target.value)}
                  placeholder="What changed today, and why?"
                  autoFocus
                />
                <p className="search-tool-journal-hint">Not saved anywhere yet — this is just the layout.</p>
              </>
            )}

            {SAMPLE_RESULTS.tools[openTool].kind === "checklist" && (
              <>
                <p className="search-tool-desc">
                  Walk the workspace and check off each step as you confirm it.
                </p>
                <div className="search-checklist">
                  {FIVE_S_ITEMS.map((item) => (
                    <label
                      key={item.key}
                      className={`search-checklist-item ${checklist[item.key] ? "checked" : ""}`}
                    >
                      <input
                        type="checkbox"
                        checked={checklist[item.key]}
                        onChange={() => toggleChecklist(item.key)}
                      />
                      {item.label}
                    </label>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
