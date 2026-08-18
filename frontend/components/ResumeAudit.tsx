"use client";

import { useState, useRef, useEffect, ChangeEvent, DragEvent } from "react";
import { uploadResume, getResume, listResumes, type ResumeRecord } from "@/lib/api";

export default function ResumeAuditComponent() {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ResumeRecord | null>(null);
  const [activeSubTab, setActiveSubTab] = useState<"audit" | "extracted">("audit");

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    async function loadLatestResume() {
      try {
        const list = await listResumes();
        if (list && list.length > 0) {
          const latestId = list[0].id;
          const full = await getResume(latestId);
          setResult(full);
        }
      } catch {
        // Silently ignore if no backend connection yet
      }
    }
    loadLatestResume();
  }, []);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];
      validateAndProcess(droppedFile);
    }
  };

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndProcess(e.target.files[0]);
    }
  };

  const validateAndProcess = (selectedFile: File) => {
    const ext = selectedFile.name.split(".").pop()?.toLowerCase();
    if (ext !== "pdf" && ext !== "docx" && ext !== "doc") {
      setError("Please upload a PDF or DOCX file.");
      return;
    }
    if (selectedFile.size > 10 * 1024 * 1024) {
      setError("File size exceeds 10MB limit.");
      return;
    }
    setError(null);
    setFile(selectedFile);
    startAudit(selectedFile);
  };

  const startAudit = async (uploadFile: File) => {
    setIsLoading(true);
    setError(null);
    setLoadingStage("Extracting raw text from document...");

    try {
      const stages = [
        "Extracting text...",
        "Calling Gemini AI to parse skills & experience...",
        "Evaluating audit score and industry readiness...",
      ];
      
      let stageIdx = 0;
      const interval = setInterval(() => {
        stageIdx = (stageIdx + 1) % stages.length;
        setLoadingStage(stages[stageIdx]);
      }, 3500);

      const res = await uploadResume(uploadFile);
      clearInterval(interval);
      setResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "An unexpected error occurred.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setResult(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const audit = result?.audit_feedback_json;
  const parsed = result?.parsed_json;
  const score = Math.round(result?.audit_score ?? audit?.overall_score ?? 0);

  const getScoreColor = (val: number) => {
    if (val >= 85) return "#10b981"; // emerald
    if (val >= 70) return "#3b82f6"; // blue
    if (val >= 55) return "#f59e0b"; // amber
    return "#ef4444"; // red
  };

  const getScoreBadgeClass = (val: number) => {
    if (val >= 85) return "badge-green";
    if (val >= 70) return "badge-blue";
    if (val >= 55) return "badge-amber";
    return "badge-red";
  };

  return (
    <div className="resume-audit-container">
      {/* Header */}
      <div className="dashboard-header">
        <h1 className="dashboard-greeting">
          Resume <span>Audit & Analysis</span>
        </h1>
        <p className="dashboard-subtitle">
          Upload your resume (PDF/DOCX) for deep AI parsing, scannability auditing, and actionable feedback.
        </p>
      </div>

      {/* Upload card (shown if no result and not loading) */}
      {!result && !isLoading && (
        <div className="panel upload-panel">
          <div className="panel-header">
            <span className="panel-title">Upload Resume</span>
            <span className="badge badge-blue">PDF / DOCX</span>
          </div>
          <div className="panel-body">
            <div
              className={`dropzone ${isDragging ? "dragging" : ""}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              role="button"
              tabIndex={0}
              aria-label="Upload resume file dropzone"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.doc"
                className="hidden-file-input"
                onChange={handleFileSelect}
              />
              <div className="dropzone-icon">📄</div>
              <h3 className="dropzone-title">
                Drag &amp; drop your resume here, or <span className="text-brand">browse files</span>
              </h3>
              <p className="dropzone-sub">
                Supports PDF and DOCX files up to 10MB.
              </p>
            </div>

            {error && (
              <div className="error-banner" role="alert">
                <span className="error-icon">⚠️</span>
                <div>
                  <strong>Upload Error:</strong> {error}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="panel loading-panel">
          <div className="panel-body loading-body">
            <div className="spinner" aria-hidden="true" />
            <h3 className="loading-title">Analyzing Resume with Gemini AI</h3>
            <p className="loading-subtitle">{loadingStage}</p>
            <p className="loading-note">
              This usually takes 8–15 seconds while Gemini performs full-text parsing and audit analysis.
            </p>
          </div>
        </div>
      )}

      {/* Error state if upload failed after trial */}
      {error && !isLoading && !result && (
        <div className="text-center mt-4">
          <button className="btn btn-secondary" onClick={handleReset}>
            Try Uploading Again
          </button>
        </div>
      )}

      {/* Results View */}
      {result && audit && (
        <div className="audit-results-space">
          {/* Top action bar */}
          <div className="results-top-bar">
            <div className="results-filename">
              <span className="file-icon">📄</span>
              <span className="file-name">{file?.name || "Uploaded Resume"}</span>
            </div>
            <div className="results-actions">
              <button
                className={`tab-btn ${activeSubTab === "audit" ? "active" : ""}`}
                onClick={() => setActiveSubTab("audit")}
              >
                📊 Audit Analysis
              </button>
              <button
                className={`tab-btn ${activeSubTab === "extracted" ? "active" : ""}`}
                onClick={() => setActiveSubTab("extracted")}
              >
                🔍 Extracted Skills &amp; Data
              </button>
              <button className="btn btn-outline" onClick={handleReset}>
                Audit Another Resume
              </button>
            </div>
          </div>

          {activeSubTab === "audit" && (
            <div className="audit-grid">
              {/* Score & Verdict Card */}
              <div className="panel score-card">
                <div className="panel-header">
                  <span className="panel-title">Resume Compatibility Score</span>
                  <span className={`badge ${getScoreBadgeClass(score)}`}>
                    {audit.industry_level || "Audited"}
                  </span>
                </div>
                <div className="score-card-body">
                  {/* Score Radial Ring */}
                  <div className="score-ring-container">
                    <svg viewBox="0 0 100 100" className="score-ring-svg">
                      <circle
                        cx="50"
                        cy="50"
                        r="42"
                        className="ring-bg"
                      />
                      <circle
                        cx="50"
                        cy="50"
                        r="42"
                        className="ring-progress"
                        stroke={getScoreColor(score)}
                        strokeDasharray={263.89}
                        strokeDashoffset={263.89 - (263.89 * score) / 100}
                      />
                    </svg>
                    <div className="score-number-box">
                      <span className="score-val" style={{ color: getScoreColor(score) }}>
                        {score}
                      </span>
                      <span className="score-max">/100</span>
                    </div>
                  </div>

                  {/* Industry Verdict */}
                  <div className="verdict-box">
                    <h4 className="verdict-title">
                      Industry Level: <span>{audit.industry_level || "Evaluation Complete"}</span>
                    </h4>
                    <p className="verdict-text">
                      {audit.industry_level_justification || audit.overall_verdict}
                    </p>
                  </div>

                  {/* Reasoning snippet */}
                  {audit.scoring_reasoning && (
                    <div className="reasoning-box">
                      <strong>Score Reasoning:</strong> {audit.scoring_reasoning}
                    </div>
                  )}

                  {/* Disclaimer note */}
                  <div className="disclaimer-note">
                    ℹ️ <strong>Note on Scoring:</strong> No universal official ATS algorithm exists publicly. This score evaluates clarity, structural formatting, keyword strength, quantified impact, and scannability based on modern engineering recruitment standards.
                  </div>
                </div>
              </div>

              {/* What's Good & What Needs Improvement Columns */}
              <div className="audit-details-col">
                {/* What's Good */}
                <div className="panel good-panel">
                  <div className="panel-header">
                    <span className="panel-title">✅ What&apos;s Working Well</span>
                    <span className="badge badge-green">Strengths</span>
                  </div>
                  <div className="panel-body">
                    {audit.whats_good && audit.whats_good.length > 0 ? (
                      <ul className="good-list">
                        {audit.whats_good.map((point, i) => (
                          <li key={i} className="good-item">
                            <span className="check-icon">✓</span>
                            <span>{point}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-neutral-500">No specific strengths listed.</p>
                    )}
                  </div>
                </div>

                {/* What Needs Improvement */}
                <div className="panel improve-panel">
                  <div className="panel-header">
                    <span className="panel-title">🛠️ Needs Improvement</span>
                    <span className="badge badge-amber">Action Items</span>
                  </div>
                  <div className="panel-body">
                    {audit.needs_improvement && audit.needs_improvement.length > 0 ? (
                      <div className="improve-list">
                        {audit.needs_improvement.map((item, i) => (
                          <div key={i} className="improve-card">
                            <h5 className="improve-point">
                              ⚠️ {item.point}
                            </h5>
                            <p className="improve-suggestion">
                              💡 <strong>Fix:</strong> {item.suggestion}
                            </p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-neutral-500">No critical fixes recommended.</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeSubTab === "extracted" && (
            <div className="extracted-data-view panel">
              <div className="panel-header">
                <span className="panel-title">Parsed Resume Content</span>
              </div>
              <div className="panel-body">
                {/* Summary */}
                {parsed?.summary && (
                  <div className="parsed-section">
                    <h4>Professional Summary</h4>
                    <p className="parsed-summary">{parsed.summary}</p>
                  </div>
                )}

                {/* Skills */}
                <div className="parsed-section">
                  <h4>Extracted Skills ({parsed?.skills?.length || 0})</h4>
                  <div className="skills-chips">
                    {parsed?.skills && parsed.skills.length > 0 ? (
                      parsed.skills.map((s, i) => (
                        <span key={i} className="skill-chip">
                          {s}
                        </span>
                      ))
                    ) : (
                      <span className="text-neutral-500">No skills detected.</span>
                    )}
                  </div>
                </div>

                {/* Experience */}
                <div className="parsed-section">
                  <h4>Work Experience</h4>
                  {parsed?.experience && parsed.experience.length > 0 ? (
                    <div className="exp-timeline">
                      {parsed.experience.map((exp, i) => (
                        <div key={i} className="exp-item">
                          <div className="exp-header">
                            <strong>{exp.role}</strong> at <span>{exp.company}</span>
                            {exp.duration && <span className="exp-duration">{exp.duration}</span>}
                          </div>
                          {exp.highlights && exp.highlights.length > 0 && (
                            <ul className="exp-highlights">
                              {exp.highlights.map((h, j) => (
                                <li key={j}>{h}</li>
                              ))}
                            </ul>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <span className="text-neutral-500">No work experience entries parsed.</span>
                  )}
                </div>

                {/* Projects */}
                {parsed?.projects && parsed.projects.length > 0 && (
                  <div className="parsed-section">
                    <h4>Projects</h4>
                    <div className="projects-grid">
                      {parsed.projects.map((proj, i) => (
                        <div key={i} className="project-card">
                          <strong>{proj.name}</strong>
                          <p>{proj.description}</p>
                          {proj.tech_stack && (
                            <div className="proj-tech">
                              {proj.tech_stack.map((t, k) => (
                                <span key={k} className="tech-badge">
                                  {t}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
