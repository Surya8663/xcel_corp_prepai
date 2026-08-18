"""
PrepAI — Centralized Prompt Template Library.

ARCHITECTURE RULE:
  All prompts used anywhere in the app must live here as named functions.
  No inline f-strings scattered across service files.

STRUCTURE:
  Each feature has its own section.  Templates return str (the full prompt).
  Actual prompt content is filled in during the phase where that feature is built.
  TODO markers indicate what each prompt must achieve when implemented.

GUIDELINES (to follow when filling in prompts):
  - Always specify the output format explicitly in the prompt.
  - For structured JSON output: describe the exact schema inline.
  - For evaluation prompts: include a scoring rubric with numeric ranges.
  - Keep prompts deterministic (avoid "be creative" instructions).
  - Always include a "respond only with..." or "output format:" line.
"""

from __future__ import annotations


def resume_parse_and_audit_prompt(raw_resume_text: str) -> str:
    """
    Unified single-pass prompt: extracts structured resume data AND generates
    the Resume Audit score and feedback in a single Gemini call.
    """
    return f"""You are a senior software engineering recruiter and resume parsing expert.
Analyze the following resume text extracted from a candidate's file.

Resume Text:
---
{raw_resume_text[:8000]}
---

Return a JSON object with EXACTLY two top-level keys: "parsed" and "audit".

Output Schema:
{{
  "parsed": {{
    "summary": "<professional summary or objective statement if present, else empty string>",
    "skills": ["<skill 1>", "<skill 2>", "..."],
    "experience": [
      {{
        "company": "<company name>",
        "role": "<job title>",
        "duration": "<e.g. Jan 2021 - Mar 2023 or 2 years>",
        "highlights": ["<achievement 1>", "<achievement 2>"]
      }}
    ],
    "education": [
      {{
        "institution": "<school/university name>",
        "degree": "<degree & major>",
        "year": "<year or date range>"
      }}
    ],
    "projects": [
      {{
        "name": "<project name>",
        "description": "<short description>",
        "tech_stack": ["<tech 1>", "<tech 2>"]
      }}
    ],
    "certifications": ["<certification name>"]
  }},
  "audit": {{
    "overall_score": <integer 0-100>,
    "scoring_reasoning": "<2-3 sentences explaining this score based on actual skills, companies, and achievements>",
    "industry_level": "<one of: Entry-Level | Needs Work | Almost Ready | Industry-Ready | Senior-Ready>",
    "industry_level_justification": "<2-3 sentences justifying this level>",
    "whats_good": [
      "<specific observation 1 citing real companies/projects/skills from the text>",
      "<specific observation 2 citing real companies/projects/skills from the text>"
    ],
    "needs_improvement": [
      {{
        "point": "<specific weakness found in text>",
        "suggestion": "<actionable fix with example>"
      }}
    ],
    "overall_verdict": "<1-2 sentence summary of resume state and main opportunity>"
  }}
}}

Rules & Constraints:
1. SCORING METHODOLOGY: Do NOT claim to use an official ATS algorithm (none exists). Evaluate based on scannability, clarity, keyword strength, quantified impact, and formatting.
2. whats_good: MUST cite real company names, project titles, or specific technologies from the text. No generic empty praise.
3. needs_improvement: Provide 2-5 actionable improvement recommendations.
4. Extract ALL skills present in text.
5. Return ONLY the raw JSON object — no markdown fences, no leading/trailing commentary.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — RESUME PARSING
# ═══════════════════════════════════════════════════════════════════════════════

def resume_parse_prompt(raw_resume_text: str) -> str:
    """
    Prompt to extract structured data from raw resume text.

    Expected output (JSON):
      {
        "summary": str,
        "skills": [str],
        "experience": [{"company": str, "role": str, "duration": str, "highlights": [str]}],
        "education": [{"institution": str, "degree": str, "year": str}],
        "projects": [{"name": str, "description": str, "tech_stack": [str]}],
        "certifications": [str]
      }

    TODO (Phase: Resume Audit):
      - Instruct the model to extract exactly the schema above.
      - Handle multi-page, poorly formatted, and ATS-style resumes.
      - Preserve original wording for skills / role titles.
      - Return empty lists (never null) for missing sections.
    """
def resume_parse_prompt(raw_resume_text: str) -> str:
    """
    Prompt to extract structured data from raw resume text.

    Expected output (JSON) — see schema inline in prompt body.
    """
    return f"""You are an expert resume parser. Your job is to extract structured information
from the following raw resume text, which was parsed from a PDF or DOCX file.

Resume text:
---
{raw_resume_text[:8000]}
---

Return a JSON object with EXACTLY this structure (no extra keys, no markdown):
{{
  "summary": "<professional summary or objective statement if present, else empty string>",
  "skills": ["<skill 1>", "<skill 2>", "..."],
  "experience": [
    {{
      "company": "<company name>",
      "role": "<job title>",
      "duration": "<e.g. Jan 2021 - Mar 2023 or 2 years>",
      "highlights": ["<achievement or responsibility>", "..."]
    }}
  ],
  "education": [
    {{
      "institution": "<school or university name>",
      "degree": "<degree type and field, e.g. B.Tech Computer Science>",
      "year": "<graduation year or date range>"
    }}
  ],
  "projects": [
    {{
      "name": "<project name>",
      "description": "<what the project does in 1-2 sentences>",
      "tech_stack": ["<technology 1>", "<technology 2>"]
    }}
  ],
  "certifications": ["<certification name and issuer if available>"]
}}

Rules:
- Extract ALL skills mentioned anywhere (technical tools, languages, frameworks, soft skills).
- Preserve exact company names, job titles, and technology names as written.
- If a section is absent from the resume, return an empty array [] or empty string "".
- Do NOT invent or hallucinate any content not explicitly present in the text.
- Return ONLY the JSON object — no markdown fences, no explanation text.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — RESUME AUDITING
# ═══════════════════════════════════════════════════════════════════════════════

def resume_audit_prompt(parsed_resume_json: dict, job_description_text: str | None = None) -> str:
    """
    Prompt to evaluate resume quality and return a structured audit report.

    Expected output (JSON):
      {
        "overall_score": float (0–100),
        "section_scores": {"summary": float, "skills": float, "experience": float, ...},
        "strengths": [str],
        "weaknesses": [str],
        "improvement_suggestions": [{"section": str, "suggestion": str, "priority": "high"|"medium"|"low"}],
        "ats_compatibility_score": float (0–100),
        "keyword_gaps": [str]   # skills in JD not found in resume (if JD provided)
      }

    TODO (Phase: Resume Audit):
      - Include ATS scoring rubric in the prompt.
      - If job_description_text is provided, perform gap analysis.
      - Penalise vague bullet points (e.g., "worked on various projects").
      - Reward quantified achievements (e.g., "reduced latency by 40%").
    """
def resume_audit_prompt(parsed_resume_json: dict, job_description_text: str | None = None) -> str:
    """
    Prompt to evaluate resume quality and return a structured audit report.

    Expected output (JSON) — see schema inline in prompt body.
    """
    import json
    parsed_str = json.dumps(parsed_resume_json, indent=2)[:6000]
    jd_section = (
        f"\nJob Description (for gap analysis):\n---\n{job_description_text[:2000]}\n---\n"
        if job_description_text
        else ""
    )

    return f"""You are a professional resume reviewer and senior career coach with 10+ years of experience.
Your job is to evaluate this resume and provide an honest, specific, actionable assessment.

IMPORTANT SCORING NOTE: You are NOT using any official ATS (Applicant Tracking System) algorithm.
No universally standardized ATS scoring algorithm exists publicly. Your score must be based on:
  - Resume structure and scannability (clear sections, consistent formatting)
  - Clarity and professional tone of language
  - Keyword strength (role-relevant technical terms and tools)
  - Quantified achievements (presence of numbers, percentages, business impact)
  - Completeness (essential sections present: experience, education, skills)
  - Formatting best practices (appropriate length, no red flags)

Parsed resume data:
---
{parsed_str}
---
{jd_section}
Return a JSON object with EXACTLY this structure (no extra keys, no markdown):
{{
  "overall_score": <integer 0-100>,
  "scoring_reasoning": "<2-3 sentences explaining this specific score, referencing actual resume content like specific companies, projects, or skills>",
  "industry_level": "<exactly one of: Entry-level | Needs Work | Almost Ready | Industry-Ready | Senior-Ready>",
  "industry_level_justification": "<2-3 sentences explaining this classification, referencing specific experience years, company names, or project complexity>",
  "whats_good": [
    "<specific observation tied to actual resume content — name the company/project/skill>",
    "<another specific positive — avoid generic praise like 'you have good experience'>"
  ],
  "needs_improvement": [
    {{
      "point": "<specific weakness tied to actual resume content>",
      "suggestion": "<concrete, actionable fix with an example if possible>"
    }}
  ],
  "overall_verdict": "<1-2 sentence honest summary of the resume's current state and biggest opportunity>"
}}

Rules:
- whats_good: 2-5 items. MUST reference specific content (company names, project names, specific skills, metrics). Never use generic phrases like "solid experience" alone.
- needs_improvement: 2-5 items. Be honest and constructive. If bullet points are vague, say so with an example.
- overall_score guidelines: fresh-grad with strong projects = 65-78; mid-level with good metrics = 78-88; senior with executive impact = 88-95; exceptional = 95+; weak/sparse = 40-60.
- Do NOT use the phrase 'ATS score' or claim any official algorithmic validation.
- Return ONLY the JSON object — no markdown fences, no explanation text.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — JOB DESCRIPTION PARSING
# ═══════════════════════════════════════════════════════════════════════════════

def jd_parse_prompt(raw_jd_text: str) -> str:
    """
    Prompt to extract structured requirements from a raw job description.

    Expected output (JSON):
      {
        "role_title": str,
        "company": str | null,
        "required_skills": [str],
        "preferred_skills": [str],
        "responsibilities": [str],
        "qualifications": [str],
        "seniority_level": "junior"|"mid"|"senior"|"lead"|"principal"|"unknown"
      }

    TODO (Phase: Resume Audit / Interview Prep):
      - Distinguish clearly between "required" vs "preferred" / "nice-to-have".
      - Normalise skill names (e.g., "JS" → "JavaScript").
      - Extract seniority signals from wording (years of experience, titles, etc.).
    """
    # TODO: Replace with real prompt implementation in Phase — Resume Audit
    raise NotImplementedError(
        "jd_parse_prompt is not yet implemented. "
        "Implement this during the Resume Audit / Interview Prep phase."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — INTERVIEW QUESTION GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def interview_question_generation_prompt(
    role: str,
    interview_type: str,
    difficulty: str,
    num_questions: int,
    resume_summary: dict | None = None,
    jd_summary: dict | None = None,
) -> str:
    """
    Prompt to generate a set of interview questions tailored to role and difficulty.

    Expected output (JSON array):
      [
        {
          "question_text": str,
          "difficulty": "easy"|"medium"|"hard",
          "category": str,   # one of the QuestionCategory enum values
          "time_limit_seconds": int | null   # only for "hard" questions
        },
        ...
      ]

    TODO (Phase: Interview):
      - Adapt questions to resume content if resume_summary is provided.
      - Focus on JD skill gaps if jd_summary is provided.
      - Ensure variety across categories (no 5 consecutive algo questions).
      - Hard questions must always have time_limit_seconds set.
      - Do NOT repeat the same question across calls for the same session.
    """
    # TODO: Replace with real prompt implementation in Phase — Interview
    raise NotImplementedError(
        "interview_question_generation_prompt is not yet implemented. "
        "Implement this during the Interview feature phase."
    )


def adaptive_next_question_prompt(
    role: str,
    previous_qa_pairs: list[dict],
    current_difficulty: str,
) -> str:
    """
    Prompt for adaptive mode: select the next question based on prior performance.

    previous_qa_pairs: [{"question": str, "answer": str, "score": float}, ...]

    Expected output (JSON):
      {
        "question_text": str,
        "difficulty": "easy"|"medium"|"hard",
        "category": str,
        "rationale": str,   # why this question was chosen (for internal logging)
        "time_limit_seconds": int | null
      }

    TODO (Phase: Interview — Adaptive Mode):
      - If last answer scored < 5/10, stay at same difficulty or step down.
      - If last answer scored ≥ 8/10, step up difficulty.
      - Never ask about a topic covered in the last 2 questions.
    """
    # TODO: Replace with real prompt implementation in Phase — Interview (Adaptive)
    raise NotImplementedError(
        "adaptive_next_question_prompt is not yet implemented. "
        "Implement this during the Interview Adaptive Mode phase."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — ANSWER EVALUATION
# ═══════════════════════════════════════════════════════════════════════════════

def answer_evaluation_prompt(
    question_text: str,
    answer_text: str,
    category: str,
    difficulty: str,
) -> str:
    """
    Prompt to evaluate a candidate's answer across 4 dimensions.

    Expected output (JSON):
      {
        "technical_score":    float (0–10),
        "relevance_score":    float (0–10),
        "completeness_score": float (0–10),
        "clarity_score":      float (0–10),
        "overall_score":      float (0–10),
        "feedback_text":      str,   # 2–4 sentence qualitative feedback
        "keywords_mentioned": [str], # domain keywords the candidate used correctly
        "missed_concepts":    [str]  # important concepts not covered
      }

    TODO (Phase: Interview):
      - Weight technical_score higher for TECHNICAL category questions.
      - Weight clarity_score higher for BEHAVIORAL category questions.
      - overall_score = weighted average, not arithmetic mean.
      - feedback_text must be constructive and actionable — never generic.
      - If answer_text is empty / "I don't know", return 0s with helpful feedback.
    """
    # TODO: Replace with real prompt implementation in Phase — Interview
    raise NotImplementedError(
        "answer_evaluation_prompt is not yet implemented. "
        "Implement this during the Interview feature phase."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — INTERVIEW REPORT GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def interview_report_prompt(
    role: str,
    interview_type: str,
    qa_pairs_with_scores: list[dict],
    overall_score: float,
) -> str:
    """
    Prompt to generate the final post-interview report.

    qa_pairs_with_scores: [
      {"question": str, "answer": str, "scores": dict, "feedback": str}, ...
    ]

    Expected output (JSON):
      {
        "strengths":  [{"point": str, "evidence": str}],
        "weaknesses": [{"point": str, "suggestion": str}],
        "recommendations_text": str,   # 3–5 paragraph narrative
        "study_topics": [str],          # specific topics to review
        "estimated_readiness": "not_ready"|"needs_work"|"almost_ready"|"ready"
      }

    TODO (Phase: Reports):
      - strengths must cite specific answers as evidence.
      - recommendations_text must include concrete next steps (books, topics, practice).
      - estimated_readiness should factor in overall_score + score variance.
    """
    # TODO: Replace with real prompt implementation in Phase — Reports
    raise NotImplementedError(
        "interview_report_prompt is not yet implemented. "
        "Implement this during the Reports feature phase."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — PREP QUESTION GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def prep_question_generation_prompt(
    role: str,
    topic: str | None = None,
    difficulty: str = "medium",
    num_questions: int = 5,
    resume_skills: list[str] | None = None,
) -> str:
    """
    Prompt to generate self-study Q&A pairs for the Prepare section.

    Expected output (JSON array of objects):
    [
      {
        "topic": "<specific topic, e.g. System Design, Database Indexing, React Hooks>",
        "difficulty": "easy"|"medium"|"hard",
        "question_text": "<clear, realistic technical or behavioral question>",
        "model_answer_text": "<detailed, structured reference answer with explanation, key takeaways, and example if applicable>"
      }
    ]
    """
    topic_clause = f"focusing on the topic '{topic}'" if topic else "covering relevant technical and conceptual domain topics"
    context_clause = f"\nCandidate Background Skills: {', '.join(resume_skills[:15])}\nTailor 2-3 questions to test these specific candidate skills." if resume_skills else ""

    return f"""You are a principal engineer and technical interview examiner.
Generate {num_questions} high-quality interview self-study questions with comprehensive model answers for the role of '{role}', {topic_clause}, at '{difficulty}' difficulty level.{context_clause}

Return a JSON array of EXACTLY {num_questions} objects with this structure:
[
  {{
    "topic": "<specific topic name>",
    "difficulty": "{difficulty.lower()}",
    "question_text": "<detailed question statement>",
    "model_answer_text": "<thorough, structured model answer formatted with clear paragraph breaks, bullet points for key steps, and example code or architectural trade-offs where applicable>"
  }}
]

Rules:
1. Each question must be realistic, practical, and commonly asked in technical interviews for a '{role}'.
2. model_answer_text MUST be concise yet complete (2 short paragraphs plus key bullet points / short code snippet). Keep under 300 words per answer so the full JSON array is complete.
3. Vary question types: design trade-offs, scenario debugging, core conceptual mechanics, and practical choices.
4. Difficulty must be exactly '{difficulty.lower()}'.
5. Return ONLY the raw JSON array — no markdown fences, no leading/trailing commentary.
"""


def jd_skill_extraction_prompt(raw_text: str) -> str:
    """
    Prompt for extracting required skills, preferred skills, responsibilities,
    role title, and qualifications from a raw job description text.
    """
    return f"""You are an expert technical recruiter and AI talent parser.
Analyze the following Job Description (JD) text and extract structured information.

Job Description Text:
\"\"\"
{raw_text[:4000]}
\"\"\"

Return a JSON object matching this exact schema:
{{
  "role_title": "<Extracted role title, e.g. Senior Backend Engineer, or 'Software Engineer' if unspecified>",
  "company": "<Extracted company name or null if unspecified>",
  "required_skills": ["<Skill 1>", "<Skill 2>", "<Skill 3>"],
  "preferred_skills": ["<Skill A>", "<Skill B>"],
  "responsibilities": ["<Key responsibility 1>", "<Key responsibility 2>"],
  "qualifications": ["<Qualification 1>", "<Qualification 2>"],
  "summary": "<1-2 sentence executive summary of the job description>"
}}

Rules:
1. Extract REAL skills explicitly mentioned in the text (programming languages, frameworks, databases, cloud, tools, methodologies).
2. Do NOT invent or hallucinate skills not present or strongly implied in the text.
3. Return ONLY valid JSON.
"""


def answer_evaluation_prompt(
    role: str,
    question_text: str,
    answer_text: str,
    category: str = "Technical",
    difficulty: str = "Medium",
) -> str:
    """
    Constructs a structured evaluation prompt for scoring a candidate's live answer across 4 dimensions.
    """
    return f"""You are a principal technical interviewer evaluating a candidate's answer for the role of '{role}'.

Question Context:
- Category: {category}
- Difficulty Level: {difficulty}
- Question Text: "{question_text}"

Candidate's Submitted Answer:
"{answer_text}"

Evaluate the candidate's answer thoroughly across 4 dimensions on a scale of 0.0 to 10.0:
1. technical_score (0.0 - 10.0): Technical accuracy, correctness of concepts, domain mechanics.
2. relevance_score (0.0 - 10.0): Directness in addressing the exact question asked.
3. completeness_score (0.0 - 10.0): Depth of coverage, edge cases, trade-offs mentioned.
4. clarity_score (0.0 - 10.0): Communication clarity, logical structure, articulation.
5. overall_score (0.0 - 10.0): Your weighted aggregate score (Weigh technical accuracy 40% and relevance 30% highest).
6. feedback_text: Provide 2-4 sentences of specific, actionable feedback referencing exact points the candidate mentioned or omitted.

Return ONLY a JSON object matching this exact schema:
{{
  "technical_score": 8.5,
  "relevance_score": 9.0,
  "completeness_score": 7.5,
  "clarity_score": 8.0,
  "overall_score": 8.4,
  "feedback_text": "<Specific actionable feedback referencing candidate points>"
}}
"""


def interview_report_summary_prompt(
    role: str,
    interview_type: str,
    difficulty_mode: str,
    qa_summary_list: list[dict[str, Any]],
    avg_scores: dict[str, float],
) -> str:
    """
    Constructs a prompt for generating holistic post-interview strengths, weaknesses, and recommendations.
    """
    qa_formatted_lines = []
    for idx, item in enumerate(qa_summary_list, 1):
        qa_formatted_lines.append(
            f"Q{idx} [{item.get('category', 'Technical')} / {item.get('difficulty', 'Medium')}]: {item.get('question_text', '')}\n"
            f"   Candidate Answer: {item.get('answer_text', 'No response provided.')}\n"
            f"   Scores: Overall={item.get('overall_score', 0):.1f}, Tech={item.get('technical_score', 0):.1f}\n"
            f"   Feedback: {item.get('feedback_text', 'N/A')}\n"
        )
    qa_block = "\n".join(qa_formatted_lines)

    return f"""You are an executive engineering manager generating a post-interview performance evaluation report for a candidate interviewing for the role of '{role}'.

Interview Session Configuration:
- Format: {interview_type}
- Difficulty Mode: {difficulty_mode}
- Calculated Average Scores:
  - Technical Accuracy: {avg_scores.get('technical', 0.0):.1f} / 10
  - Relevance: {avg_scores.get('relevance', 0.0):.1f} / 10
  - Completeness / Depth: {avg_scores.get('completeness', 0.0):.1f} / 10
  - Clarity / Communication: {avg_scores.get('clarity', 0.0):.1f} / 10
  - Overall Performance: {avg_scores.get('overall', 0.0):.1f} / 10

Question & Answer Session Transcript:
{qa_block}

Generate a comprehensive, non-generic performance report grounded strictly in the actual Q&A transcript above.

Return ONLY a JSON object matching this exact schema:
{{
  "strengths": [
    "<Specific technical strength 1 with evidence from candidate answers>",
    "<Specific technical strength 2 with evidence from candidate answers>"
  ],
  "weaknesses": [
    "<Specific technical gap 1 with actionable improvement advice>",
    "<Specific technical gap 2 with actionable improvement advice>"
  ],
  "recommendations": "<Personalized, encouraging written study roadmap recommending specific technical concepts, topics, or system design trade-offs to study next.>",
  "executive_summary": "<2-3 sentence executive overview summarizing the candidate's interview readiness for a {role} position.>"
}}
"""
