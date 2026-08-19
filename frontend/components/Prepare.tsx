"use client";

import { useState, useEffect, useRef } from "react";
import {
  generatePrepQuestions,
  getPrepQuestions,
  getPrepFilters,
  type PrepQuestionRecord,
} from "@/lib/api";

declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

const PRESET_ROLES = [
  "Senior Backend Engineer",
  "Full Stack Developer",
  "Frontend Engineer (React/Next.js)",
  "DevOps / Infrastructure Engineer",
  "AI / GenAI Engineer",
  "System Architect",
];

function formatMarkdownText(text: string) {
  const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={i}
          style={{
            background: "var(--gray-100)",
            color: "var(--brand-700)",
            padding: "2px 6px",
            borderRadius: "var(--r-sm)",
            fontFamily: "monospace",
            fontSize: "0.9em",
          }}
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return part;
  });
}

function renderFormattedAnswer(rawText: string) {
  const blocks = rawText.split(/\n\n+/);
  return blocks.map((block, bIdx) => {
    const trimmed = block.trim();
    if (!trimmed) return null;

    const lines = trimmed.split("\n").map((l) => l.trim()).filter(Boolean);
    const isList = lines.length > 0 && lines.every((l) => l.startsWith("*") || l.startsWith("-") || /^\d+\./.test(l));

    if (isList) {
      return (
        <ul key={bIdx} className="answer-bullet-list">
          {lines.map((line, lIdx) => {
            const cleanLine = line.replace(/^[\*\-\d\.]+\s*/, "");
            return <li key={lIdx}>{formatMarkdownText(cleanLine)}</li>;
          })}
        </ul>
      );
    }

    return (
      <p key={bIdx} className="answer-paragraph">
        {formatMarkdownText(trimmed)}
      </p>
    );
  });
}

export default function PrepareComponent() {
  const [questions, setQuestions] = useState<PrepQuestionRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [generating, setGenerating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Generation Controls
  const [selectedRole, setSelectedRole] = useState<string>("Senior Backend Engineer");
  const [customRole, setCustomRole] = useState<string>("");
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>("medium");
  const [topicInput, setTopicInput] = useState<string>("");

  // Filtering State
  const [diffFilter, setDiffFilter] = useState<string>("all");
  const [topicFilter, setTopicFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [availableTopics, setAvailableTopics] = useState<string[]>([]);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  // Practice Dictation State per Question
  const [practiceAnswers, setPracticeAnswers] = useState<Record<number, string>>({});
  const [listeningQId, setListeningQId] = useState<number | null>(null);
  const recognitionRef = useRef<any>(null);

  // Initial load
  useEffect(() => {
    fetchQuestions();
    fetchFilterOptions();

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      try {
        const rec = new SpeechRecognition();
        rec.continuous = true;
        rec.interimResults = true;
        rec.lang = "en-US";
        recognitionRef.current = rec;
      } catch {
        // Speech not supported
      }
    }
  }, []);

  const togglePracticeDictation = (qId: number) => {
    if (!recognitionRef.current) {
      alert("Speech recognition is not supported in this browser. Please try Chrome, Edge, or Safari.");
      return;
    }

    if (listeningQId === qId) {
      try { recognitionRef.current.stop(); } catch {}
      setListeningQId(null);
    } else {
      if (listeningQId !== null) {
        try { recognitionRef.current.stop(); } catch {}
      }

      recognitionRef.current.onresult = (event: any) => {
        let transcript = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        if (transcript.trim()) {
          setPracticeAnswers((prev) => ({
            ...prev,
            [qId]: (prev[qId] ? prev[qId].trim() + " " : "") + transcript.trim(),
          }));
        }
      };

      recognitionRef.current.onerror = () => {
        setListeningQId(null);
      };

      recognitionRef.current.onend = () => {
        setListeningQId(null);
      };

      try {
        recognitionRef.current.start();
        setListeningQId(qId);
      } catch {
        setListeningQId(null);
      }
    }
  };

  const fetchQuestions = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPrepQuestions();
      setQuestions(data);
      if (data.length > 0 && expandedId === null) {
        setExpandedId(data[0].id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load study questions.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const fetchFilterOptions = async () => {
    try {
      const res = await getPrepFilters();
      setAvailableTopics(res.topics || []);
    } catch {
      // Non-critical
    }
  };

  const handleGenerate = async () => {
    const activeRole = customRole.trim() || selectedRole;
    if (!activeRole) {
      setError("Please select or enter a target role.");
      return;
    }

    setGenerating(true);
    setError(null);
    try {
      const newQuestions = await generatePrepQuestions({
        role: activeRole,
        topic: topicInput.trim() || undefined,
        difficulty: selectedDifficulty,
        count: 5,
      });

      // Append new questions to top of list
      setQuestions((prev) => [...newQuestions, ...prev]);
      if (newQuestions.length > 0) {
        setExpandedId(newQuestions[0].id);
      }
      fetchFilterOptions();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Generation failed.";
      setError(msg);
    } finally {
      setGenerating(false);
    }
  };

  const toggleExpand = (id: number) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  // Filtered Questions
  const filteredQuestions = questions.filter((q) => {
    if (diffFilter !== "all" && q.difficulty.toLowerCase() !== diffFilter.toLowerCase()) {
      return false;
    }
    if (topicFilter !== "all" && q.topic.toLowerCase() !== topicFilter.toLowerCase()) {
      return false;
    }
    if (searchQuery.trim()) {
      const term = searchQuery.toLowerCase();
      const inText = q.question_text.toLowerCase().includes(term);
      const inAnswer = q.model_answer_text.toLowerCase().includes(term);
      const inTopic = q.topic.toLowerCase().includes(term);
      const inRole = q.role.toLowerCase().includes(term);
      if (!inText && !inAnswer && !inTopic && !inRole) return false;
    }
    return true;
  });

  const getDifficultyBadge = (diff: string) => {
    const d = diff.toLowerCase();
    if (d === "easy") return <span className="badge badge-green">Easy</span>;
    if (d === "hard") return <span className="badge badge-amber">Hard</span>;
    return <span className="badge badge-blue">Medium</span>;
  };

  return (
    <div className="prep-container">
      {/* Header */}
      <div className="dashboard-header">
        <h1 className="dashboard-greeting">
          Interview <span>Study &amp; Prepare</span>
        </h1>
        <p className="dashboard-subtitle">
          Browse AI-generated practice questions and comprehensive model answers tailored to your target engineering role.
        </p>
      </div>

      {/* Generation Panel */}
      <div className="panel prep-gen-panel">
        <div className="panel-header">
          <span className="panel-title">✨ Generate New Practice Questions</span>
          <span className="badge badge-purple">Gemini 3.5 AI</span>
        </div>
        <div className="panel-body">
          <div className="gen-controls-grid">
            {/* Role Select */}
            <div className="control-group">
              <label className="control-label" htmlFor="role-select">Target Role</label>
              <select
                id="role-select"
                className="control-input"
                value={selectedRole}
                onChange={(e) => {
                  setSelectedRole(e.target.value);
                  setCustomRole("");
                }}
              >
                {PRESET_ROLES.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
                <option value="custom">+ Custom Role...</option>
              </select>
              {selectedRole === "custom" && (
                <input
                  type="text"
                  className="control-input"
                  style={{ marginTop: "var(--sp-2)" }}
                  placeholder="e.g. Lead Data Platform Engineer"
                  value={customRole}
                  onChange={(e) => setCustomRole(e.target.value)}
                />
              )}
            </div>

            {/* Difficulty Selector */}
            <div className="control-group">
              <label className="control-label">Difficulty Level</label>
              <div className="diff-pills" role="radiogroup" aria-label="Difficulty selection">
                {["easy", "medium", "hard"].map((d) => (
                  <button
                    key={d}
                    type="button"
                    className={`diff-pill ${selectedDifficulty === d ? "active" : ""}`}
                    onClick={() => setSelectedDifficulty(d)}
                  >
                    {d.charAt(0).toUpperCase() + d.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            {/* Optional Topic */}
            <div className="control-group">
              <label className="control-label" htmlFor="topic-input">Specific Topic (Optional)</label>
              <input
                id="topic-input"
                type="text"
                className="control-input"
                placeholder="e.g. System Design, Indexing, React Async"
                value={topicInput}
                onChange={(e) => setTopicInput(e.target.value)}
              />
            </div>
          </div>

          <div className="gen-action-row">
            <button
              type="button"
              className="btn btn-primary btn-lg"
              onClick={handleGenerate}
              disabled={generating}
            >
              {generating ? (
                <>
                  <span className="spinner-sm" aria-hidden="true" /> Generating 5 Questions with Gemini...
                </>
              ) : (
                "✨ Generate Practice Questions"
              )}
            </button>
            <span className="gen-hint">
              Uses live Gemini AI &amp; tailors questions to your uploaded resume background.
            </span>
          </div>

          {error && (
            <div className="alert alert-error" role="alert" style={{ marginTop: "var(--sp-3)" }}>
              <span>⚠️</span>
              <div>{error}</div>
            </div>
          )}
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="prep-filter-bar">
        <div className="search-box">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            className="search-input"
            placeholder="Search questions or keywords..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        {/* Difficulty Filter Chips */}
        <div className="filter-chips">
          <span className="filter-label">Difficulty:</span>
          {["all", "easy", "medium", "hard"].map((d) => (
            <button
              key={d}
              type="button"
              className={`chip ${diffFilter === d ? "active" : ""}`}
              onClick={() => setDiffFilter(d)}
            >
              {d.charAt(0).toUpperCase() + d.slice(1)}
            </button>
          ))}
        </div>

        {/* Topic Filter Select */}
        {availableTopics.length > 0 && (
          <div className="filter-chips">
            <span className="filter-label">Topic:</span>
            <select
              className="chip-select"
              value={topicFilter}
              onChange={(e) => setTopicFilter(e.target.value)}
            >
              <option value="all">All Topics ({questions.length})</option>
              {availableTopics.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Questions List & Accordion View */}
      {loading ? (
        <div className="panel" style={{ textAlign: "center", padding: "var(--sp-8)" }}>
          <div className="spinner" style={{ margin: "0 auto" }} aria-hidden="true" />
          <p style={{ marginTop: "var(--sp-3)", color: "var(--gray-500)" }}>Loading stored prep questions...</p>
        </div>
      ) : filteredQuestions.length === 0 ? (
        <div className="panel empty-state-panel">
          <div className="empty-state">
            <div className="empty-state-icon">📚</div>
            <h3>No practice questions match your filter</h3>
            <p className="empty-state-text">
              Click &quot;Generate Practice Questions&quot; above to create AI-powered study material for your role.
            </p>
          </div>
        </div>
      ) : (
        <div className="prep-questions-list">
          <div className="list-meta">
            <span>Showing <strong>{filteredQuestions.length}</strong> stored study questions</span>
            <button type="button" className="btn btn-sm btn-outline" onClick={handleGenerate} disabled={generating}>
              + Generate 5 More Questions
            </button>
          </div>

          {filteredQuestions.map((q, index) => {
            const isExpanded = expandedId === q.id;
            const isRec = listeningQId === q.id;
            const pAns = practiceAnswers[q.id] || "";
            return (
              <div key={q.id} className={`panel question-card ${isExpanded ? "expanded" : ""}`}>
                <div
                  className="question-header"
                  onClick={() => toggleExpand(q.id)}
                  role="button"
                  tabIndex={0}
                  aria-expanded={isExpanded}
                >
                  <div className="question-title-row">
                    <span className="q-number">Q{filteredQuestions.length - index}</span>
                    <h3 className="question-text">{q.question_text}</h3>
                  </div>

                  <div className="question-tags-row">
                    {getDifficultyBadge(q.difficulty)}
                    <span className="badge badge-gray">{q.topic}</span>
                    <span className="role-tag">👤 {q.role}</span>
                    <span className="expand-indicator">{isExpanded ? "▲ Hide Model Answer" : "▼ View Model Answer"}</span>
                  </div>
                </div>

                {isExpanded && (
                  <div className="model-answer-pane">
                    <div className="answer-header">
                      <span className="answer-icon">💡</span>
                      <span className="answer-label">AI Model Answer &amp; Solution Guide</span>
                    </div>

                    <div className="answer-content">
                      {renderFormattedAnswer(q.model_answer_text)}
                    </div>

                    {/* Interactive Voice Practice Section */}
                    <div style={{ marginTop: "var(--sp-6)", paddingTop: "var(--sp-4)", borderTop: "1px dashed var(--border)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--sp-2)", flexWrap: "wrap", gap: "var(--sp-2)" }}>
                        <span style={{ fontSize: "var(--text-xs)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--gray-600)" }}>
                          🗣️ Voice Practice Area
                        </span>
                        <button
                          type="button"
                          onClick={() => togglePracticeDictation(q.id)}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "var(--sp-2)",
                            padding: "4px 12px",
                            borderRadius: "var(--r-full)",
                            fontSize: "var(--text-xs)",
                            fontWeight: 700,
                            cursor: "pointer",
                            border: isRec ? "1px solid var(--danger-border)" : "1px solid var(--brand-300)",
                            background: isRec ? "var(--danger-bg)" : "var(--brand-50)",
                            color: isRec ? "var(--danger-text)" : "var(--brand-700)",
                          }}
                        >
                          {isRec ? "🔴 Recording... (Click to stop)" : "🎙️ Practice Speaking Answer"}
                        </button>
                      </div>

                      <textarea
                        className="textarea"
                        style={{ minHeight: 90, fontSize: "var(--text-sm)" }}
                        placeholder="Click '🎙️ Practice Speaking Answer' to speak your answer out loud and practice your verbal delivery..."
                        value={pAns}
                        onChange={(e) => setPracticeAnswers({ ...practiceAnswers, [q.id]: e.target.value })}
                      />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
