export type Mode = "interview" | "practice";

export interface RoleInfo { id: string; label: string; tagline: string; description: string }
export interface KnowledgeStatus { ready: boolean; total_chunks: number; roles: Record<string, number> }

export interface ResumeProject { name: string; summary: string; technologies: string[] }
export interface ResumeProfile {
  candidate_name: string | null;
  headline: string;
  seniority: "student" | "junior" | "mid" | "senior";
  years_experience: number;
  ml_exposure: "none" | "basic" | "moderate" | "strong";
  skills: string[];
  technologies: string[];
  domains: string[];
  projects: ResumeProject[];
  education: string[];
}
export interface TopicPlan {
  topic: string;
  origin: "resume" | "resume_gap" | "role_core";
  rationale: string;
  resume_signals: string[];
  queries: string[];
  question_type: string;
}

export interface Source {
  chunk_id: string; source: string; section: string;
  page_start: number; page_end: number; score: number; excerpt: string; used: boolean;
}
export interface Evaluation {
  score: number; depth: "shallow" | "adequate" | "deep";
  covered_points: string[]; missed_points: string[]; strengths: string[]; gaps: string[]; feedback: string;
}
export interface AnswerOut {
  text: string; time_taken_sec: number | null; submitted_at: string;
  eval_status: "pending" | "done"; evaluation: Evaluation | null;
}
export interface QuestionOut {
  id: string; order: number; topic: string; qtype: string; difficulty: number; difficulty_label: string;
  text: string; rationale: string; is_follow_up: boolean; resume_signals: string[];
  retrieval: { queries: string[]; quality: string; candidates: number; threshold: number };
  sources: Source[]; rubric: string[] | null; answer: AnswerOut | null;
}
export interface SessionOut {
  id: string; role: string; role_label: string; mode: Mode; status: "created" | "in_progress" | "completed";
  candidate_name: string | null; profile: ResumeProfile; plan: TopicPlan[];
  total_questions: number; answered: number; current_difficulty: number; difficulty_label: string;
  created_at: string; completed_at: string | null; questions: QuestionOut[];
}
export interface AnswerSubmitOut {
  question_id: string; answer: AnswerOut; answered_count: number; total_questions: number; finished: boolean;
}
export interface Report {
  overall_score: number; band: string; recommendation: string; summary: string;
  strengths: string[]; gaps: string[]; next_steps: string[];
  topic_scores: { topic: string; score: number; questions: number }[];
  trajectory: { order: number; difficulty: number; score: number }[];
  study_map: { topic: string; source: string; section: string; page_start: number; page_end: number }[];
  stats: {
    questions_asked: number; answered: number; avg_time_sec: number | null; chunks_used: number;
    sections_covered: number; grounding: Record<string, number>; resume_anchored: number;
    gap_probes: number; follow_ups: number; ended_early: boolean;
  };
  generated_at: string;
}
