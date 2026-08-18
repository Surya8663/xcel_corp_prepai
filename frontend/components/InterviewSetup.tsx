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
    badgeClass: "badge-purple",
    description: "Complex distributed systems, performance bottleneck analysis, and deep architectural questions.",
  },
  {
    id: "Adaptive",
    title: "Adaptive AI",
    icon: "🧠",
    badgeClass: "badge-orange",
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
    <div className="interview-setup-container max-w-5xl mx-auto p-6">
      {/* Header Banner */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-semibold uppercase tracking-wider mb-2">
          <span>🚀</span> Live AI Mock Interview
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Configure Your Interview Session</h1>
        <p className="text-gray-600 max-w-2xl mx-auto">
          Tailor your mock interview to your target role, difficulty level, and optional resume or job description context before starting.
        </p>
      </div>

      {/* Stepper Progress Bar */}
      <div className="stepper-header mb-8">
        <div className="flex justify-between items-center relative z-10">
          {[
            { step: 1, label: "Role" },
            { step: 2, label: "Interview Type" },
            { step: 3, label: "Context" },
            { step: 4, label: "Difficulty" },
            { step: 5, label: "Pace & Length" },
          ].map((s) => {
            const isActive = currentStep === s.step;
            const isCompleted = currentStep > s.step;
            return (
              <button
                key={s.step}
                type="button"
                onClick={() => setCurrentStep(s.step)}
                className={`step-item flex flex-col items-center gap-1 group focus:outline-none`}
              >
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-all ${
                    isCompleted
                      ? "bg-blue-600 text-white shadow-sm"
                      : isActive
                      ? "bg-blue-600 text-white ring-4 ring-blue-100 shadow-md"
                      : "bg-gray-100 text-gray-500 group-hover:bg-gray-200"
                  }`}
                >
                  {isCompleted ? "✓" : s.step}
                </div>
                <span
                  className={`text-xs font-medium ${
                    isActive ? "text-blue-600 font-bold" : "text-gray-500"
                  }`}
                >
                  {s.label}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {error && (
        <div className="error-banner mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl flex items-center gap-3">
          <span className="text-xl">⚠️</span>
          <div className="text-sm font-medium">{error}</div>
        </div>
      )}

      {/* Success Created State */}
      {createdInterview ? (
        <div className="panel p-8 text-center bg-white rounded-2xl border border-gray-200 shadow-xl max-w-xl mx-auto">
          <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center text-3xl mx-auto mb-4">
            ✨
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Interview Session Created!</h2>
          <p className="text-gray-600 text-sm mb-6">
            Session <strong className="text-gray-900">#{createdInterview.id}</strong> has been configured and saved in PostgreSQL with status{" "}
            <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs font-semibold rounded-full uppercase">
              {createdInterview.status}
            </span>.
          </p>

          <div className="bg-gray-50 rounded-xl p-4 text-left mb-6 space-y-2 text-sm border border-gray-100">
            <div className="flex justify-between border-b pb-2">
              <span className="text-gray-500">Target Role:</span>
              <span className="font-semibold text-gray-900">{createdInterview.role}</span>
            </div>
            <div className="flex justify-between border-b pb-2">
              <span className="text-gray-500">Interview Type:</span>
              <span className="font-semibold text-gray-900 capitalize">{createdInterview.interview_type}</span>
            </div>
            <div className="flex justify-between border-b pb-2">
              <span className="text-gray-500">Difficulty Strategy:</span>
              <span className="font-semibold text-gray-900 capitalize">{createdInterview.difficulty_mode}</span>
            </div>
            <div className="flex justify-between border-b pb-2">
              <span className="text-gray-500">Planned Duration:</span>
              <span className="font-semibold text-gray-900">{createdInterview.duration_minutes} minutes</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Question Count:</span>
              <span className="font-semibold text-gray-900">{createdInterview.question_count} Questions</span>
            </div>
          </div>

          <div className="flex gap-3 justify-center">
            <button
              className="btn btn-outline"
              onClick={() => setCreatedInterview(null)}
            >
              ⚙️ Modify Configuration
            </button>
            <button
              className="btn btn-primary px-6"
              onClick={() => alert(`Starting Live Mock Session #${createdInterview.id}... (Phase 7 feature)`)}
            >
              🎯 Begin Mock Interview
            </button>
          </div>
        </div>
      ) : (
        <div className="setup-card bg-white rounded-2xl border border-gray-200 shadow-sm p-8">
          {/* STEP 1: Target Role */}
          {currentStep === 1 && (
            <div className="step-content space-y-6">
              <div>
                <h2 className="text-xl font-bold text-gray-900 mb-1">Step 1: Select Your Target Job Role</h2>
                <p className="text-gray-500 text-sm">
                  Choose a preset role or enter a custom job title so Gemini tailors relevant questions.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {PRESET_ROLES.map((role) => {
                  const isSelected = selectedRole === role;
                  return (
                    <button
                      key={role}
                      type="button"
                      className={`p-4 rounded-xl text-left border transition-all flex items-center justify-between ${
                        isSelected
                          ? "border-blue-600 bg-blue-50/50 text-blue-900 ring-2 ring-blue-500/20 font-semibold"
                          : "border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50"
                      }`}
                      onClick={() => {
                        setSelectedRole(role);
                      }}
                    >
                      <span>{role}</span>
                      {isSelected && <span className="text-blue-600 font-bold">✓</span>}
                    </button>
                  );
                })}
              </div>

              {/* Custom Role Input */}
              <div className="pt-2">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Or enter a Custom Role Title:
                </label>
                <input
                  type="text"
                  className="control-input w-full"
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

              <div className="flex justify-end pt-4">
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
            <div className="step-content space-y-6">
              <div>
                <h2 className="text-xl font-bold text-gray-900 mb-1">Step 2: Choose Interview Format</h2>
                <p className="text-gray-500 text-sm">
                  Select the style of interview you want to simulate.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {INTERVIEW_TYPES.map((t) => {
                  const isSelected = interviewType === t.id;
                  return (
                    <div
                      key={t.id}
                      onClick={() => setInterviewType(t.id)}
                      className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                        isSelected
                          ? "border-blue-600 bg-blue-50/60 ring-2 ring-blue-500/20 shadow-sm"
                          : "border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-2xl">{t.icon}</span>
                        {isSelected && (
                          <span className="px-2.5 py-0.5 bg-blue-600 text-white rounded-full text-xs font-bold">
                            Selected
                          </span>
                        )}
                      </div>
                      <h3 className="font-bold text-gray-900 text-base mb-1">{t.title}</h3>
                      <p className="text-gray-500 text-xs leading-relaxed">{t.description}</p>
                    </div>
                  );
                })}
              </div>

              <div className="flex justify-between pt-4">
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
            <div className="step-content space-y-6">
              <div>
                <h2 className="text-xl font-bold text-gray-900 mb-1">Step 3: Attach Candidate Context (Optional)</h2>
                <p className="text-gray-500 text-sm">
                  Provide an uploaded resume or a specific job description so questions target your actual experience gaps.
                </p>
              </div>

              {/* Context Selector Tabs */}
              <div className="flex border-b border-gray-200 space-x-6">
                {[
                  { id: "none", label: "No Context (General Role)" },
                  { id: "resume", label: `Uploaded Resume (${resumes.length})` },
                  { id: "jd", label: `Job Description (${jobDescriptions.length})` },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    type="button"
                    className={`py-3 text-sm font-medium border-b-2 transition-all ${
                      contextTab === tab.id
                        ? "border-blue-600 text-blue-600 font-semibold"
                        : "border-transparent text-gray-500 hover:text-gray-700"
                    }`}
                    onClick={() => setContextTab(tab.id as "none" | "resume" | "jd")}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Tab 1: None */}
              {contextTab === "none" && (
                <div className="p-6 bg-gray-50 rounded-xl text-center text-gray-600 text-sm border border-gray-100">
                  <span>ℹ️</span> The AI will generate standard industry mock interview questions tailored to{" "}
                  <strong className="text-gray-900">"{getEffectiveRole()}"</strong>.
                </div>
              )}

              {/* Tab 2: Resume Selection */}
              {contextTab === "resume" && (
                <div className="space-y-4">
                  {resumes.length === 0 ? (
                    <div className="p-6 bg-amber-50 border border-amber-200 text-amber-800 rounded-xl text-sm">
                      ⚠️ No resumes uploaded yet. Go to the <strong>Resume Audit</strong> tab to upload your resume PDF/DOCX.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <label className="block text-sm font-medium text-gray-700">Select Resume:</label>
                      {resumes.map((r) => (
                        <div
                          key={r.id}
                          onClick={() => setSelectedResumeId(r.id)}
                          className={`p-4 rounded-xl border cursor-pointer flex items-center justify-between ${
                            selectedResumeId === r.id
                              ? "border-blue-600 bg-blue-50/60 ring-2 ring-blue-500/20"
                              : "border-gray-200 bg-white hover:bg-gray-50"
                          }`}
                        >
                          <div>
                            <div className="font-semibold text-gray-900 text-sm">
                              {r.file_url ? r.file_url.split(/[/\\]/).pop() : `Resume #${r.id}`}
                            </div>
                            <div className="text-xs text-gray-500">
                              Audit Score: {r.audit_score ? `${Math.round(r.audit_score)}/100` : "N/A"} • Uploaded {new Date(r.created_at).toLocaleDateString()}
                            </div>
                          </div>
                          {selectedResumeId === r.id && <span className="text-blue-600 font-bold">✓</span>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tab 3: Job Description */}
              {contextTab === "jd" && (
                <div className="space-y-4">
                  {jobDescriptions.length > 0 && (
                    <div className="space-y-2 mb-4">
                      <label className="block text-sm font-medium text-gray-700">Select Saved Job Description:</label>
                      {jobDescriptions.map((jd) => {
                        const title = jd.parsed_required_skills_json?.role_title || `Job Description #${jd.id}`;
                        const skills = jd.parsed_required_skills_json?.required_skills || [];
                        return (
                          <div
                            key={jd.id}
                            onClick={() => setSelectedJdId(jd.id)}
                            className={`p-4 rounded-xl border cursor-pointer flex items-center justify-between ${
                              selectedJdId === jd.id
                                ? "border-blue-600 bg-blue-50/60 ring-2 ring-blue-500/20"
                                : "border-gray-200 bg-white hover:bg-gray-50"
                            }`}
                          >
                            <div>
                              <div className="font-semibold text-gray-900 text-sm">{title}</div>
                              <div className="text-xs text-gray-500 line-clamp-1">
                                Skills: {skills.length > 0 ? skills.slice(0, 5).join(", ") : jd.raw_text.slice(0, 60)}
                              </div>
                            </div>
                            {selectedJdId === jd.id && <span className="text-blue-600 font-bold">✓</span>}
                          </div>
                        );
                      })}
                    </div>
                  )}

                  <div className="pt-2 border-t">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Or Paste New Job Description Text:
                    </label>
                    <textarea
                      className="control-input w-full min-h-[100px] text-sm p-3"
                      placeholder="Paste target job description text here..."
                      value={pastedJdText}
                      onChange={(e) => setPastedJdText(e.target.value)}
                    />
                    <button
                      type="button"
                      className="btn btn-outline btn-sm mt-2"
                      onClick={handleSavePastedJd}
                      disabled={savingJd || !pastedJdText.trim()}
                    >
                      {savingJd ? "Parsing Skills with Gemini..." : "Parse & Save JD"}
                    </button>
                  </div>
                </div>
              )}

              <div className="flex justify-between pt-4">
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
            <div className="step-content space-y-6">
              <div>
                <h2 className="text-xl font-bold text-gray-900 mb-1">Step 4: Select Difficulty Strategy</h2>
                <p className="text-gray-500 text-sm">
                  Choose a fixed difficulty level or opt for Adaptive AI scaling.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {DIFFICULTY_MODES.map((d) => {
                  const isSelected = difficultyMode === d.id;
                  return (
                    <div
                      key={d.id}
                      onClick={() => setDifficultyMode(d.id)}
                      className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                        isSelected
                          ? "border-blue-600 bg-blue-50/60 ring-2 ring-blue-500/20 shadow-sm"
                          : "border-gray-200 bg-white hover:border-gray-300"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-2xl">{d.icon}</span>
                        <span className={`badge ${d.badgeClass}`}>{d.title}</span>
                      </div>
                      <h3 className="font-bold text-gray-900 text-base mb-1">{d.title} Mode</h3>
                      <p className="text-gray-500 text-xs leading-relaxed">{d.description}</p>
                    </div>
                  );
                })}
              </div>

              {/* Informational Callout for Adaptive Mode */}
              {difficultyMode === "Adaptive" && (
                <div className="p-4 bg-orange-50 border border-orange-200 text-orange-900 rounded-xl text-xs space-y-1">
                  <div className="font-bold text-sm flex items-center gap-1.5">
                    <span>🧠</span> Adaptive AI Mode Active
                  </div>
                  <div>
                    The system starts your session at <strong>Medium</strong> difficulty. If you provide thorough, high-scoring answers, the AI automatically escalates to <strong>Hard</strong> questions. If an answer lacks key concepts, it adjusts back to <strong>Medium/Easy</strong> to test core fundamentals.
                  </div>
                </div>
              )}

              <div className="flex justify-between pt-4">
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
            <div className="step-content space-y-6">
              <div>
                <h2 className="text-xl font-bold text-gray-900 mb-1">Step 5: Session Duration & Question Count</h2>
                <p className="text-gray-500 text-sm">
                  Configure how long your mock session will run and how many questions to attempt.
                </p>
              </div>

              <div className="space-y-6">
                {/* Duration */}
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Planned Session Duration:
                  </label>
                  <div className="grid grid-cols-4 gap-3">
                    {DURATION_OPTIONS.map((mins) => (
                      <button
                        key={mins}
                        type="button"
                        className={`py-3 rounded-xl font-semibold text-sm border transition-all ${
                          durationMinutes === mins
                            ? "border-blue-600 bg-blue-600 text-white shadow-sm"
                            : "border-gray-200 bg-white text-gray-700 hover:border-gray-300"
                        }`}
                        onClick={() => setDurationMinutes(mins)}
                      >
                        ⏱️ {mins} mins
                      </button>
                    ))}
                  </div>
                </div>

                {/* Question Count */}
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">
                    Number of Questions:
                  </label>
                  <div className="grid grid-cols-4 gap-3">
                    {QUESTION_COUNT_OPTIONS.map((cnt) => (
                      <button
                        key={cnt}
                        type="button"
                        className={`py-3 rounded-xl font-semibold text-sm border transition-all ${
                          questionCount === cnt
                            ? "border-blue-600 bg-blue-600 text-white shadow-sm"
                            : "border-gray-200 bg-white text-gray-700 hover:border-gray-300"
                        }`}
                        onClick={() => setQuestionCount(cnt)}
                      >
                        ❓ {cnt} Questions
                      </button>
                    ))}
                  </div>
                </div>

                {/* Final Configuration Review Summary */}
                <div className="bg-gray-50 rounded-2xl p-5 border border-gray-200 space-y-3">
                  <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider">
                    Session Configuration Summary
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                    <div>
                      <div className="text-xs text-gray-500">Target Role</div>
                      <div className="font-semibold text-gray-900">{getEffectiveRole()}</div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-500">Interview Type</div>
                      <div className="font-semibold text-gray-900">{interviewType}</div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-500">Difficulty Mode</div>
                      <div className="font-semibold text-gray-900">{difficultyMode}</div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-500">Length</div>
                      <div className="font-semibold text-gray-900">{durationMinutes}m ({questionCount} Qs)</div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex justify-between pt-4">
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => setCurrentStep(4)}
                >
                  ← Back
                </button>
                <button
                  type="button"
                  className="btn btn-primary px-8 text-base py-3 shadow-md hover:shadow-lg"
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
