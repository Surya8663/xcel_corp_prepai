"use client";

import { useState, useEffect } from "react";
import { apiGetCandidateProgress, type CandidateProgressRecord } from "@/lib/api";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface ProgressAnalyticsProps {
  onSelectReport?: (interviewId: number) => void;
}

export default function ProgressAnalyticsComponent({
  onSelectReport,
}: ProgressAnalyticsProps) {
  const [history, setHistory] = useState<CandidateProgressRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadProgress() {
      setLoading(true);
      setError(null);
      try {
        const records = await apiGetCandidateProgress();
        setHistory(records);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Failed to load progress history.";
        setError(msg);
      } finally {
        setLoading(false);
      }
    }
    loadProgress();
  }, []);

  /* ── Loading ─────────────────────────────────────────────── */
  if (loading) {
    return (
      <div className="card" style={{ maxWidth: 860, margin: "0 auto" }}>
        <div className="card-body">
          <div className="page-loading" style={{ minHeight: "30vh" }}>
            <div className="spinner" />
            <div>
              <p className="page-loading-title">Loading Historical Progress…</p>
              <p className="page-loading-sub">
                Fetching your completed interview sessions and performance data.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const completedCount = history.length;
  const maxScore =
    completedCount > 0 ? Math.max(...history.map((h) => h.overall_score)) : 0;
  const avgScore =
    completedCount > 0
      ? (history.reduce((acc, h) => acc + h.overall_score, 0) / completedCount).toFixed(1)
      : null;

  const chartData = history.map((rec, index) => ({
    session: `Session #${rec.interview_id}`,
    shortLabel: `#${rec.interview_id}`,
    score: Number(rec.overall_score.toFixed(1)),
    role: rec.role,
    date: rec.completed_at ? new Date(rec.completed_at).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : `S${index + 1}`,
  }));

  /* ── Render ──────────────────────────────────────────────── */
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--sp-6)" }}>

      {/* ── Page header ─────────────────────────────────────── */}
      <div>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "var(--sp-2)",
            padding: "3px var(--sp-3)",
            background: "var(--brand-50)",
            color: "var(--brand-700)",
            borderRadius: "var(--r-full)",
            fontSize: "var(--text-xs)",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            marginBottom: "var(--sp-3)",
            border: "1px solid var(--brand-200)",
          }}
        >
          📊 Historical Performance
        </div>
        <h1 style={{ fontSize: "var(--text-3xl)", fontWeight: 800, color: "var(--gray-900)", letterSpacing: "-0.4px", lineHeight: 1.2 }}>
          Candidate Progress &amp; Growth
        </h1>
        <p style={{ fontSize: "var(--text-sm)", color: "var(--gray-500)", marginTop: "var(--sp-2)" }}>
          Track your interview readiness score progression across mock sessions over time.
        </p>
      </div>

      {/* ── Error ───────────────────────────────────────────── */}
      {error && (
        <div className="alert alert-error" role="alert">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {/* ── Summary stat cards ───────────────────────────────── */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "var(--sp-4)",
        }}
      >
        {[
          { icon: "🎯", color: "var(--brand-50)", label: "Completed Sessions", value: String(completedCount) },
          { icon: "🏆", color: "var(--success-bg)", label: "Highest Score", value: completedCount > 0 ? `${maxScore.toFixed(1)} / 10` : "—" },
          { icon: "📈", color: "var(--gray-50)", label: "Average Score", value: avgScore ? `${avgScore} / 10` : "—" },
        ].map((s) => (
          <div key={s.label} className="card card-hover">
            <div className="card-body" style={{ display: "flex", alignItems: "center", gap: "var(--sp-4)" }}>
              <div
                style={{
                  width: 44, height: 44,
                  borderRadius: "var(--r-xl)",
                  background: s.color,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "1.5rem", flexShrink: 0,
                }}
                aria-hidden="true"
              >
                {s.icon}
              </div>
              <div>
                <div className="text-xs text-muted" style={{ textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 700, marginBottom: "var(--sp-1)" }}>
                  {s.label}
                </div>
                <div style={{ fontSize: "var(--text-2xl)", fontWeight: 800, color: "var(--gray-900)", letterSpacing: "-0.5px" }}>
                  {s.value}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* ── Score trend chart ────────────────────────────────── */}
      <div className="card">
        <div className="card-header">
          <div>
            <h2 className="text-title" style={{ fontSize: "var(--text-xl)" }}>Score Trend Over Time</h2>
            <p className="text-sm" style={{ marginTop: "var(--sp-1)" }}>
              Chronological score trajectory across completed mock interviews.
            </p>
          </div>
        </div>
        <div className="card-body">
          {completedCount < 2 ? (
            <div className="empty-state" style={{ padding: "var(--sp-12) var(--sp-6)" }}>
              <div className="empty-state-illustration">📈</div>
              <p className="empty-state-title">Complete more sessions to see trends</p>
              <p className="empty-state-desc">
                You have <strong>{completedCount}</strong> completed session.
                Complete at least 2 sessions to unlock score trajectory charts and identify
                improvement patterns over time.
              </p>
            </div>
          ) : (
            <div style={{ width: "100%", height: 260, marginTop: "var(--sp-2)" }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 20, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--brand-500)" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="var(--brand-500)" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--gray-200)" />
                  <XAxis
                    dataKey="shortLabel"
                    stroke="var(--gray-400)"
                    tick={{ fill: "var(--gray-600)", fontSize: 12, fontWeight: 600 }}
                  />
                  <YAxis
                    domain={[0, 10]}
                    stroke="var(--gray-400)"
                    tick={{ fill: "var(--gray-600)", fontSize: 12, fontWeight: 600 }}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "var(--surface)",
                      border: "1px solid var(--border-strong)",
                      borderRadius: "var(--r-lg)",
                      boxShadow: "var(--shadow-md)",
                      fontSize: "var(--text-xs)",
                    }}
                    formatter={(value: any) => [`${value} / 10`, "Overall Score"]}
                    labelFormatter={(label: any, items: any) => {
                      const item = items[0]?.payload;
                      return item ? `${item.session} (${item.role})` : label;
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="score"
                    stroke="var(--brand-600)"
                    strokeWidth={3}
                    fillOpacity={1}
                    fill="url(#scoreGradient)"
                    dot={{ r: 5, fill: "var(--brand-600)", stroke: "#ffffff", strokeWidth: 2 }}
                    activeDot={{ r: 7, fill: "var(--brand-700)" }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      {/* ── History table ────────────────────────────────────── */}
      {completedCount > 0 && (
        <div className="card">
          <div className="card-header">
            <h2 className="text-title" style={{ fontSize: "var(--text-xl)" }}>Session History</h2>
            <span className="badge badge-gray">{completedCount} sessions</span>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table
              style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--text-sm)" }}
              aria-label="Completed interview sessions"
            >
              <thead>
                <tr
                  style={{
                    borderBottom: "1.5px solid var(--border)",
                    textAlign: "left",
                  }}
                >
                  {["Session", "Target Role", "Format", "Mode", "Score", ""].map((h) => (
                    <th
                      key={h}
                      style={{
                        padding: "var(--sp-3) var(--sp-5)",
                        fontSize: "var(--text-xs)",
                        fontWeight: 700,
                        color: "var(--gray-400)",
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                        whiteSpace: "nowrap",
                        textAlign: h === "" ? "right" : "left",
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {history.map((rec) => (
                  <tr
                    key={rec.interview_id}
                    style={{ borderBottom: "1px solid var(--border)" }}
                    onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--gray-50)"; }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "transparent"; }}
                  >
                    <td style={{ padding: "var(--sp-4) var(--sp-5)", fontWeight: 700, color: "var(--gray-900)", whiteSpace: "nowrap" }}>
                      #{rec.interview_id}
                    </td>
                    <td style={{ padding: "var(--sp-4) var(--sp-5)", color: "var(--gray-800)", fontWeight: 500, maxWidth: 240 }}>
                      <span style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {rec.role}
                      </span>
                    </td>
                    <td style={{ padding: "var(--sp-4) var(--sp-5)", color: "var(--gray-600)", textTransform: "capitalize" }}>
                      {rec.interview_type}
                    </td>
                    <td style={{ padding: "var(--sp-4) var(--sp-5)", color: "var(--gray-600)", textTransform: "capitalize" }}>
                      {rec.difficulty_mode}
                    </td>
                    <td style={{ padding: "var(--sp-4) var(--sp-5)", whiteSpace: "nowrap" }}>
                      <span
                        style={{
                          fontWeight: 800,
                          color: rec.overall_score >= 7 ? "var(--success-text)" : rec.overall_score >= 5 ? "var(--brand-600)" : "var(--warning-text)",
                        }}
                      >
                        {rec.overall_score.toFixed(1)} / 10
                      </span>
                    </td>
                    <td style={{ padding: "var(--sp-4) var(--sp-5)", textAlign: "right" }}>
                      {onSelectReport && (
                        <button
                          type="button"
                          className="btn btn-sm btn-outline"
                          onClick={() => onSelectReport(rec.interview_id)}
                        >
                          View Report
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── True empty state (no sessions at all) ────────────── */}
      {completedCount === 0 && !error && (
        <div className="card">
          <div className="card-body">
            <div className="empty-state">
              <div className="empty-state-illustration">🎤</div>
              <p className="empty-state-title">No completed interviews yet</p>
              <p className="empty-state-desc">
                Complete your first mock interview to see performance metrics,
                score trends, and AI-generated insights appear here.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
