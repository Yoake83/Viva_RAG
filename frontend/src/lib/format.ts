export const formatClock = (total: number) => {
  const m = Math.floor(total / 60).toString().padStart(2, "0");
  const s = (total % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
};

export const qtypeLabel: Record<string, string> = {
  conceptual: "Concept",
  applied_scenario: "Scenario",
  project_deep_dive: "Your project",
  tradeoff: "Trade-off",
  debugging: "Diagnosis",
};

export const originLabel: Record<string, string> = {
  resume: "From your resume",
  resume_gap: "Probing a gap",
  role_core: "Core to the role",
};

export const pages = (a: number, b: number) => (a === b ? `p. ${a}` : `pp. ${a}-${b}`);

export const scoreTone = (score: number) => (score >= 7 ? "text-ok" : score >= 5 ? "text-warn" : "text-margin");

export const LAST_SESSION_KEY = "viva:last-session";
