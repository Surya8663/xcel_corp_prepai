"use client";

import { useState, useEffect, useCallback } from "react";

const NAV_TABS = [
  { id: "dashboard",    label: "Dashboard",    icon: "⊞" },
  { id: "resume-audit", label: "Resume Audit", icon: "📄" },
  { id: "prepare",      label: "Prepare",      icon: "📚" },
  { id: "interview",    label: "Interview",    icon: "🎤" },
  { id: "reports",      label: "Reports",      icon: "📊" },
] as const;

type TabId = (typeof NAV_TABS)[number]["id"];

interface NavbarProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
}

export default function Navbar({ activeTab, onTabChange }: NavbarProps) {
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Close drawer on resize to desktop
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 681px)");
    const handler = (e: MediaQueryListEvent) => { if (e.matches) setDrawerOpen(false); };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  // Close drawer on Escape
  useEffect(() => {
    if (!drawerOpen) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") setDrawerOpen(false); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [drawerOpen]);

  const handleTabChange = useCallback((tab: TabId) => {
    onTabChange(tab);
    setDrawerOpen(false);
  }, [onTabChange]);

  return (
    <>
      <nav className="navbar" role="navigation" aria-label="Main navigation">
        <div className="navbar-inner">
          {/* Logo */}
          <button
            className="navbar-logo"
            onClick={() => handleTabChange("dashboard")}
            aria-label="PrepAI — go to Dashboard"
            style={{ background: "none", border: "none", cursor: "pointer", padding: 0 }}
          >
            <div className="navbar-logo-icon" aria-hidden="true">P</div>
            <span className="navbar-logo-text">
              Prep<em>AI</em>
            </span>
          </button>

          {/* Desktop nav */}
          <ul className="navbar-nav" role="list" aria-label="Navigation tabs">
            {NAV_TABS.map((tab) => (
              <li key={tab.id}>
                <button
                  id={`nav-tab-${tab.id}`}
                  className={`nav-tab${activeTab === tab.id ? " active" : ""}`}
                  onClick={() => handleTabChange(tab.id)}
                  aria-current={activeTab === tab.id ? "page" : undefined}
                >
                  <span className="nav-tab-icon" aria-hidden="true">{tab.icon}</span>
                  {tab.label}
                </button>
              </li>
            ))}
          </ul>

          {/* Mobile hamburger */}
          <button
            className={`nav-hamburger${drawerOpen ? " open" : ""}`}
            aria-label={drawerOpen ? "Close navigation menu" : "Open navigation menu"}
            aria-expanded={drawerOpen}
            aria-controls="nav-mobile-drawer"
            onClick={() => setDrawerOpen((v) => !v)}
          >
            <span />
            <span />
            <span />
          </button>
        </div>
      </nav>

      {/* Mobile drawer */}
      <div
        id="nav-mobile-drawer"
        className={`nav-drawer${drawerOpen ? " open" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label="Navigation menu"
        onClick={(e) => { if (e.target === e.currentTarget) setDrawerOpen(false); }}
      >
        <div className="nav-drawer-panel">
          {NAV_TABS.map((tab) => (
            <button
              key={tab.id}
              className={`nav-drawer-tab${activeTab === tab.id ? " active" : ""}`}
              onClick={() => handleTabChange(tab.id)}
              aria-current={activeTab === tab.id ? "page" : undefined}
            >
              <span style={{ fontSize: "1.25rem" }} aria-hidden="true">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>
      </div>
    </>
  );
}

export type { TabId };
export { NAV_TABS };
