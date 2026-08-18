"use client";

import { useState, useEffect, useRef } from "react";
import Navbar, { type TabId } from "@/components/Navbar";
import StatCard from "@/components/StatCard";
import ResumeAuditComponent from "@/components/ResumeAudit";
import PrepareComponent from "@/components/Prepare";
import InterviewSetupComponent from "@/components/InterviewSetup";
import LiveInterviewComponent from "@/components/LiveInterview";
import ReportCardComponent from "@/components/ReportCard";
import ProgressAnalyticsComponent from "@/components/ProgressAnalytics";
import { listResumes, type InterviewRecord } from "@/lib/api";

/* ── Stat card config ─────────────────────────────────────────────────────── */
const STATS = [
  {
    icon: "🎯",
    iconVariant: "blue" as const,
    label: "Sessions",
    value: "—",
    delta: "No sessions yet",
  },
  {
    icon: "📄",
    iconVariant: "green" as const,
    label: "Resumes Audited",
    value: "—",
    delta: "Upload your first resume",
  },
  {
    icon: "🎤",
    iconVariant: "purple" as const,
    label: "Interviews Taken",
    value: "—",
    delta: "Start your first interview",
  },
  {
    icon: "📈",
    iconVariant: "amber" as const,
    label: "Overall Score",
    value: "—",
    delta: "Complete an interview to see",
  },
];

/* ── Quick action config ──────────────────────────────────────────────────── */
const QUICK_ACTIONS = [
  {
    icon: "📄",
    label: "Audit My Resume",
    desc: "Get AI-powered feedback on your resume",
    tab: "resume-audit" as TabId,
  },
  {
    icon: "📚",
    label: "Start Prep Session",
    desc: "Brush up on concepts before your interview",
    tab: "prepare" as TabId,
  },
  {
    icon: "🎤",
    label: "Begin Mock Interview",
    desc: "Practice with an AI interviewer",
    tab: "interview" as TabId,
  },
  {
    icon: "📊",
    label: "View My Reports",
    desc: "See trends and improvement areas",
    tab: "reports" as TabId,
  },
];

/* ── Dashboard content ────────────────────────────────────────────────────── */
function DashboardContent({ onTabChange }: { onTabChange: (tab: TabId) => void }) {
  const [resumeCount, setResumeCount] = useState<number | null>(null);

  useEffect(() => {
    listResumes()
      .then((list) => setResumeCount(list.length))
      .catch(() => setResumeCount(0));
  }, []);

  const stats = STATS.map((stat) => {
    if (stat.label === "Resumes Audited") {
      return {
        ...stat,
        value: resumeCount !== null ? String(resumeCount) : "—",
        delta:
          resumeCount !== null && resumeCount > 0
            ? `${resumeCount} resume${resumeCount > 1 ? "s" : ""} analyzed`
            : "Upload your first resume",
      };
    }
    return stat;
  });

  return (
    <>
      {/* Header */}
      <div className="dashboard-header">
        <h1 className="dashboard-greeting">
          Welcome to{" "}
          <span className="gradient-text">PrepAI</span>
        </h1>
        <p className="dashboard-subtitle">
          Your adaptive AI-powered interview preparation platform.
          Let&rsquo;s get you interview-ready.
        </p>
      </div>

      {/* Stat cards */}
      <div className="stats-grid" role="list" aria-label="Dashboard statistics">
        {stats.map((stat) => (
          <StatCard key={stat.label} {...stat} />
        ))}
      </div>

      {/* Two-column content */}
      <div className="content-grid">
        {/* Recent activity */}
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">Recent Activity</span>
            <span className="badge badge-blue">Live</span>
          </div>
          <div className="panel-body">
            <div className="empty-state" style={{ padding: "var(--sp-12) var(--sp-6)" }}>
              <div className="empty-state-illustration">📋</div>
              <p className="empty-state-title">Nothing here yet</p>
              <p className="empty-state-desc">
                Your interview sessions, resume audits, and prep history will
                appear here once you get started.
              </p>
              <button
                className="btn btn-primary btn-sm"
                onClick={() => onTabChange("interview")}
              >
                Start an interview
              </button>
            </div>
          </div>
        </div>

        {/* Quick actions */}
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">Quick Actions</span>
          </div>
          <div className="panel-body">
            <nav className="quick-actions" aria-label="Quick actions">
              {QUICK_ACTIONS.map((action) => (
                <button
                  key={action.label}
                  id={`quick-action-${action.tab}`}
                  className="quick-action-btn"
                  onClick={() => onTabChange(action.tab)}
                  aria-label={action.label}
                >
                  <div className="quick-action-icon" aria-hidden="true">
                    {action.icon}
                  </div>
                  <div>
                    <div className="quick-action-label">{action.label}</div>
                    <div className="quick-action-desc">{action.desc}</div>
                  </div>
                  <span
                    style={{
                      marginLeft: "auto",
                      color: "var(--gray-300)",
                      fontSize: "var(--text-sm)",
                    }}
                    aria-hidden="true"
                  >
                    →
                  </span>
                </button>
              ))}
            </nav>
          </div>
        </div>
      </div>
    </>
  );
}

/* ── Animated tab wrapper ─────────────────────────────────────────────────── */
function TabView({ children, tabKey }: { children: React.ReactNode; tabKey: string }) {
  return (
    <div className="tab-view" key={tabKey}>
      {children}
    </div>
  );
}

/* === Tab router ============================================================ */
function TabContent({
  activeTab,
  activeInterview,
  selectedReportId,
  setSelectedReportId,
  setActiveInterview,
  onTabChange,
}: {
  activeTab: TabId;
  activeInterview: InterviewRecord | null;
  selectedReportId: number | null;
  setSelectedReportId: (id: number | null) => void;
  setActiveInterview: (interview: InterviewRecord | null) => void;
  onTabChange: (tab: TabId) => void;
}) {
  switch (activeTab) {
    case "dashboard":
      return (
        <TabView tabKey="dashboard">
          <DashboardContent onTabChange={onTabChange} />
        </TabView>
      );
    case "resume-audit":
      return (
        <TabView tabKey="resume-audit">
          <ResumeAuditComponent />
        </TabView>
      );
    case "prepare":
      return (
        <TabView tabKey="prepare">
          <PrepareComponent />
        </TabView>
      );
    case "interview":
      if (activeInterview) {
        return (
          <TabView tabKey={`live-${activeInterview.id}`}>
            <LiveInterviewComponent
              interview={activeInterview}
              onExit={() => setActiveInterview(null)}
              onSessionComplete={(interviewId) => {
                setSelectedReportId(interviewId);
                setActiveInterview(null);
                onTabChange("reports");
              }}
            />
          </TabView>
        );
      }
      return (
        <TabView tabKey="interview-setup">
          <InterviewSetupComponent
            onInterviewCreated={(interview) => setActiveInterview(interview)}
          />
        </TabView>
      );
    case "reports":
      if (selectedReportId) {
        return (
          <TabView tabKey={`report-${selectedReportId}`}>
            <ReportCardComponent
              interviewId={selectedReportId}
              onBack={() => setSelectedReportId(null)}
            />
          </TabView>
        );
      }
      return (
        <TabView tabKey="progress">
          <ProgressAnalyticsComponent
            onSelectReport={(interviewId) => setSelectedReportId(interviewId)}
          />
        </TabView>
      );
    default:
      return (
        <TabView tabKey="dashboard">
          <DashboardContent onTabChange={onTabChange} />
        </TabView>
      );
  }
}

/* === Page root ============================================================= */
export default function HomePage() {
  const [activeTab, setActiveTab] = useState<TabId>("dashboard");
  const [activeInterview, setActiveInterview] = useState<InterviewRecord | null>(null);
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);

  return (
    <>
      <Navbar activeTab={activeTab} onTabChange={setActiveTab} />
      <main className="main-content" id="main-content" role="main">
        <TabContent
          activeTab={activeTab}
          activeInterview={activeInterview}
          selectedReportId={selectedReportId}
          setSelectedReportId={setSelectedReportId}
          setActiveInterview={setActiveInterview}
          onTabChange={setActiveTab}
        />
      </main>
    </>
  );
}
