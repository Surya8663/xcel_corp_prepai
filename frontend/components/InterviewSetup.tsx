"use client";

import { useState, useEffect } from "react";
import {
  createInterview,
  listJobDescriptions,
  listResumes,
  uploadJobDescription,
  type InterviewRecord,
  type JobDescriptionRecord,
} from "@/lib/api";

const PRESET_ROLES = [
  "Senior Backend Engineer",
  "Full Stack Developer",
  "Frontend Engineer (React/Next.js)",
  "DevOps / Infrastructure Engineer",
  "AI / GenAI Engineer",
  "System Architect",
];

const INTERVIEW_TYPES = [
  {
    id: "Technical",
    title: "Technical Interview",
    icon: "💻",
    description: "Deep dive into system design, algorithms, databases, API architecture, and live coding trade-offs.",
  },
  {
    id: "HR",
    title: "HR Screening",
    icon: "🤝",
    description: "Evaluate cultural fit, communication clarity, career trajectory, expectations, and interpersonal alignment.",
  },
  {
    id: "Behavioral",
    title: "Behavioral (STAR)",
    icon: "🎯",
    description: "STAR method scenarios: conflict resolution, leadership, handling failure, cross-team collaboration.",
  },
  {
    id: "System Design",
    title: "System Design",
    icon: "🏗️",
    description: "High-scale architectural trade-offs, caching, message queues, sharding, and fault tolerance.",
  },
];

const DIFFICULTY_MODES = [
  {
    id: "Easy",
    title: "Easy",
    icon: "🌱",
    badgeClass: "badge-green",
    description: "Foundational questions to build confidence and refine basic technical articulation.",
  },
  {
    id: "Medium",
    title: "Medium",
    icon: "⚡",
    badgeClass: "badge-blue",
    description: "Standard industry interview rigor testing core mechanics, trade-offs, and edge cases.",
  },
  {
    id: "Hard",
    title: "Hard",
    icon: "🔥",
    badgeClass: "badge-amber",
    description: "Complex distributed systems, performance bottleneck analysis, and deep architectural questions.",
  },
  {
    id: "Adaptive",
    title: "Adaptive AI",
    icon: "🧠",
    badgeClass: "badge-purple",
    description: "Starts at Medium difficulty and dynamically escalates or softens based on your answer evaluation in real time.",
  },
];

const DURATION_OPTIONS = [15, 30, 45, 60];
const QUESTION_COUNT_OPTIONS = [3, 5, 8, 10];

interface InterviewSetupProps {
  onInterviewCreated?: (interview: InterviewRecord) => void;
}

export default function InterviewSetupComponent({ onInterviewCreated }: InterviewSetupProps) {
  // Stepper state (Step 1 to 5)
  const [currentStep, setCurrentStep] = useState<number>(1);

  // Form State
  const [selectedRole, setSelectedRole] = useState<string>("Senior Backend Engineer");
  const [customRole, setCustomRole] = useState<string>("");
  const [interviewType, setInterviewType] = useState<string>("Technical");
  const [difficultyMode, setDifficultyMode] = useState<string>("Adaptive");
  const [durationMinutes, setDurationMinutes] = useState<number>(30);
  const [questionCount, setQuestionCount] = useState<number>(5);

  // Context Attachments State
  const [contextTab, setContextTab] = useState<"none" | "resume" | "jd">("none");
  const [resumes, setResumes] = useState<{ id: number; file_url?: string; audit_score?: number; created_at: string }[]>([]);
  const [jobDescriptions, setJobDescriptions] = useState<JobDescriptionRecord[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<number | null>(null);
  const [selectedJdId, setSelectedJdId] = useState<number | null>(null);
  const [pastedJdText, setPastedJdText] = useState<string>("");

  // UI state
  const [loadingContext, setLoadingContext] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [savingJd, setSavingJd] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [createdInterview, setCreatedInterview] = useState<InterviewRecord | null>(null);

  useEffect(() => {
    fetchContextData();
  }, []);

  const fetchContextData = async () => {
    setLoadingContext(true);
    try {
      const [rList, jList] = await Promise.all([
        listResumes().catch(() => []),
        listJobDescriptions().catch(() => []),
      ]);
      setResumes(rList);
      setJobDescriptions(jList);
      if (rList.length > 0) {
        setSelectedResumeId(rList[0].id);
      }
      if (jList.length > 0) {
        setSelectedJdId(jList[0].id);
      }
    } catch {
      // Ignore initial load context fetch errors
    } finally {
      setLoadingContext(false);
    }
  };

  const getEffectiveRole = () => {
    if (selectedRole === "Custom") {
      return customRole.trim() || "Software Engineer";
    }
    return selectedRole;
  };

  const handleSavePastedJd = async () => {
    if (!pastedJdText.trim() || pastedJdText.trim().length < 10) {
      setError("Please paste a valid job description text (at least 10 characters).");
      return;
    }
    setSavingJd(true);
    setError(null);
    try {
      const newJd = await uploadJobDescription(pastedJdText.trim());
      setJobDescriptions((prev) => [newJd, ...prev]);
      setSelectedJdId(newJd.id);
      setPastedJdText("");
      setContextTab("jd");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to parse job description.";
      setError(msg);
    } finally {
      setSavingJd(false);
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        role: getEffectiveRole(),
        interview_type: interviewType,
        difficulty_mode: difficultyMode,
        duration_minutes: durationMinutes,
        question_count: questionCount,
        resume_id: contextTab === "resume" ? selectedResumeId : null,
        job_description_id: contextTab === "jd" ? selectedJdId : null,
      };

      const result = await createInterview(payload);
      setCreatedInterview(result);
      if (onInterviewCreated) {
        onInterviewCreated(result);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create mock interview session.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: 860, margin: "0 auto" }}>
      {/* Header Banner */}
      <div style={{ textAlign: "center", marginBottom: "var(--sp-8)" }}>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "var(--sp-2)",
            padding: "4px 12px",
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
          <span>🚀</span> Live AI Mock Interview
        </div>
        <h1 className="dashboard-greeting" style={{ fontSize: "var(--text-3xl)", marginBottom: "var(--sp-2)" }}>
          Configure Your Interview Session
        </h1>
        <p className="dashboard-subtitle" style={{ maxWidth: 560, margin: "0 auto" }}>
          Tailor your mock interview to your target role, difficulty level, and optional resume or job description context before starting.
        </p>
      </div>

      {/* Stepper Progress Bar */}
      <div style={{ marginBottom: "var(--sp-8)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", position: "relative" }}>
          {[
            { step: 1, label: "Role" },
            { step: 2, label: "Interview Type" },
            { step: 3, label: "Context" },
            { step: 4, label: "Difficulty" },
            { step: 5, label: "Pace & Length" },
          ].map((s) => {
            const isActive = currentStep === s.step;
            const isCompleted = currentStep > s.step;

            let circleBg = "var(--gray-100)";
            let circleColor = "var(--gray-500)";
            let circleShadow = "none";

            if (isCompleted) {
              circleBg = "var(--brand-500)";
              circleColor = "#ffffff";
            } else if (isActive) {
              circleBg = "var(--brand-600)";
              circleColor = "#ffffff";
              circleShadow = "0 0 0 4px var(--brand-100)";
            }

            return (
              <button
                key={s.step}
                type="button"
                onClick={() => setCurrentStep(s.step)}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "var(--sp-1)",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  padding: 0,
                }}
              >
                <div
                  style={{
                    width: 38,
                    height: 38,
                    borderRadius: "var(--r-full)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontWeight: 700,
                    fontSize: "var(--text-sm)",
                    background: circleBg,
                    color: circleColor,
                    boxShadow: circleShadow,
                    transition: "all var(--dur-fast, 150ms) var(--ease)",
                  }}
                >
                  {isCompleted ? "✓" : s.step}
                </div>
                <span
                  style={{
                    fontSize: "var(--text-xs)",
                    fontWeight: isActive ? 700 : 500,
                    color: isActive ? "var(--brand-600)" : "var(--gray-500)",
                  }}
                >
                  {s.label}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {error && (
        <div className="alert alert-error" role="alert" style={{ marginBottom: "var(--sp-6)" }}>
          <span>⚠️</span>
          <div>{error}</div>
        </div>
      )}

      {/* Success Created State */}
      {createdInterview ? (
        <div className="panel" style={{ padding: "var(--sp-8)", textAlign: "center", maxWidth: 560, margin: "0 auto" }}>
          <div
            style={{
              width: 56,
              height: 56,
              background: "var(--success-bg)",
              color: "var(--success-text)",
              borderRadius: "var(--r-full)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "var(--text-2xl)",
              margin: "0 auto var(--sp-4)",
            }}
          >
            ✨
          </div>
          <h2 style={{ fontSize: "var(--text-2xl)", fontWeight: 800, color: "var(--gray-900)", marginBottom: "var(--sp-2)" }}>
            Interview Session Created!
          </h2>
          <p style={{ fontSize: "var(--text-sm)", color: "var(--gray-600)", marginBottom: "var(--sp-6)" }}>
            Session <strong>#{createdInterview.id}</strong> has been configured and saved in PostgreSQL with status{" "}
            <span className="badge badge-blue">{createdInterview.status}</span>.
          </p>

          <div
            style={{
              background: "var(--gray-50)",
              borderRadius: "var(--r-xl)",
              padding: "var(--sp-5)",
              textAlign: "left",
              marginBottom: "var(--sp-6)",
              border: "1px solid var(--border)",
              display: "flex",
              flexDirection: "column",
              gap: "var(--sp-3)",
              fontSize: "var(--text-sm)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border)", paddingBottom: "var(--sp-2)" }}>
              <span style={{ color: "var(--gray-500)" }}>Target Role:</span>
              <strong style={{ color: "var(--gray-900)" }}>{createdInterview.role}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border)", paddingBottom: "var(--sp-2)" }}>
              <span style={{ color: "var(--gray-500)" }}>Interview Type:</span>
              <strong style={{ color: "var(--gray-900)", textTransform: "capitalize" }}>{createdInterview.interview_type}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border)", paddingBottom: "var(--sp-2)" }}>
              <span style={{ color: "var(--gray-500)" }}>Difficulty Strategy:</span>
              <strong style={{ color: "var(--gray-900)", textTransform: "capitalize" }}>{createdInterview.difficulty_mode}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border)", paddingBottom: "var(--sp-2)" }}>
              <span style={{ color: "var(--gray-500)" }}>Planned Duration:</span>
              <strong style={{ color: "var(--gray-900)" }}>{createdInterview.duration_minutes} minutes</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--gray-500)" }}>Question Count:</span>
              <strong style={{ color: "var(--gray-900)" }}>{createdInterview.question_count} Questions</strong>
            </div>
          </div>

          <div style={{ display: "flex", gap: "var(--sp-3)", justifyContent: "center" }}>
            <button
              type="button"
              className="btn btn-outline"
              onClick={() => setCreatedInterview(null)}
            >
              ⚙️ Modify Configuration
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => {
                if (onInterviewCreated) {
                  onInterviewCreated(createdInterview);
                }
              }}
            >
              🎯 Begin Mock Interview
            </button>
          </div>
        </div>
      ) : (
        <div className="panel" style={{ padding: "var(--sp-8)" }}>
          {/* STEP 1: Target Role */}
          {currentStep === 1 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--sp-6)" }}>
              <div>
                <h2 style={{ fontSize: "var(--text-xl)", fontWeight: 800, color: "var(--gray-900)", marginBottom: "var(--sp-1)" }}>
                  Step 1: Select Your Target Job Role
                </h2>
                <p style={{ fontSize: "var(--text-sm)", color: "var(--gray-500)" }}>
                  Choose a preset role or enter a custom job title so Gemini tailors relevant questions.
                </p>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "var(--sp-3)" }}>
                {PRESET_ROLES.map((role) => {
                  const isSelected = selectedRole === role;
                  return (
                    <button
                      key={role}
                      type="button"
                      onClick={() => setSelectedRole(role)}
                      style={{
                        padding: "var(--sp-4)",
                        borderRadius: "var(--r-xl)",
                        textAlign: "left",
                        border: isSelected ? "2px solid var(--brand-500)" : "1px solid var(--border)",
                        background: isSelected ? "var(--brand-50)" : "var(--surface)",
                        color: isSelected ? "var(--brand-900)" : "var(--gray-700)",
                        fontWeight: isSelected ? 700 : 500,
                        fontSize: "var(--text-sm)",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        transition: "all var(--dur-fast, 150ms) var(--ease)",
                      }}
                    >
                      <span>{role}</span>
                      {isSelected && <span style={{ color: "var(--brand-600)", fontWeight: 800 }}>✓</span>}
                    </button>
                  );
                })}
              </div>

              {/* Custom Role Input */}
              <div style={{ paddingTop: "var(--sp-2)" }}>
                <label className="control-label" style={{ marginBottom: "var(--sp-2)", display: "block" }}>
                  Or enter a Custom Role Title:
                </label>
                <input
                  type="text"
                  className="control-input"
                  style={{ width: "100%" }}
                  placeholder="e.g. Lead Distributed Systems Architect, iOS Tech Lead"
                  value={customRole}
                  onChange={(e) => {
                    setCustomRole(e.target.value);
                    if (e.target.value.trim()) {
                      setSelectedRole("Custom");
                    }
                  }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", paddingTop: "var(--sp-4)" }}>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setCurrentStep(2)}
                >
                  Next: Interview Type →
                </button>
              </div>
            </div>
          )}

          {/* STEP 2: Interview Type */}
          {currentStep === 2 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--sp-6)" }}>
              <div>
                <h2 style={{ fontSize: "var(--text-xl)", fontWeight: 800, color: "var(--gray-900)", marginBottom: "var(--sp-1)" }}>
                  Step 2: Choose Interview Format
                </h2>
                <p style={{ fontSize: "var(--text-sm)", color: "var(--gray-500)" }}>
                  Select the style of interview you want to simulate.
                </p>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "var(--sp-4)" }}>
                {INTERVIEW_TYPES.map((t) => {
                  const isSelected = interviewType === t.id;
                  return (
                    <div
                      key={t.id}
                      onClick={() => setInterviewType(t.id)}
                      style={{
                        padding: "var(--sp-5)",
                        borderRadius: "var(--r-xl)",
                        border: isSelected ? "2px solid var(--brand-500)" : "1px solid var(--border)",
                        background: isSelected ? "var(--brand-50)" : "var(--surface)",
                        cursor: "pointer",
                        transition: "all var(--dur-fast, 150ms) var(--ease)",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--sp-2)" }}>
                        <span style={{ fontSize: "var(--text-2xl)" }}>{t.icon}</span>
                        {isSelected && <span className="badge badge-blue">Selected</span>}
                      </div>
                      <h3 style={{ fontWeight: 700, color: "var(--gray-900)", fontSize: "var(--text-base)", marginBottom: "var(--sp-1)" }}>
                        {t.title}
                      </h3>
                      <p style={{ color: "var(--gray-500)", fontSize: "var(--text-xs)", lineHeight: 1.5 }}>
                        {t.description}
                      </p>
                    </div>
                  );
                })}
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", paddingTop: "var(--sp-4)" }}>
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => setCurrentStep(1)}
                >
                  ← Back
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setCurrentStep(3)}
                >
                  Next: Attach Context →
                </button>
              </div>
            </div>
          )}

          {/* STEP 3: Context Attachment */}
          {currentStep === 3 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--sp-6)" }}>
              <div>
                <h2 style={{ fontSize: "var(--text-xl)", fontWeight: 800, color: "var(--gray-900)", marginBottom: "var(--sp-1)" }}>
                  Step 3: Attach Candidate Context (Optional)
                </h2>
                <p style={{ fontSize: "var(--text-sm)", color: "var(--gray-500)" }}>
                  Provide an uploaded resume or a specific job description so questions target your actual experience gaps.
                </p>
              </div>

              {/* Context Selector Tabs */}
              <div style={{ display: "flex", borderBottom: "1px solid var(--border)", gap: "var(--sp-6)" }}>
                {[
                  { id: "none", label: "No Context (General Role)" },
                  { id: "resume", label: `Uploaded Resume (${resumes.length})` },
                  { id: "jd", label: `Job Description (${jobDescriptions.length})` },
                ].map((tab) => {
                  const isActive = contextTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      type="button"
                      onClick={() => setContextTab(tab.id as "none" | "resume" | "jd")}
                      style={{
                        padding: "var(--sp-3) 0",
                        fontSize: "var(--text-sm)",
                        fontWeight: isActive ? 700 : 500,
                        color: isActive ? "var(--brand-600)" : "var(--gray-500)",
                        borderBottom: isActive ? "2px solid var(--brand-500)" : "2px solid transparent",
                        background: "none",
                        borderTop: "none",
                        borderLeft: "none",
                        borderRight: "none",
                        cursor: "pointer",
                      }}
                    >
                      {tab.label}
                    </button>
                  );
                })}
              </div>

              {/* Tab 1: None */}
              {contextTab === "none" && (
                <div style={{ padding: "var(--sp-5)", background: "var(--gray-50)", borderRadius: "var(--r-xl)", color: "var(--gray-600)", fontSize: "var(--text-sm)", border: "1px solid var(--border)" }}>
                  <span>ℹ️</span> The AI will generate standard industry mock interview questions tailored to{" "}
                  <strong style={{ color: "var(--gray-900)" }}>&quot;{getEffectiveRole()}&quot;</strong>.
                </div>
              )}

              {/* Tab 2: Resume Selection */}
              {contextTab === "resume" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "var(--sp-4)" }}>
                  {resumes.length === 0 ? (
                    <div className="alert alert-warning">
                      <span>⚠️</span> No resumes uploaded yet. Go to the <strong>Resume Audit</strong> tab to upload your resume PDF/DOCX.
                    </div>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: "var(--sp-2)" }}>
                      <label className="control-label">Select Resume:</label>
                      {resumes.map((r) => {
                        const isSelected = selectedResumeId === r.id;
                        return (
                          <div
                            key={r.id}
                            onClick={() => setSelectedResumeId(r.id)}
                            style={{
                              padding: "var(--sp-4)",
                              borderRadius: "var(--r-xl)",
                              border: isSelected ? "2px solid var(--brand-500)" : "1px solid var(--border)",
                              background: isSelected ? "var(--brand-50)" : "var(--surface)",
                              cursor: "pointer",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                            }}
                          >
                            <div>
                              <div style={{ fontWeight: 600, color: "var(--gray-900)", fontSize: "var(--text-sm)" }}>
                                {r.file_url ? r.file_url.split(/[/\\]/).pop() : `Resume #${r.id}`}
                              </div>
                              <div style={{ fontSize: "var(--text-xs)", color: "var(--gray-500)" }}>
                                Audit Score: {r.audit_score ? `${Math.round(r.audit_score)}/100` : "N/A"} • Uploaded {new Date(r.created_at).toLocaleDateString()}
                              </div>
                            </div>
                            {isSelected && <span style={{ color: "var(--brand-600)", fontWeight: 800 }}>✓</span>}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* Tab 3: Job Description */}
              {contextTab === "jd" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "var(--sp-4)" }}>
                  {jobDescriptions.length > 0 && (
                    <div style={{ display: "flex", flexDirection: "column", gap: "var(--sp-2)", marginBottom: "var(--sp-4)" }}>
                      <label className="control-label">Select Saved Job Description:</label>
                      {jobDescriptions.map((jd) => {
                        const title = jd.parsed_required_skills_json?.role_title || `Job Description #${jd.id}`;
                        const skills = jd.parsed_required_skills_json?.required_skills || [];
                        const isSelected = selectedJdId === jd.id;
                        return (
                          <div
                            key={jd.id}
                            onClick={() => setSelectedJdId(jd.id)}
                            style={{
                              padding: "var(--sp-4)",
                              borderRadius: "var(--r-xl)",
                              border: isSelected ? "2px solid var(--brand-500)" : "1px solid var(--border)",
                              background: isSelected ? "var(--brand-50)" : "var(--surface)",
                              cursor: "pointer",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                            }}
                          >
                            <div>
                              <div style={{ fontWeight: 600, color: "var(--gray-900)", fontSize: "var(--text-sm)" }}>{title}</div>
                              <div style={{ fontSize: "var(--text-xs)", color: "var(--gray-500)" }} className="truncate">
                                Skills: {skills.length > 0 ? skills.slice(0, 5).join(", ") : jd.raw_text.slice(0, 60)}
                              </div>
                            </div>
                            {isSelected && <span style={{ color: "var(--brand-600)", fontWeight: 800 }}>✓</span>}
                          </div>
                        );
                      })}
                    </div>
                  )}

                  <div style={{ paddingTop: "var(--sp-3)", borderTop: "1px solid var(--border)" }}>
                    <label className="control-label" style={{ marginBottom: "var(--sp-2)", display: "block" }}>
                      Or Paste New Job Description Text:
                    </label>
                    <textarea
                      className="control-input"
                      style={{ width: "100%", minHeight: 100, fontSize: "var(--text-sm)", padding: "var(--sp-3)" }}
                      placeholder="Paste target job description text here..."
                      value={pastedJdText}
                      onChange={(e) => setPastedJdText(e.target.value)}
                    />
                    <button
                      type="button"
                      className="btn btn-outline btn-sm"
                      style={{ marginTop: "var(--sp-2)" }}
                      onClick={handleSavePastedJd}
                      disabled={savingJd || !pastedJdText.trim()}
                    >
                      {savingJd ? "Parsing Skills with Gemini..." : "Parse & Save JD"}
                    </button>
                  </div>
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "space-between", paddingTop: "var(--sp-4)" }}>
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => setCurrentStep(2)}
                >
                  ← Back
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setCurrentStep(4)}
                >
                  Next: Difficulty Strategy →
                </button>
              </div>
            </div>
          )}

          {/* STEP 4: Difficulty Strategy */}
          {currentStep === 4 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--sp-6)" }}>
              <div>
                <h2 style={{ fontSize: "var(--text-xl)", fontWeight: 800, color: "var(--gray-900)", marginBottom: "var(--sp-1)" }}>
                  Step 4: Select Difficulty Strategy
                </h2>
                <p style={{ fontSize: "var(--text-sm)", color: "var(--gray-500)" }}>
                  Choose a fixed difficulty level or opt for Adaptive AI scaling.
                </p>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "var(--sp-4)" }}>
                {DIFFICULTY_MODES.map((d) => {
                  const isSelected = difficultyMode === d.id;
                  return (
                    <div
                      key={d.id}
                      onClick={() => setDifficultyMode(d.id)}
                      style={{
                        padding: "var(--sp-5)",
                        borderRadius: "var(--r-xl)",
                        border: isSelected ? "2px solid var(--brand-500)" : "1px solid var(--border)",
                        background: isSelected ? "var(--brand-50)" : "var(--surface)",
                        cursor: "pointer",
                        transition: "all var(--dur-fast, 150ms) var(--ease)",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--sp-2)" }}>
                        <span style={{ fontSize: "var(--text-2xl)" }}>{d.icon}</span>
                        <span className={`badge ${d.badgeClass}`}>{d.title}</span>
                      </div>
                      <h3 style={{ fontWeight: 700, color: "var(--gray-900)", fontSize: "var(--text-base)", marginBottom: "var(--sp-1)" }}>
                        {d.title} Mode
                      </h3>
                      <p style={{ color: "var(--gray-500)", fontSize: "var(--text-xs)", lineHeight: 1.5 }}>
                        {d.description}
                      </p>
                    </div>
                  );
                })}
              </div>

              {/* Informational Callout for Adaptive Mode */}
              {difficultyMode === "Adaptive" && (
                <div style={{ padding: "var(--sp-4)", background: "var(--warning-bg)", border: "1px solid var(--warning-border)", color: "var(--warning-text)", borderRadius: "var(--r-xl)", fontSize: "var(--text-xs)" }}>
                  <div style={{ fontWeight: 700, fontSize: "var(--text-sm)", marginBottom: "var(--sp-1)" }}>
                    🧠 Adaptive AI Mode Active
                  </div>
                  <div>
                    The system starts your session at <strong>Medium</strong> difficulty. If you provide thorough, high-scoring answers, the AI automatically escalates to <strong>Hard</strong> questions. If an answer lacks key concepts, it adjusts back to <strong>Medium/Easy</strong> to test core fundamentals.
                  </div>
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "space-between", paddingTop: "var(--sp-4)" }}>
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => setCurrentStep(3)}
                >
                  ← Back
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setCurrentStep(5)}
                >
                  Next: Session Length →
                </button>
              </div>
            </div>
          )}

          {/* STEP 5: Pace & Length */}
          {currentStep === 5 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--sp-6)" }}>
              <div>
                <h2 style={{ fontSize: "var(--text-xl)", fontWeight: 800, color: "var(--gray-900)", marginBottom: "var(--sp-1)" }}>
                  Step 5: Session Duration &amp; Question Count
                </h2>
                <p style={{ fontSize: "var(--text-sm)", color: "var(--gray-500)" }}>
                  Configure how long your mock session will run and how many questions to attempt.
                </p>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "var(--sp-6)" }}>
                {/* Duration */}
                <div>
                  <label className="control-label" style={{ marginBottom: "var(--sp-2)", display: "block" }}>
                    Planned Session Duration:
                  </label>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))", gap: "var(--sp-3)" }}>
                    {DURATION_OPTIONS.map((mins) => {
                      const isSelected = durationMinutes === mins;
                      return (
                        <button
                          key={mins}
                          type="button"
                          onClick={() => setDurationMinutes(mins)}
                          style={{
                            padding: "var(--sp-3)",
                            borderRadius: "var(--r-xl)",
                            fontWeight: 600,
                            fontSize: "var(--text-sm)",
                            border: isSelected ? "1px solid var(--brand-600)" : "1px solid var(--border)",
                            background: isSelected ? "var(--brand-600)" : "var(--surface)",
                            color: isSelected ? "#ffffff" : "var(--gray-700)",
                            cursor: "pointer",
                            transition: "all var(--dur-fast, 150ms) var(--ease)",
                          }}
                        >
                          ⏱️ {mins} mins
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Question Count */}
                <div>
                  <label className="control-label" style={{ marginBottom: "var(--sp-2)", display: "block" }}>
                    Number of Questions:
                  </label>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))", gap: "var(--sp-3)" }}>
                    {QUESTION_COUNT_OPTIONS.map((cnt) => {
                      const isSelected = questionCount === cnt;
                      return (
                        <button
                          key={cnt}
                          type="button"
                          onClick={() => setQuestionCount(cnt)}
                          style={{
                            padding: "var(--sp-3)",
                            borderRadius: "var(--r-xl)",
                            fontWeight: 600,
                            fontSize: "var(--text-sm)",
                            border: isSelected ? "1px solid var(--brand-600)" : "1px solid var(--border)",
                            background: isSelected ? "var(--brand-600)" : "var(--surface)",
                            color: isSelected ? "#ffffff" : "var(--gray-700)",
                            cursor: "pointer",
                            transition: "all var(--dur-fast, 150ms) var(--ease)",
                          }}
                        >
                          ❓ {cnt} Questions
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Final Configuration Review Summary */}
                <div style={{ background: "var(--gray-50)", borderRadius: "var(--r-2xl)", padding: "var(--sp-5)", border: "1px solid var(--border)", display: "flex", flexDirection: "column", gap: "var(--sp-3)" }}>
                  <h3 style={{ fontSize: "var(--text-xs)", fontWeight: 700, color: "var(--gray-400)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                    Session Configuration Summary
                  </h3>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "var(--sp-3)", fontSize: "var(--text-sm)" }}>
                    <div>
                      <div style={{ fontSize: "var(--text-xs)", color: "var(--gray-500)" }}>Target Role</div>
                      <strong style={{ color: "var(--gray-900)" }}>{getEffectiveRole()}</strong>
                    </div>
                    <div>
                      <div style={{ fontSize: "var(--text-xs)", color: "var(--gray-500)" }}>Interview Type</div>
                      <strong style={{ color: "var(--gray-900)" }}>{interviewType}</strong>
                    </div>
                    <div>
                      <div style={{ fontSize: "var(--text-xs)", color: "var(--gray-500)" }}>Difficulty Mode</div>
                      <strong style={{ color: "var(--gray-900)" }}>{difficultyMode}</strong>
                    </div>
                    <div>
                      <div style={{ fontSize: "var(--text-xs)", color: "var(--gray-500)" }}>Length</div>
                      <strong style={{ color: "var(--gray-900)" }}>{durationMinutes}m ({questionCount} Qs)</strong>
                    </div>
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", paddingTop: "var(--sp-4)" }}>
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => setCurrentStep(4)}
                >
                  ← Back
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  style={{ padding: "var(--sp-3) var(--sp-8)", fontSize: "var(--text-base)" }}
                  onClick={handleSubmit}
                  disabled={submitting}
                >
                  {submitting ? "Saving Configuration..." : "🚀 Save Interview Configuration"}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
