import { useState } from "react";
import HomePage from "./pages/HomePage";
import ToolBuilderPage from "./pages/ToolBuilderPage";
import AgentsPage from "./pages/AgentsPage";
import BrowserPage from "./pages/BrowserPage";
import MemoryPanel from "./components/MemoryPanel";
import Notch from "./components/Notch";
import Splash from "./components/Splash";
import ScriptsPanel from "./components/ScriptsPanel";
import SettingsPanel from "./components/SettingsPanel";
import UsageWidget from "./components/UsageWidget";
import { SAMPLE_PAGES } from "./pages/samples";
import "./App.css";

const PAGE_TITLES = {
  home:        null,
  toolbuilder: "Tool Builder",
  agents:      "Agents",
  browser:     "Browser",
  memory:      "Memory",
};

export default function App() {
  const [booting, setBooting] = useState(true);
  const [navStack, setNavStack] = useState([{ page: "home", arg: "" }]);
  const [navIndex, setNavIndex] = useState(0);

  // Dev mode: always present/hardwired, but visually near-invisible until toggled.
  // Not gated behind a build flag on purpose -- this is a permanent dev affordance,
  // not a temporary feature flag. Always starts OFF on every load/relaunch -- session-only,
  // never persisted, so it can't accidentally stay on from a previous session.
  const [devMode, setDevMode] = useState(false);
  // Only one floating overlay (Notch / Scripts / Usage) can be open at a time --
  // opening one closes whichever else was open, and clicking outside any of them
  // closes it too. Tool Builder is a real page (lives in navStack), not an overlay,
  // so it's deliberately not part of this and keeps its normal stay-open behaviour.
  const [activeOverlay, setActiveOverlay] = useState(null); // null | "notch" | "scripts" | "usage" | "settings"
  const toggleOverlay = (name) => setActiveOverlay(o => (o === name ? null : name));
  const closeOverlay = () => setActiveOverlay(null);

  if (booting) return <Splash onDone={() => setBooting(false)} />;

  const { page, arg: pageArg } = navStack[navIndex];

  const navigate = (dest, arg = "") => {
    const next = navStack.slice(0, navIndex + 1);
    next.push({ page: dest, arg });
    setNavStack(next);
    setNavIndex(next.length - 1);
  };

  const goBack = () => { if (navIndex > 0) setNavIndex(navIndex - 1); };
  const goForward = () => { if (navIndex < navStack.length - 1) setNavIndex(navIndex + 1); };

  // Dev mode is a global switch, so turning it off takes priority over whatever
  // subpage is open -- if that page only exists as a dev affordance (Tool Builder
  // is reachable via the dev-only nav button), bounce back home instead of leaving
  // the user stranded on a now-half-hidden page.
  const toggleDevMode = () => {
    setDevMode(prev => {
      const next = !prev;
      if (!next) {
        // Notch isn't dev-gated, so leave it be -- only close the dev-only overlays.
        if (activeOverlay === "scripts" || activeOverlay === "usage" || activeOverlay === "settings") setActiveOverlay(null);
        if (page === "toolbuilder") navigate("home");
      }
      return next;
    });
  };

  const topnavTitle = page === "sample" ? `Sample · ${pageArg || "?"}` : PAGE_TITLES[page];

  const renderPage = () => {
    switch (page) {
      case "home":
        return <HomePage onNavigate={navigate} devMode={devMode} />;
      case "toolbuilder":
        return (
          <div className="subpage">
            <ToolBuilderPage initialPrompt={pageArg} devMode={devMode} />
          </div>
        );
      case "agents":
        return (
          <div className="subpage">
            <AgentsPage devMode={devMode} initialRunId={pageArg} />
          </div>
        );
      case "browser":
        return (
          <div className="subpage">
            <BrowserPage initialUrl={pageArg} />
          </div>
        );
      case "memory":
        return (
          <div className="subpage">
            <MemoryPanel initialSearch={pageArg} />
          </div>
        );
      case "sample": {
        const SamplePage = SAMPLE_PAGES[pageArg?.toLowerCase()];
        return (
          <div className="subpage">
            {SamplePage ? <SamplePage /> : (
              <p style={{ padding: "2rem", color: "var(--text-3)" }}>
                No sample page called "{pageArg}". Available: {Object.keys(SAMPLE_PAGES).join(", ")}
              </p>
            )}
          </div>
        );
      }
      default:
        return <HomePage onNavigate={navigate} />;
    }
  };

  return (
    <div className="app-shell">
      {page === "sample" && (
        <div className="topnav">
          <button className="back-btn" onClick={goBack} disabled={navIndex === 0}>←</button>
          <button className="back-btn" onClick={goForward} disabled={navIndex === navStack.length - 1}>→</button>
          <span className="subpage-title">{topnavTitle}</span>
        </div>
      )}
      <div className="app-page">
        {renderPage()}
      </div>
      <Notch onNavigate={navigate} open={activeOverlay === "notch"} onToggle={() => toggleOverlay("notch")} onClose={closeOverlay} />
      {devMode && (
        <button
          className="agents-access-btn"
          onClick={() => navigate(page === "agents" ? "home" : "agents", "")}
          aria-label={page === "agents" ? "Close Agents" : "Open Agents"}
          title={page === "agents" ? "Close Agents" : "Agents"}
        >
          <svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.6"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg>
        </button>
      )}
      <button
        className={`dev-toggle ${devMode ? "dev-toggle-on" : ""}`}
        onClick={toggleDevMode}
        aria-label="Toggle dev mode"
        title={devMode ? "Dev mode: on" : ""}
      />
      {devMode && (
        <button
          className="toolbuilder-access-btn"
          onClick={() => navigate(page === "toolbuilder" ? "home" : "toolbuilder", "")}
          aria-label={page === "toolbuilder" ? "Close Tool Builder" : "Open Tool Builder"}
          title={page === "toolbuilder" ? "Close Tool Builder" : "Tool Builder"}
        >
          <svg viewBox="0 0 24 24" fill="none"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.4-3.4a5 5 0 0 1-6.4 6.4L6.5 20.5a2.1 2.1 0 0 1-3-3l8.2-8.2a5 5 0 0 1 6.4-6.4l-3.4 3.4Z" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>
        </button>
      )}
      {devMode && (
        <button
          className={`scripts-access-btn ${activeOverlay === "scripts" ? "scripts-access-btn-on" : ""}`}
          onClick={() => toggleOverlay("scripts")}
          aria-label={activeOverlay === "scripts" ? "Close Scripts Mode" : "Open Scripts Mode"}
          title={activeOverlay === "scripts" ? "Close Scripts Mode" : "Scripts Mode"}
        >
          <svg viewBox="0 0 24 24" fill="none"><path d="M4 5.5h16M4 12h10M4 18.5h7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/><path d="M17 15.5l3 3-3 3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>
        </button>
      )}
      {devMode && activeOverlay === "scripts" && (
        <>
          <div style={{ position: "fixed", inset: 0, zIndex: 1499 }} onClick={closeOverlay} />
          <ScriptsPanel onClose={closeOverlay} />
        </>
      )}
      {devMode && (
        <button
          className={`settings-access-btn ${activeOverlay === "settings" ? "settings-access-btn-on" : ""}`}
          onClick={() => toggleOverlay("settings")}
          aria-label={activeOverlay === "settings" ? "Close Settings" : "Open Settings"}
          title={activeOverlay === "settings" ? "Close Settings" : "Settings"}
        >
          <svg viewBox="0 0 24 24" fill="none"><path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z" stroke="currentColor" strokeWidth="1.6"/><path d="M19.4 13.5a1.7 1.7 0 0 0 .34 1.87l.06.06a2.06 2.06 0 1 1-2.9 2.9l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1.03 1.56V20a2.06 2.06 0 1 1-4.12 0v-.09a1.7 1.7 0 0 0-1.11-1.56 1.7 1.7 0 0 0-1.87.34l-.06.06a2.06 2.06 0 1 1-2.9-2.9l.06-.06a1.7 1.7 0 0 0 .34-1.87 1.7 1.7 0 0 0-1.56-1.03H4a2.06 2.06 0 1 1 0-4.12h.09a1.7 1.7 0 0 0 1.56-1.11 1.7 1.7 0 0 0-.34-1.87l-.06-.06a2.06 2.06 0 1 1 2.9-2.9l.06.06a1.7 1.7 0 0 0 1.87.34H10.5a1.7 1.7 0 0 0 1.03-1.56V4a2.06 2.06 0 1 1 4.12 0v.09a1.7 1.7 0 0 0 1.03 1.56 1.7 1.7 0 0 0 1.87-.34l.06-.06a2.06 2.06 0 1 1 2.9 2.9l-.06.06a1.7 1.7 0 0 0-.34 1.87V10.5a1.7 1.7 0 0 0 1.56 1.03H20a2.06 2.06 0 1 1 0 4.12h-.09a1.7 1.7 0 0 0-1.56 1.03Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/></svg>
        </button>
      )}
      {devMode && activeOverlay === "settings" && <SettingsPanel onClose={closeOverlay} />}
      {devMode && <UsageWidget open={activeOverlay === "usage"} onToggle={() => toggleOverlay("usage")} onClose={closeOverlay} />}
    </div>
  );
}
