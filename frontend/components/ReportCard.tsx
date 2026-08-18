"use client";

import { useState, useEffect } from "react";
import {
  apiGetInterviewReport,
  apiCompleteInterview,
  type InterviewReportRecord,
  type DetailedQuestionAnswer,
} from "@/lib/api";

interface ReportCardProps {
  interviewId: number;
  initialReport?: InterviewReportRecord | null;
  onBack?: () => void;
}

const METRICS = [
  { key: "avg_technical_score",    label: "Technical Accuracy",      weight: "40%", color: "var(--brand-500)" },
  { key: "avg_relevance_score",    label: "Relevance & Directness",  weight: "30%", color: "#7c3aed" },
  { key: "avg_completeness_score", label: "Completeness & Depth",    weight: "20%", color: "#0891b2" },
  { key: "avg_clarity_score",      label: "Communication Clarity",   weight: "10%", color: "var(--success-text)" },
] as const;

function scoreLabel(score: number) {
  if (score >= 8.0) return "🌟 Excellent Performance";
  if (score >= 6.5) return "👍 Interview Ready";
  if (score >= 5.0) return "📈 Developing Skills";
  return "🔁 Keep Practicing";
}

function scoreBadgeStyle(score: number): React.CSSProperties {
  if (score >= 6.5) return { background: "rgba(16,185,129,0.15)", color: "#d1fae5" };
  if (score >= 5.0) return { background: "rgba(99,102,241,0.2)", color: "#c7d2fe" };
  return { background: "rgba(245,158,11,0.2)", color: "#fde68a" };
}

export default function ReportCardComponent({
  interviewId,
  initialReport = null,
  onBack,
}: ReportCardProps) {
  const [report, setReport] = useState<InterviewReportRecord | null>(initialReport);
  const [loading, setLoading] = useState<boolean>(!initialReport);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => {
    if (initialReport) { setReport(initialReport); setLoading(false); return; }
    async function load() {
      setLoading(true);
      setError(null);
      try {
        try {
          setReport(await apiGetInterviewReport(interviewId));
        } catch {
          setReport(await apiCompleteInterview(interviewId));
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load interview report.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [interviewId, initialReport]);

  /* ── Loading ───────────────────────────────── */
  if (loading) {
    return (
      <div className="card" style={{ maxWidth: 860, margin: "0 auto" }}>
        <div className="card-body">
          <div className="page-loading" style={{ minHeight: "30vh" }}>
            <div className="spinner" />
            <div>
              <p className="page-loading-title">Generating Performance Report…</p>
              <p className="page-loading-sub">
                Computing aggregate scores and generating personalized AI insights.
                This may take a moment.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  /* ── Error ─────────────────────────────────── */
  if (error || !report) {
    return (
      <div className="card" style={{ maxWidth: 760, margin: "0 auto" }}>
        <div className="card-body">
          <div className="alert alert-error" role="alert" style={{ marginBottom: "var(--sp-4)" }}>
            <span>⚠️</span>
            <span>{error || "Report not available."}</span>
          </div>
          {onBack && (
            <button className="btn btn-secondary" onClick={onBack}>
              ← Back to Reports
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--sp-6)" }}>

      {/* ── Back + session ID ─────────────────── */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "var(--sp-3)" }}>
        {onBack && (
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={onBack}
            style={{ paddingLeft: 0 }}
          >
            ← Back to Progress
          </button>
        )}
        <div style={{ display: "flex", alignItems: "center", gap: "var(--sp-2)", marginLeft: "auto" }}>
          <span className="badge badge-green">✓ Completed</span>
          <span style={{ fontSize: "var(--text-xs)", color: "var(--gray-400)" }}>
            Interview #{report.interview_id}
          </span>
        </div>
      </div>

      {/* ── Dark banner ───────────────────────── */}
      <div
        style={{
          background: "linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%)",
          color: "#fff",
          borderRadius: "var(--r-2xl)",
          padding: "var(--sp-8)",
          display: "flex",
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "var(--sp-8)",
          flexWrap: "wrap",
          boxShadow: "var(--shadow-lg)",
        }}
      >
        {/* Left: role + summary */}
        <div style={{ flex: 1, minWidth: 240 }}>
          <div
            style={{
              display: "inline-flex", alignItems: "center", gap: "var(--sp-2)",
              padding: "3px 12px",
              background: "rgba(99,102,241,0.2)",
              color: "#a5b4fc",
              borderRadius: "var(--r-full)",
              fontSize: "var(--text-xs)", fontWeight: 700,
              textTransform: "uppercase", letterSpacing: "0.06em",
              marginBottom: "var(--sp-3)",
              border: "1px solid rgba(99,102,241,0.25)",
            }}
          >
            🎯 Performance Report Card
          </div>
          <h1 style={{ fontSize: "var(--text-2xl)", fontWeight: 800, lineHeight: 1.2, letterSpacing: "-0.3px", marginBottom: "var(--sp-3)" }}>
            {report.role}
          </h1>
          <p style={{ fontSize: "var(--text-sm)", color: "#94a3b8", lineHeight: 1.65, maxWidth: 500 }}>
            {report.executive_summary ||
              `Evaluated across ${report.questions.length} question${report.questions.length !== 1 ? "s" : ""} in ${report.interview_type} format under ${report.difficulty_mode} difficulty mode.`}
          </p>
        </div>

        {/* Right: score gauge */}
        <div
          style={{
            background: "rgba(255,255,255,0.08)",
            border: "1px solid rgba(255,255,255,0.15)",
            borderRadius: "var(--r-xl)",
            padding: "var(--sp-6) var(--sp-8)",
            textAlign: "center",
            backdropFilter: "blur(8px)",
            minWidth: 180,
            flexShrink: 0,
          }}
        >
          <div style={{ fontSize: "var(--text-xs)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "#94a3b8", marginBottom: "var(--sp-2)" }}>
            Overall Score
          </div>
          <div style={{ fontSize: "3rem", fontWeight: 900, letterSpacing: "-2px", lineHeight: 1, color: "#fff" }}>
            {report.overall_score.toFixed(1)}
            <span style={{ fontSize: "var(--text-xl)", fontWeight: 400, color: "#64748b" }}> /10</span>
          </div>
          <div
            style={{
              marginTop: "var(--sp-3)",
              display: "inline-block",
              padding: "3px 12px",
              borderRadius: "var(--r-full)",
              fontSize: "var(--text-xs)",
              fontWeight: 600,
              ...scoreBadgeStyle(report.overall_score),
            }}
          >
            {scoreLabel(report.overall_score)}
          </div>
        </div>
      </div>

      {/* ── Dimensional scores ────────────────── */}
      <div className="card">
        <div className="card-header">
          <div>
            <h2 className="text-title">Dimensional Scoring</h2>
            <p className="text-sm" style={{ marginTop: "var(--sp-1)" }}>
              Aggregate performance computed from real per-question evaluation vectors.
            </p>
          </div>
        </div>
        <div className="card-body">
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
              gap: "var(--sp-4)",
            }}
          >
            {METRICS.map((m) => {
              const score = report[m.key as keyof InterviewReportRecord] as number;
              return (
                <div
                  key={m.key}
                  style={{
                    padding: "var(--sp-4)",
                    background: "var(--gray-50)",
                    borderRadius: "var(--r-lg)",
                    border: "1px solid var(--border)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--sp-3)" }}>
                    <span style={{ fontSize: "var(--text-sm)", fontWeight: 600, color: "var(--gray-800)" }}>{m.label}</span>
                    <span style={{ fontWeight: 800, color: "var(--gray-900)", fontSize: "var(--text-base)" }}>{score.toFixed(1)}</span>
                  </div>
                  <div className="progress-bar-track">
                    <div
                      className="progress-bar-fill"
                      style={{ width: `${(score / 10) * 100}%`, background: m.color }}
                    />
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "var(--text-xs)", color: "var(--gray-400)", marginTop: "var(--sp-2)" }}>
                    <span>0.0</span>
                    <span style={{ fontWeight: 600 }}>{m.weight} weight</span>
                    <span>10.0</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── Strengths & Weaknesses ────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "var(--sp-5)" }}>
        {/* Strengths */}
        <div className="card" style={{ borderColor: "var(--success-border)" }}>
          <div className="card-header" style={{ borderBottomColor: "var(--success-border)" }}>
            <h3 style={{ fontWeight: 700, fontSize: "var(--text-base)", color: "var(--success-text)", display: "flex", alignItems: "center", gap: "var(--sp-2)" }}>
              ✅ Key Strengths
            </h3>
          </div>
          <div className="card-body">
            {report.strengths && report.strengths.length > 0 ? (
              <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "var(--sp-3)" }}>
                {report.strengths.map((item, i) => (
                  <li key={i} style={{ display: "flex", gap: "var(--sp-3)", alignItems: "flex-start", fontSize: "var(--text-sm)", color: "var(--gray-700)", lineHeight: 1.6 }}>
                    <span style={{ color: "var(--success-text)", fontWeight: 700, flexShrink: 0 }}>•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p style={{ fontSize: "var(--text-sm)", color: "var(--gray-400)" }}>No specific strengths logged for this session.</p>
            )}
          </div>
        </div>

        {/* Weaknesses */}
        <div className="card" style={{ borderColor: "var(--warning-border)" }}>
          <div className="card-header" style={{ borderBottomColor: "var(--warning-border)" }}>
            <h3 style={{ fontWeight: 700, fontSize: "var(--text-base)", color: "var(--warning-text)", display: "flex", alignItems: "center", gap: "var(--sp-2)" }}>
              ⚠️ Areas for Growth
            </h3>
          </div>
          <div className="card-body">
            {report.weaknesses && report.weaknesses.length > 0 ? (
              <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "var(--sp-3)" }}>
                {report.weaknesses.map((item, i) => (
                  <li key={i} style={{ display: "flex", gap: "var(--sp-3)", alignItems: "flex-start", fontSize: "var(--text-sm)", color: "var(--gray-700)", lineHeight: 1.6 }}>
                    <span style={{ color: "var(--warning-text)", fontWeight: 700, flexShrink: 0 }}>•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p style={{ fontSize: "var(--text-sm)", color: "var(--gray-400)" }}>No weaknesses recorded for this session.</p>
            )}
          </div>
        </div>
      </div>

      {/* ── Recommendation ───────────────────── */}
      {report.recommendations && (
        <div
          className="card"
          style={{ borderColor: "var(--brand-200)", background: "var(--brand-50)" }}
        >
          <div className="card-header" style={{ borderBottomColor: "var(--brand-200)" }}>
            <h3 style={{ fontWeight: 700, fontSize: "var(--text-base)", color: "var(--brand-700)", display: "flex", alignItems: "center", gap: "var(--sp-2)" }}>
              💡 Personalized Study Roadmap
            </h3>
          </div>
          <div className="card-body">
            <p style={{ fontSize: "var(--text-base)", color: "var(--brand-900)", lineHeight: 1.7 }}>
              {report.recommendations}
            </p>
          </div>
        </div>
      )}

      {/* ── Per-question accordion ────────────── */}
      <div className="card">
        <div className="card-header">
          <div>
            <h2 className="text-title">Per-Question Breakdown</h2>
            <p className="text-sm" style={{ marginTop: "var(--sp-1)" }}>
              Review your answers, individual scores, and specific AI feedback.
            </p>
          </div>
          <span className="badge badge-gray">{report.questions.length} questions</span>
        </div>
        <div className="card-body" style={{ display: "flex", flexDirection: "column", gap: "var(--sp-3)" }}>
          {report.questions.map((q: DetailedQuestionAnswer) => {
            const isExpanded = expandedId === q.question_id;
            return (
              <div
                key={q.question_id}
                className="card"
                style={{
                  border: isExpanded ? "1.5px solid var(--brand-400)" : "1.5px solid var(--border)",
                  boxShadow: isExpanded ? "var(--shadow-sm)" : "none",
                  transition: "border-color var(--dur-fast) var(--ease)",
                }}
              >
                {/* Question header row */}
                <button
                  type="button"
                  onClick={() => setExpandedId(isExpanded ? null : q.question_id)}
                  style={{
                    width: "100%",
                    display: "flex",
                    alignItems: "center",
                    gap: "var(--sp-3)",
                    padding: "var(--sp-4) var(--sp-5)",
                    background: "transparent",
                    border: "none",
                    cursor: "pointer",
                    textAlign: "left",
                    borderRadius: "var(--r-xl)",
                  }}
                  aria-expanded={isExpanded}
                >
                  <span
                    style={{
                      width: 32, height: 32, flexShrink: 0,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      background: "var(--brand-50)",
                      color: "var(--brand-700)",
                      borderRadius: "var(--r-full)",
                      fontSize: "var(--text-xs)",
                      fontWeight: 800,
                      border: "1px solid var(--brand-200)",
                    }}
                  >
                    {q.order_index}
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontWeight: 600, color: "var(--gray-900)", fontSize: "var(--text-sm)", lineHeight: 1.45, overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 1, WebkitBoxOrient: "vertical" }}>
                      {q.question_text}
                    </p>
                    <div style={{ display: "flex", gap: "var(--sp-2)", marginTop: "var(--sp-1)", flexWrap: "wrap" }}>
                      <span className="badge badge-gray" style={{ textTransform: "capitalize" }}>{q.category.replace(/_/g, " ")}</span>
                      <span className="badge badge-blue" style={{ textTransform: "capitalize" }}>{q.difficulty}</span>
                    </div>
                  </div>
                  <div style={{ textAlign: "right", flexShrink: 0 }}>
                    <div style={{ fontSize: "var(--text-xs)", color: "var(--gray-400)", marginBottom: 2 }}>Score</div>
                    <div style={{ fontWeight: 800, color: "var(--gray-900)", fontSize: "var(--text-base)" }}>
                      {q.overall_score.toFixed(1)}<span style={{ color: "var(--gray-400)", fontWeight: 400 }}>/10</span>
                    </div>
                  </div>
                  <span style={{ color: "var(--gray-400)", fontSize: "var(--text-sm)", marginLeft: "var(--sp-2)", flexShrink: 0 }}>
                    {isExpanded ? "▲" : "▼"}
                  </span>
                </button>

                {/* Expanded content */}
                {isExpanded && (
                  <div style={{ padding: "0 var(--sp-5) var(--sp-5)", display: "flex", flexDirection: "column", gap: "var(--sp-4)", borderTop: "1px solid var(--border)", paddingTop: "var(--sp-4)" }}>
                    {/* Full question */}
                    <div>
                      <p style={{ fontSize: "var(--text-xs)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--gray-400)", marginBottom: "var(--sp-2)" }}>
                        Question Prompt
                      </p>
                      <p style={{ fontSize: "var(--text-sm)", fontWeight: 600, color: "var(--gray-900)", lineHeight: 1.55 }}>{q.question_text}</p>
                    </div>

                    {/* Candidate answer */}
                    <div style={{ background: "var(--gray-50)", border: "1px solid var(--border)", borderRadius: "var(--r-lg)", padding: "var(--sp-4)" }}>
                      <p style={{ fontSize: "var(--text-xs)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--gray-400)", marginBottom: "var(--sp-2)" }}>
                        Your Response
                      </p>
                      <p style={{ fontSize: "var(--text-sm)", color: "var(--gray-800)", whiteSpace: "pre-wrap", lineHeight: 1.65, fontFamily: "var(--font-sans)" }}>
                        {q.answer_text || "No response submitted."}
                      </p>
                    </div>

                    {/* Score matrix */}
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "repeat(4, 1fr)",
                        gap: "var(--sp-3)",
                        background: "var(--gray-50)",
                        border: "1px solid var(--border)",
                        borderRadius: "var(--r-lg)",
                        padding: "var(--sp-4)",
                        textAlign: "center",
                      }}
                    >
                      {[
                        { label: "Technical", val: q.technical_score },
                        { label: "Relevance", val: q.relevance_score },
                        { label: "Completeness", val: q.completeness_score },
                        { label: "Clarity", val: q.clarity_score },
                      ].map((s) => (
                        <div key={s.label}>
                          <div style={{ fontSize: "var(--text-xs)", color: "var(--gray-500)", marginBottom: "var(--sp-1)" }}>{s.label}</div>
                          <div style={{ fontWeight: 800, color: "var(--gray-900)", fontSize: "var(--text-base)" }}>{s.val.toFixed(1)}</div>
                        </div>
                      ))}
                    </div>

                    {/* AI Feedback */}
                    <div
                      style={{
                        background: "var(--success-bg)",
                        border: "1px solid var(--success-border)",
                        borderRadius: "var(--r-lg)",
                        padding: "var(--sp-4)",
                      }}
                    >
                      <p style={{ fontSize: "var(--text-xs)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--success-text)", marginBottom: "var(--sp-2)" }}>
                        💬 AI Feedback
                      </p>
                      <p style={{ fontSize: "var(--text-sm)", color: "var(--gray-800)", lineHeight: 1.7 }}>{q.feedback_text}</p>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
