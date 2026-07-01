import { useState } from "react";
import HomePage from "./pages/HomePage";
import ToolBuilderPage from "./pages/ToolBuilderPage";
import BrowserPage from "./pages/BrowserPage";
import MemoryPanel from "./components/MemoryPanel";
import Notch from "./components/Notch";
import Splash from "./components/Splash";
import "./App.css";

const PAGE_TITLES = {
  home:        null,
  toolbuilder: "Tool Builder",
  browser:     "Browser",
  memory:      "Memory",
};

export default function App() {
  const [booting, setBooting] = useState(true);
  const [page, setPage]     = useState("home");
  const [pageArg, setPageArg] = useState("");

  if (booting) return <Splash onDone={() => setBooting(false)} />;

  const navigate = (dest, arg = "") => {
    setPage(dest);
    setPageArg(arg);
  };

  const goHome = () => { setPage("home"); setPageArg(""); };

  const renderPage = () => {
    switch (page) {
      case "home":
        return <HomePage onNavigate={navigate} />;
      case "toolbuilder":
        return (
          <div className="subpage">
            <div className="subpage-header">
              <button className="back-btn" onClick={goHome}>←</button>
              <span className="subpage-title">Tool Builder</span>
            </div>
            <ToolBuilderPage initialPrompt={pageArg} />
          </div>
        );
      case "browser":
        return (
          <div className="subpage">
            <div className="subpage-header">
              <button className="back-btn" onClick={goHome}>←</button>
              <span className="subpage-title">Browser</span>
            </div>
            <BrowserPage initialUrl={pageArg} />
          </div>
        );
      case "memory":
        return (
          <div className="subpage">
            <div className="subpage-header">
              <button className="back-btn" onClick={goHome}>←</button>
              <span className="subpage-title">Memory</span>
            </div>
            <MemoryPanel initialSearch={pageArg} />
          </div>
        );
      default:
        return <HomePage onNavigate={navigate} />;
    }
  };

  return (
    <div className="app-shell">
      <div className="app-page">
        {renderPage()}
      </div>
      <Notch onNavigate={navigate} />
    </div>
  );
}
