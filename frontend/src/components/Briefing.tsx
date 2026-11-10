import { originLabel } from "@/lib/format";
import type { SessionOut } from "@/lib/types";

export function BriefingAside({ s }: { s: SessionOut }) {
  const p = s.profile;
  return (
    <div className="font-serif text-[15px] leading-8">
      <p className="font-sans font-semibold">What we read in your resume</p>
      {p.headline && <p>{p.headline}</p>}
      <p className="mt-8 text-soft">
        Level: {p.seniority}. Hands-on ML: {p.ml_exposure}.
      </p>
      {p.technologies.length > 0 && (
        <>
          <p className="mt-8 font-sans font-semibold">Tools and technologies</p>
          <p>{p.technologies.slice(0, 14).join(", ")}</p>
        </>
      )}
      {p.skills.length > 0 && (
        <>
          <p className="mt-8 font-sans font-semibold">Skills</p>
          <p>{p.skills.slice(0, 10).join(", ")}</p>
        </>
      )}
      {p.projects.length > 0 && (
        <>
          <p className="mt-8 font-sans font-semibold">Projects</p>
          <ul>{p.projects.slice(0, 4).map((x) => <li key={x.name}>{x.name}</li>)}</ul>
        </>
      )}
    </div>
  );
}

export function Briefing({ s, onBegin, busy }: { s: SessionOut; onBegin: () => void; busy: boolean }) {
  return (
    <div>
      <h1 className="text-[44px] font-bold leading-[64px] tracking-tight">Your interview is planned.</h1>
      <p className="font-serif text-[18px] leading-8">
        We chose {s.total_questions} topics for the {s.role_label} role. You start at <b>{s.difficulty_label.toLowerCase()}</b> difficulty.
        Strong answers raise it; weak ones lower it and bring a follow-up on the gap.
        {s.mode === "practice"
          ? " This is practice mode, so you will see feedback after every answer."
          : " Scores and feedback appear in your report at the end."}
      </p>

      <ol className="mt-8">
        {s.plan.map((t) => (
          <li key={t.topic} className="mb-8">
            <p className="text-[17px] font-semibold leading-8">{t.topic}</p>
            <p className="text-[14px] leading-8 text-soft">{originLabel[t.origin]}</p>
            <p className="font-serif text-[16px] leading-8">{t.rationale}</p>
          </li>
        ))}
      </ol>

      <div className="flex h-16 items-center">
        <button type="button" className="btn" onClick={onBegin} disabled={busy}>
          Begin interview
        </button>
      </div>
    </div>
  );
}
