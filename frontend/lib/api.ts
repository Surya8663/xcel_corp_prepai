/**
 * PrepAI — Frontend API Client.
 * Communicates with the FastAPI backend (/api/v1).
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function checkResponseOk(res: Response, defaultMessage: string = "Request failed"): Promise<void> {
  if (res.ok) return;

  let errMessage = defaultMessage;
  try {
    const json = await res.json();
    if (json.message) {
      errMessage = typeof json.message === "string" ? json.message : JSON.stringify(json.message);
    } else if (json.detail) {
      errMessage = typeof json.detail === "string" ? json.detail : JSON.stringify(json.detail);
    }
  } catch {
    errMessage = `${defaultMessage} (HTTP ${res.status} ${res.statusText})`;
  }

  throw new Error(errMessage);
}

export interface ParsedResumeExperience {
  company: string;
  role: string;
  duration?: string;
  highlights?: string[];
}

export interface ParsedResumeEducation {
  institution: string;
  degree: string;
  year?: string;
}

export interface ParsedResumeProject {
  name: string;
  description: string;
  tech_stack?: string[];
}

export interface ParsedResumeData {
  summary?: string;
  skills?: string[];
  experience?: ParsedResumeExperience[];
  education?: ParsedResumeEducation[];
  projects?: ParsedResumeProject[];
  certifications?: string[];
}

export interface ResumeNeedImprovement {
  point: string;
  suggestion: string;
}

export interface ResumeAuditFeedback {
  overall_score: number;
  scoring_reasoning?: string;
  industry_level?: string;
  industry_level_justification?: string;
  whats_good?: string[];
  needs_improvement?: ResumeNeedImprovement[];
  overall_verdict?: string;
}

export interface ResumeRecord {
  id: number;
  candidate_id: number;
  file_url?: string;
  raw_extracted_text?: string;
  parsed_json?: ParsedResumeData;
  audit_score?: number;
  audit_feedback_json?: ResumeAuditFeedback;
  created_at: string;
}

export async function uploadResume(file: File): Promise<ResumeRecord> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE_URL}/resume/upload`, {
    method: "POST",
    body: formData,
  });

  await checkResponseOk(res, "Failed to upload and audit resume");
  return res.json();
}

export async function getResume(id: number): Promise<ResumeRecord> {
  const res = await fetch(`${API_BASE_URL}/resume/${id}`);
  await checkResponseOk(res, `Failed to fetch resume #${id}`);
  return res.json();
}

export async function listResumes(): Promise<{ id: number; file_url?: string; audit_score?: number; created_at: string }[]> {
  const res = await fetch(`${API_BASE_URL}/resume/list`);
  await checkResponseOk(res, "Failed to list resumes");
  return res.json();
}

// ── Prep / Study Mode API ───────────────────────────────────────────────────

export interface PrepQuestionRecord {
  id: number;
  candidate_id: number;
  role: string;
  topic: string;
  difficulty: "easy" | "medium" | "hard" | string;
  question_text: string;
  model_answer_text: string;
  created_at: string;
}

export interface GeneratePrepQuestionsPayload {
  role: string;
  topic?: string;
  difficulty?: string;
  count?: number;
}

export async function generatePrepQuestions(payload: GeneratePrepQuestionsPayload): Promise<PrepQuestionRecord[]> {
  const res = await fetch(`${API_BASE_URL}/prep/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      role: payload.role,
      topic: payload.topic || undefined,
      difficulty: payload.difficulty || "medium",
      count: payload.count || 5,
    }),
  });

  await checkResponseOk(res, "Failed to generate prep questions");
  return res.json();
}

export async function getPrepQuestions(params?: {
  role?: string;
  topic?: string;
  difficulty?: string;
  limit?: number;
  offset?: number;
}): Promise<PrepQuestionRecord[]> {
  const query = new URLSearchParams();
  if (params?.role) query.append("role", params.role);
  if (params?.topic) query.append("topic", params.topic);
  if (params?.difficulty) query.append("difficulty", params.difficulty);
  if (params?.limit) query.append("limit", String(params.limit));
  if (params?.offset) query.append("offset", String(params.offset));

  const url = `${API_BASE_URL}/prep/questions?${query.toString()}`;
  const res = await fetch(url);
  await checkResponseOk(res, "Failed to fetch prep questions");
  return res.json();
}

export async function getPrepFilters(): Promise<{ roles: string[]; topics: string[] }> {
  const res = await fetch(`${API_BASE_URL}/prep/filters`);
  await checkResponseOk(res, "Failed to fetch prep filters");
  return res.json();
}

// ── Interview Setup API ──────────────────────────────────────────────────────

export interface CreateInterviewPayload {
  role: string;
  interview_type: string;
  difficulty_mode: string;
  duration_minutes?: number;
  question_count?: number;
  resume_id?: number | null;
  job_description_id?: number | null;
}

export interface InterviewRecord {
  id: number;
  candidate_id: number;
  role: string;
  interview_type: string;
  difficulty_mode: string;
  duration_minutes?: number;
  question_count: number;
  status: string;
  resume_id?: number | null;
  job_description_id?: number | null;
  created_at: string;
}

export interface JobDescriptionRecord {
  id: number;
  candidate_id: number;
  raw_text: string;
  parsed_required_skills_json?: {
    role_title?: string;
    company?: string;
    required_skills?: string[];
    preferred_skills?: string[];
    responsibilities?: string[];
    qualifications?: string[];
    summary?: string;
  };
  created_at: string;
}

export async function createInterview(payload: CreateInterviewPayload): Promise<InterviewRecord> {
  const res = await fetch(`${API_BASE_URL}/interview/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  await checkResponseOk(res, "Failed to create interview session");
  return res.json();
}

export async function getInterview(id: number): Promise<InterviewRecord> {
  const res = await fetch(`${API_BASE_URL}/interview/${id}`);
  await checkResponseOk(res, `Failed to fetch interview #${id}`);
  return res.json();
}

export async function uploadJobDescription(rawText: string): Promise<JobDescriptionRecord> {
  const res = await fetch(`${API_BASE_URL}/job-description`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ raw_text: rawText }),
  });

  await checkResponseOk(res, "Failed to save job description");
  return res.json();
}

export async function listJobDescriptions(): Promise<JobDescriptionRecord[]> {
  const res = await fetch(`${API_BASE_URL}/job-descriptions`);
  await checkResponseOk(res, "Failed to list job descriptions");
  return res.json();
}

export interface InterviewQuestionRecord {
  id: number;
  interview_id: number;
  order_index: number;
  question_text: string;
  difficulty: string;
  category: string;
  time_limit_seconds?: number | null;
  created_at: string;
}

export async function apiNextQuestion(interviewId: number): Promise<InterviewQuestionRecord> {
  const res = await fetch(`${API_BASE_URL}/interview/${interviewId}/next-question`, {
    method: "POST",
  });

  await checkResponseOk(res, "Failed to fetch next question");
  return res.json();
}

export async function apiSubmitAnswer(
  interviewId: number,
  questionId: number,
  answerText: string
): Promise<{ id: number; question_id: number; answer_text: string; created_at: string }> {
  const res = await fetch(`${API_BASE_URL}/interview/${interviewId}/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question_id: questionId, answer_text: answerText }),
  });

  await checkResponseOk(res, "Failed to submit answer");
  return res.json();
}

export interface DetailedQuestionAnswer {
  question_id: number;
  order_index: number;
  category: string;
  difficulty: string;
  question_text: string;
  answer_text?: string | null;
  technical_score: number;
  relevance_score: number;
  completeness_score: number;
  clarity_score: number;
  overall_score: number;
  feedback_text: string;
}

export interface InterviewReportRecord {
  interview_id: number;
  candidate_id: number;
  role: string;
  interview_type: string;
  difficulty_mode: string;
  status: string;
  completed_at?: string | null;
  overall_score: number;
  avg_technical_score: number;
  avg_relevance_score: number;
  avg_completeness_score: number;
  avg_clarity_score: number;
  strengths: string[];
  weaknesses: string[];
  recommendations: string;
  executive_summary?: string | null;
  questions: DetailedQuestionAnswer[];
}

export interface CandidateProgressRecord {
  interview_id: number;
  role: string;
  interview_type: string;
  difficulty_mode: string;
  overall_score: number;
  avg_technical_score: number;
  completed_at: string;
}

export async function apiCompleteInterview(interviewId: number): Promise<InterviewReportRecord> {
  const res = await fetch(`${API_BASE_URL}/interview/${interviewId}/complete`, {
    method: "POST",
  });

  await checkResponseOk(res, "Failed to finalize interview session");
  return res.json();
}

export async function apiGetInterviewReport(interviewId: number): Promise<InterviewReportRecord> {
  const res = await fetch(`${API_BASE_URL}/interview/${interviewId}/report`);
  await checkResponseOk(res, `Failed to fetch report for interview #${interviewId}`);
  return res.json();
}

export async function apiGetCandidateProgress(): Promise<CandidateProgressRecord[]> {
  const res = await fetch(`${API_BASE_URL}/candidate/progress`);
  await checkResponseOk(res, "Failed to fetch candidate progress history");
  return res.json();
}
