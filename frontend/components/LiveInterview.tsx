"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  apiNextQuestion,
  apiSubmitAnswer,
  type InterviewQuestionRecord,
  type InterviewRecord,
} from "@/lib/api";

interface LiveInterviewProps {
  interview: InterviewRecord;
  onSessionComplete?: (interviewId: number) => void;
  onExit?: () => void;
}

export default function LiveInterviewComponent({
  interview,
  onSessionComplete,
  onExit,
}: LiveInterviewProps) {
  // Session Question State
  const [currentQuestion, setCurrentQuestion] = useState<InterviewQuestionRecord | null>(null);
  const [answerText, setAnswerText] = useState<string>("");
  const [loadingQuestion, setLoadingQuestion] = useState<boolean>(true);
  const [submittingAnswer, setSubmittingAnswer] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Session Progress
  const [completedCount, setCompletedCount] = useState<number>(0);
  const totalQuestions = interview.question_count || 5;
  const [isSessionFinished, setIsSessionFinished] = useState<boolean>(false);

  // Countdown Timer State (for Hard tier 120s timer)
  const [timeLeft, setTimeLeft] = useState<number | null>(null);
  const [initialTimer, setInitialTimer] = useState<number | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const isSubmittingRef = useRef<boolean>(false);

  // Auto-submit callback when timer hits 0
  const handleAutoSubmit = useCallback(async () => {
    if (isSubmittingRef.current || !currentQuestion) return;
    console.log("[TIMER] Time expired! Auto-submitting current answer...");
    await handleSubmit(true);
  }, [currentQuestion]);

  // Load next question on component mount or step advance
  const loadNextQuestion = useCallback(async () => {
    setLoadingQuestion(true);
    setError(null);
    setAnswerText("");
    try {
      const q = await apiNextQuestion(interview.id);
      setCurrentQuestion(q);

      // Handle Timer setup for Hard questions
      if (q.time_limit_seconds && q.time_limit_seconds > 0) {
        setTimeLeft(q.time_limit_seconds);
        setInitialTimer(q.time_limit_seconds);
      } else {
        setTimeLeft(null);
        setInitialTimer(null);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load next question.";
      setError(msg);
    } finally {
      setLoadingQuestion(false);
    }
  }, [interview.id]);

  useEffect(() => {
    loadNextQuestion();
  }, [loadNextQuestion]);

  // Active Timer interval effect
  useEffect(() => {
    if (timeLeft === null || loadingQuestion || submittingAnswer || isSessionFinished) {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }

    if (timeLeft <= 0) {
      if (timerRef.current) clearInterval(timerRef.current);
      handleAutoSubmit();
      return;
    }

    timerRef.current = setInterval(() => {
      setTimeLeft((prev) => (prev !== null && prev > 0 ? prev - 1 : 0));
    }, 1000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [timeLeft, loadingQuestion, submittingAnswer, isSessionFinished, handleAutoSubmit]);

  // Handle Answer Submission (Manual or Auto-Submit)
  const handleSubmit = async (isAutoSubmit = false) => {
    if (isSubmittingRef.current || !currentQuestion) return;
    isSubmittingRef.current = true;
    setSubmittingAnswer(true);
    setError(null);

    // Stop timer
    if (timerRef.current) clearInterval(timerRef.current);

    const finalAnswer = answerText.trim() || (isAutoSubmit ? "[Time expired — answer submitted automatically]" : "No response provided.");

    try {
      await apiSubmitAnswer(interview.id, currentQuestion.id, finalAnswer);
      setCompletedCount((prev) => prev + 1);

      const nextOrder = currentQuestion.order_index;
      if (nextOrder >= totalQuestions) {
        setIsSessionFinished(true);
        if (onSessionComplete) {
          onSessionComplete(interview.id);
        }
      } else {
        await loadNextQuestion();
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to submit answer.";
      setError(msg);
    } finally {
      setSubmittingAnswer(false);
      isSubmittingRef.current = false;
    }
  };

  // Keyboard shortcut: Ctrl + Enter / Cmd + Enter to submit
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      handleSubmit(false);
    }
  };

  // Format seconds to mm:ss
  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  // Render Session Finished Screen
  if (isSessionFinished) {
    return (
      <div style={{ maxWidth: 640, margin: "0 auto" }}>
        <div className="card" style={{ padding: "var(--sp-12)", textAlign: "center" }}>
          <div
            style={{
              width: 80, height: 80,
              background: "var(--success-bg)",
              borderRadius: "var(--r-full)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: "2.5rem", margin: "0 auto var(--sp-6)",
            }}
            aria-hidden="true"
          >
            🎉
          </div>
          <h1 style={{ fontSize: "var(--text-2xl)", fontWeight: 800, color: "var(--gray-900)", marginBottom: "var(--sp-3)" }}>
            Interview Complete!
          </h1>
          <p style={{ fontSize: "var(--text-sm)", color: "var(--gray-600)", maxWidth: 380, margin: "0 auto var(--sp-6)", lineHeight: 1.65 }}>
            You completed all <strong>{totalQuestions} question{totalQuestions !== 1 ? "s" : ""}</strong> for session #{interview.id} — {interview.role}.
          </p>

          <div
            style={{
              background: "var(--gray-50)", border: "1px solid var(--border)",
              borderRadius: "var(--r-lg)", padding: "var(--sp-4)",
              textAlign: "left", maxWidth: 360, margin: "0 auto var(--sp-6)",
              display: "flex", flexDirection: "column", gap: "var(--sp-3)",
            }}
          >
            {[
              ["Target Role", interview.role],
              ["Interview Format", interview.interview_type],
              ["Questions Completed", `${totalQuestions} / ${totalQuestions}`],
            ].map(([label, value]) => (
              <div key={label} style={{ display: "flex", justifyContent: "space-between", fontSize: "var(--text-sm)" }}>
                <span style={{ color: "var(--gray-500)" }}>{label}</span>
                <span style={{ fontWeight: 600, color: "var(--gray-900)", textTransform: "capitalize" }}>{value}</span>
              </div>
            ))}
          </div>

          <div style={{ display: "flex", gap: "var(--sp-3)", justifyContent: "center", flexWrap: "wrap" }}>
            {onExit && (
              <button className="btn btn-secondary" onClick={onExit}>
                ← Back to Setup
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", display: "flex", flexDirection: "column", gap: "var(--sp-5)" }}>

      {/* ── Session header ───────── */}
      <div
        style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          borderBottom: "1px solid var(--border)", paddingBottom: "var(--sp-4)",
          flexWrap: "wrap", gap: "var(--sp-3)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "var(--sp-3)" }}>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={onExit}
            style={{ paddingLeft: 0 }}
          >
            ← Exit
          </button>
          <span style={{ color: "var(--border-strong)" }}>|</span>
          <span style={{ fontWeight: 600, color: "var(--gray-900)", fontSize: "var(--text-sm)" }}>{interview.role}</span>
          <span className="badge badge-blue" style={{ textTransform: "capitalize" }}>{interview.interview_type}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--sp-2)" }}>
          <span style={{ fontSize: "var(--text-xs)", fontWeight: 700, color: "var(--gray-400)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Question</span>
          <span
            style={{
              padding: "3px 12px",
              background: "var(--gray-900)",
              color: "#fff",
              borderRadius: "var(--r-full)",
              fontSize: "var(--text-xs)",
              fontWeight: 800,
            }}
          >
            {currentQuestion ? currentQuestion.order_index : completedCount + 1} / {totalQuestions}
          </span>
        </div>
      </div>

      {/* ── Progress bar ─────────── */}
      <div style={{ display: "flex", gap: "var(--sp-2)" }} role="progressbar" aria-valuenow={completedCount} aria-valuemax={totalQuestions} aria-label="Interview progress">
        {Array.from({ length: totalQuestions }).map((_, idx) => {
          const isDone = idx < completedCount;
          const isCurrent = currentQuestion && idx === currentQuestion.order_index - 1;
          return (
            <div
              key={idx}
              style={{
                height: 6, flex: 1, borderRadius: "var(--r-full)",
                transition: "background var(--dur-normal) var(--ease)",
                background: isDone
                  ? "var(--success-text)"
                  : isCurrent
                  ? "var(--brand-500)"
                  : "var(--gray-200)",
                boxShadow: isCurrent ? "0 0 0 3px var(--brand-100)" : "none",
              }}
            />
          );
        })}
      </div>

      {/* ── Error ────────────────── */}
      {error && (
        <div className="alert alert-error" role="alert" style={{ justifyContent: "space-between" }}>
          <span>⚠️ {error}</span>
          <button className="btn btn-sm btn-secondary" onClick={loadNextQuestion}>
            Retry
          </button>
        </div>
      )}

      {/* ── Loading question ──────── */}
      {loadingQuestion ? (
        <div className="card">
          <div className="card-body">
            <div className="page-loading" style={{ minHeight: "28vh" }}>
              <div className="spinner" />
              <div>
                <p className="page-loading-title">Generating Question {completedCount + 1}…</p>
                <p className="page-loading-sub">
                  Gemini AI &amp; LangGraph are tailoring this question to your profile and difficulty level.
                </p>
              </div>
            </div>
          </div>
        </div>
      ) : currentQuestion ? (
        <div className="card" style={{ boxShadow: "var(--shadow-md)" }}>
          <div className="card-body" style={{ display: "flex", flexDirection: "column", gap: "var(--sp-6)" }}>

            {/* Question metadata + timer */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "var(--sp-3)" }}>
              <div style={{ display: "flex", gap: "var(--sp-2)", flexWrap: "wrap" }}>
                <span className="badge badge-gray" style={{ textTransform: "capitalize" }}>
                  🏷️ {currentQuestion.category.replace(/_/g, " ")}
                </span>
                <span
                  className={
                    currentQuestion.difficulty === "hard"
                      ? "badge badge-purple"
                      : currentQuestion.difficulty === "medium"
                      ? "badge badge-blue"
                      : "badge badge-green"
                  }
                  style={{ textTransform: "capitalize" }}
                >
                  {currentQuestion.difficulty}
                </span>
              </div>

              {timeLeft !== null && initialTimer !== null && (
                <div
                  style={{
                    display: "flex", alignItems: "center", gap: "var(--sp-2)",
                    padding: "var(--sp-2) var(--sp-4)",
                    borderRadius: "var(--r-full)",
                    border: `1px solid ${timeLeft <= 15 ? "var(--danger-border)" : "var(--warning-border)"}`,
                    background: timeLeft <= 15 ? "var(--danger-bg)" : "var(--warning-bg)",
                    fontSize: "var(--text-xs)",
                    fontWeight: 700,
                    color: timeLeft <= 15 ? "var(--danger-text)" : "var(--warning-text)",
                    fontFamily: "monospace",
                    animation: timeLeft <= 15 ? "pulse 1s infinite" : "none",
                  }}
                  role="timer"
                  aria-live="polite"
                >
                  ⏱️ {formatTime(timeLeft)}
                </div>
              )}
            </div>

            {/* Question text */}
            <div
              style={{
                background: "var(--gray-50)",
                borderRadius: "var(--r-lg)",
                padding: "var(--sp-6)",
                border: "1px solid var(--border)",
              }}
            >
              <p style={{ fontSize: "var(--text-xs)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--gray-400)", marginBottom: "var(--sp-3)" }}>
                Question #{currentQuestion.order_index}
              </p>
              <h2
                style={{
                  fontSize: "clamp(1.125rem, 2.5vw, 1.375rem)",
                  fontWeight: 700,
                  color: "var(--gray-900)",
                  lineHeight: 1.55,
                  letterSpacing: "-0.2px",
                }}
              >
                {currentQuestion.question_text}
              </h2>
            </div>

            {/* Answer area */}
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--sp-3)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "var(--sp-2)" }}>
                <label htmlFor="answer-input" className="input-label">
                  Your Response
                </label>
                <span style={{ fontSize: "var(--text-xs)", color: "var(--gray-400)" }}>
                  {answerText.length} chars · Ctrl+Enter to submit
                </span>
              </div>
              <textarea
                id="answer-input"
                className="textarea"
                style={{ minHeight: 200, fontSize: "var(--text-base)", lineHeight: 1.7 }}
                placeholder="Type your answer clearly. Explain your thought process, trade-offs, and technical reasoning…"
                value={answerText}
                onChange={(e) => setAnswerText(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={submittingAnswer}
              />
            </div>

            {/* Submit bar */}
            <div
              style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                borderTop: "1px solid var(--border)", paddingTop: "var(--sp-5)",
                flexWrap: "wrap", gap: "var(--sp-3)",
              }}
            >
              <span style={{ fontSize: "var(--text-xs)", color: "var(--gray-400)" }}>
                {submittingAnswer ? "Evaluating and saving your answer…" : "Ready to proceed?"}
              </span>
              <button
                type="button"
                className="btn btn-primary btn-lg"
                onClick={() => handleSubmit(false)}
                disabled={submittingAnswer || !answerText.trim()}
              >
                {submittingAnswer ? (
                  <>
                    <span className="spinner-sm" />
                    Evaluating…
                  </>
                ) : (
                  "Submit & Continue →"
                )}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
