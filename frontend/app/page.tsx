"use client";

import { useState, useEffect } from "react";
import Navbar, { type TabId } from "@/components/Navbar";
import StatCard from "@/components/StatCard";
import ResumeAuditComponent from "@/components/ResumeAudit";
import PrepareComponent from "@/components/Prepare";
import InterviewSetupComponent from "@/components/InterviewSetup";
import LiveInterviewComponent from "@/components/LiveInterview";
import ReportCardComponent from "@/components/ReportCard";
import ProgressAnalyticsComponent from "@/components/ProgressAnalytics";
import {
  listResumes,
  apiListInterviews,
  apiGetCandidateProgress,
  type InterviewRecord,
  type InterviewSessionItem,
  type CandidateProgressRecord,
} from "@/lib/api";

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

interface ActivityItem {
  id: string;
  type: "resume" | "interview_completed" | "interview_in_progress" | "interview_created";
  title: string;
  subtitle: string;
  icon: string;
  createdAt: string;
  badgeText?: string;
  badgeClass?: string;
  targetTab: TabId;
  targetId?: number;
}

function formatRelativeTime(dateStr: string): string {
  if (!dateStr) return "recently";
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return "recently";
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffInSeconds < 30) return "Just now";
  if (diffInSeconds < 60) return `${diffInSeconds}s ago`;
  const diffInMinutes = Math.floor(diffInSeconds / 60);
  if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
  const diffInHours = Math.floor(diffInMinutes / 60);
  if (diffInHours < 24) return `${diffInHours}h ago`;
  const diffInDays = Math.floor(diffInHours / 24);
  if (diffInDays < 7) return `${diffInDays}d ago`;

  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

/* ── Dashboard content ────────────────────────────────────────────────────── */
function DashboardContent({
  onTabChange,
  onSelectReport,
}: {
  onTabChange: (tab: TabId) => void;
  onSelectReport: (id: number) => void;
}) {
  const [loading, setLoading] = useState<boolean>(true);
  const [resumes, setResumes] = useState<{ id: number; file_url?: string; audit_score?: number; created_at: string }[]>([]);
  const [interviews, setInterviews] = useState<InterviewSessionItem[]>([]);

  useEffect(() => {
    let isMounted = true;
    async function loadDashboardData() {
      setLoading(true);
      try {
        const [resList, intList] = await Promise.all([
          listResumes().catch(() => []),
          apiListInterviews().catch(() => []),
        ]);
        if (isMounted) {
          setResumes(resList);
          setInterviews(intList);
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    loadDashboardData();
    return () => {
      isMounted = false;
    };
  }, []);

  // ── Derived Stats ──────────────────────────────────────────────────────────
  const totalSessionsCount = interviews.length;
  const resumesAuditedCount = resumes.length;
  const completedInterviews = interviews.filter((i) => i.status === "completed");
  const completedCount = completedInterviews.length;

  // Calculate Overall Score (Average across completed sessions)
  const scoredSessions = completedInterviews.filter(
    (i) => i.overall_score !== null && i.overall_score !== undefined
  );

  let overallScoreDisplay = "—";
  let overallScoreDelta = "Complete an interview to see";

  if (scoredSessions.length > 0) {
    const avgScore =
      scoredSessions.reduce((acc, curr) => acc + (curr.overall_score || 0), 0) /
      scoredSessions.length;
    overallScoreDisplay = avgScore.toFixed(1);
    overallScoreDelta =
      scoredSessions.length === 1
        ? "From 1 completed session"
        : `Avg across ${scoredSessions.length} completed sessions`;
  }

  const stats = [
    {
      icon: "🎯",
      iconVariant: "blue" as const,
      label: "Sessions",
      value: String(totalSessionsCount),
      delta:
        totalSessionsCount === 0
          ? "No sessions created yet"
          : totalSessionsCount === 1
          ? "1 session configured"
          : `${totalSessionsCount} total sessions created`,
    },
    {
      icon: "📄",
      iconVariant: "green" as const,
      label: "Resumes Audited",
      value: String(resumesAuditedCount),
      delta:
        resumesAuditedCount === 0
          ? "Upload your first resume"
          : resumesAuditedCount === 1
          ? "1 resume analyzed"
          : `${resumesAuditedCount} resumes analyzed`,
    },
    {
      icon: "🎤",
      iconVariant: "purple" as const,
      label: "Interviews Taken",
      value: String(completedCount),
      delta:
        completedCount === 0
          ? "Start your first interview"
          : completedCount === 1
          ? "1 session completed"
          : `${completedCount} sessions completed`,
    },
    {
      icon: "📈",
      iconVariant: "amber" as const,
      label: "Overall Score",
      value: overallScoreDisplay,
      delta: overallScoreDelta,
    },
  ];

  // ── Derived Timeline Activities ────────────────────────────────────────────
  const activities: ActivityItem[] = [];

  // Add Resumes
  resumes.forEach((r) => {
    const filename = r.file_url ? r.file_url.split("/").pop()?.replace(/^[a-f0-9]+_/, "") : null;
    activities.push({
      id: `resume-${r.id}`,
      type: "resume",
      icon: "📄",
      title: filename ? `Resume Audited: ${filename}` : "Resume Audited",
      subtitle:
        r.audit_score !== undefined && r.audit_score !== null
          ? `Overall Quality Score: ${r.audit_score}/100`
          : "Resume text extracted & parsed",
      createdAt: r.created_at,
      badgeText: r.audit_score ? `${r.audit_score}/100` : "Audited",
      badgeClass: "badge-green",
      targetTab: "resume-audit",
    });
  });

  // Add Interviews
  interviews.forEach((i) => {
    if (i.status === "completed") {
      activities.push({
        id: `interview-comp-${i.id}`,
        type: "interview_completed",
        icon: "🏆",
        title: `${i.role} — ${i.interview_type.toUpperCase()} Mock`,
        subtitle:
          i.overall_score !== null && i.overall_score !== undefined
            ? `Completed session with score ${i.overall_score.toFixed(1)}/10`
            : "Completed mock interview session",
        createdAt: i.completed_at || i.created_at,
        badgeText: i.overall_score ? `${i.overall_score.toFixed(1)}/10` : "Completed",
        badgeClass: "badge-green",
        targetTab: "reports",
        targetId: i.id,
      });
    } else if (i.status === "in_progress") {
      activities.push({
        id: `interview-prog-${i.id}`,
        type: "interview_in_progress",
        icon: "🎤",
        title: `${i.role} — In Progress`,
        subtitle: `${i.difficulty_mode} mode · ${i.question_count} questions`,
        createdAt: i.created_at,
        badgeText: "In Progress",
        badgeClass: "badge-amber",
        targetTab: "interview",
        targetId: i.id,
      });
    } else {
      activities.push({
        id: `interview-sched-${i.id}`,
        type: "interview_created",
        icon: "🎯",
        title: `${i.role} Session Configured`,
        subtitle: `${i.interview_type} format · ${i.difficulty_mode} difficulty`,
        createdAt: i.created_at,
        badgeText: "Configured",
        badgeClass: "badge-blue",
        targetTab: "interview",
        targetId: i.id,
      });
    }
  });

  // Sort activities by createdAt descending
  activities.sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  );

  const topActivities = activities.slice(0, 7);

  const handleActivityClick = (item: ActivityItem) => {
    if (item.targetTab === "reports" && item.targetId) {
      onSelectReport(item.targetId);
      onTabChange("reports");
    } else {
      onTabChange(item.targetTab);
    }
  };

  return (
    <>
      {/* Header */}
      <div className="dashboard-header">
        <h1 className="dashboard-greeting">
          Welcome to <span className="gradient-text">PrepAI</span>
        </h1>
        <p className="dashboard-subtitle">
          Your adaptive AI-powered interview preparation platform. Let&rsquo;s get you interview-ready.
        </p>
      </div>

      {/* Stat cards */}
      <div className="stats-grid" role="list" aria-label="Dashboard statistics">
        {loading ? (
          <>
            {[1, 2, 3, 4].map((n) => (
              <div key={n} className="stat-card" style={{ pointerEvents: "none" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--sp-3)" }}>
                  <div className="skeleton" style={{ width: 40, height: 40, borderRadius: "var(--r-md)" }} />
                  <div className="skeleton" style={{ width: 60, height: 16 }} />
                </div>
                <div className="skeleton" style={{ width: 80, height: 36, marginBottom: "var(--sp-2)" }} />
                <div className="skeleton" style={{ width: 120, height: 14 }} />
              </div>
            ))}
          </>
        ) : (
          stats.map((stat) => <StatCard key={stat.label} {...stat} />)
        )}
      </div>

      {/* Two-column content */}
      <div className="content-grid">
        {/* Recent activity */}
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">Recent Activity</span>
            {!loading && topActivities.length > 0 && (
              <span className="badge badge-blue">{topActivities.length} Events</span>
            )}
          </div>
          <div className="panel-body">
            {loading ? (
              <div className="activity-list">
                {[1, 2, 3, 4].map((n) => (
                  <div key={n} style={{ display: "flex", alignItems: "center", gap: "var(--sp-3)", padding: "var(--sp-3) var(--sp-4)" }}>
                    <div className="skeleton" style={{ width: 38, height: 38, borderRadius: "var(--r-md)", flexShrink: 0 }} />
                    <div style={{ flex: 1 }}>
                      <div className="skeleton" style={{ width: "60%", height: 16, marginBottom: 6 }} />
                      <div className="skeleton" style={{ width: "40%", height: 12 }} />
                    </div>
                    <div className="skeleton" style={{ width: 50, height: 14 }} />
                  </div>
                ))}
              </div>
            ) : topActivities.length > 0 ? (
              <div className="activity-list" role="list">
                {topActivities.map((act) => (
                  <button
                    key={act.id}
                    type="button"
                    className="activity-item"
                    onClick={() => handleActivityClick(act)}
                  >
                    <div className="activity-icon" aria-hidden="true">
                      {act.icon}
                    </div>
                    <div className="activity-content">
                      <div className="activity-title">{act.title}</div>
                      <div className="activity-subtitle">{act.subtitle}</div>
                    </div>
                    <div className="activity-meta">
                      {act.badgeText && (
                        <span className={`badge ${act.badgeClass || "badge-blue"}`}>
                          {act.badgeText}
                        </span>
                      )}
                      <span className="activity-time">{formatRelativeTime(act.createdAt)}</span>
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="empty-state" style={{ padding: "var(--sp-12) var(--sp-6)" }}>
                <div className="empty-state-illustration">📋</div>
                <p className="empty-state-title">Nothing here yet</p>
                <p className="empty-state-desc">
                  Your interview sessions, resume audits, and prep history will appear here once you get started.
                </p>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => onTabChange("interview")}
                >
                  Start an interview
                </button>
              </div>
            )}
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
          <DashboardContent
            onTabChange={onTabChange}
            onSelectReport={(id) => setSelectedReportId(id)}
          />
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
          <DashboardContent
            onTabChange={onTabChange}
            onSelectReport={(id) => setSelectedReportId(id)}
          />
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
