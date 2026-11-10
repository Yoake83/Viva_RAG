import type {
  AnswerSubmitOut, KnowledgeStatus, Mode, QuestionOut, Report, RoleInfo, SessionOut,
} from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public code: string, message: string, public status: number) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api${path}`, { ...init, cache: "no-store" });
  } catch {
    throw new ApiError("network", `Can't reach the API at ${API_URL}. Start the backend and try again.`, 0);
  }
  if (!res.ok) {
    let code = "error";
    let message = `Request failed (${res.status}).`;
    try {
      const body = await res.json();
      code = body?.error?.code ?? code;
      message = body?.error?.message ?? message;
    } catch { /* non-JSON error body */ }
    throw new ApiError(code, message, res.status);
  }
  return res.json() as Promise<T>;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  roles: () => request<RoleInfo[]>("/roles"),
  knowledge: () => request<KnowledgeStatus>("/knowledge/status"),
  createSession: (input: { role: string; mode: Mode; name?: string; file?: File | null; text?: string }) => {
    const form = new FormData();
    form.set("role", input.role);
    form.set("mode", input.mode);
    if (input.name) form.set("candidate_name", input.name);
    if (input.file) form.set("resume", input.file);
    else if (input.text) form.set("resume_text", input.text);
    return request<SessionOut>("/sessions", { method: "POST", body: form });
  },
  session: (id: string) => request<SessionOut>(`/sessions/${id}`),
  nextQuestion: (id: string) => request<QuestionOut>(`/sessions/${id}/questions/next`, { method: "POST" }),
  submitAnswer: (id: string, questionId: string, answer: string, seconds: number) =>
    request<AnswerSubmitOut>(`/sessions/${id}/answers`, json({ question_id: questionId, answer, time_taken_sec: seconds })),
  complete: (id: string) => request<Report>(`/sessions/${id}/complete`, { method: "POST" }),
  report: (id: string) => request<Report>(`/sessions/${id}/report`),
};
