"use client";

import Link from "next/link";
import { formatClock, originLabel, pages, qtypeLabel, scoreTone } from "@/lib/format";
import type { QuestionOut, Report, SessionOut } from "@/lib/types";

export function ResultsAside({ report }: { report: Report }) {
  const st = report.stats;
  return (
    <div className="font-serif text-[15px] leading-8">
      {report.study_map.length > 0 && (
        <>
          <p className="font-sans font-semibold">Where to read next</p>
          {report.study_map.map((m) => (
            <div key={`${m.source}-${m.section}`} className="mb-8">
              <p className="font-sans text-[14px] font-semibold leading-8">{m.section}</p>
              <p className="text-soft">{m.source}, {pages(m.page_start, m.page_end)}</p>
              <p>For: {m.topic}</p>
            </div>
          ))}
        </>
      )}
      <p className="font-sans font-semibold">How this was graded</p>
      <p>
        {st.answered} of {st.questions_asked} questions answered, graded against {st.chunks_used} passages from{" "}
        {st.sections_covered} book {st.sections_covered === 1 ? "section" : "sections"}.
      </p>
      <p>
        {st.resume_anchored} from the resume, {st.gap_probes} probing gaps, {st.follow_ups} {st.follow_ups === 1 ? "follow-up" : "follow-ups"}.
      </p>
      {st.avg_time_sec !== null && <p>Average time per answer: {formatClock(st.avg_time_sec)}.</p>}
      {st.ended_early && <p className="text-warn">The interview was ended early.</p>}
    </div>
  );
}

function CircledScore({ score }: { score: number }) {
  return (
    <div className="relative h-32 w-[220px] shrink-0" role="img" aria-label={`Overall score ${score} out of 100`}>
      <svg viewBox="0 0 220 128" className="circle-draw absolute inset-0 h-full w-full text-margin" fill="none" stroke="currentColor"
        strokeWidth="3.5" strokeLinecap="round">
        <path d="M18 70 C10 28 78 8 128 12 C186 16 214 52 192 88 C170 120 66 126 30 100 C12 86 12 56 52 34 C70 26 96 20 124 20" />
      </svg>
      <div className="absolute inset-0 flex items-baseline justify-center gap-1 pt-[34px]">
        <span className="text-[56px] font-extrabold leading-[64px] tabular-nums">{Math.round(score)}</span>
        <span className="text-[16px] text-soft">/100</span>
      </div>
    </div>
  );
}

function TopicBars({ rows }: { rows: Report["topic_scores"] }) {
  return (
    <div>
      {rows.map((r) => (
        <div key={r.topic} className="mb-8">
          <p className="flex justify-between gap-4 leading-8">
            <span className="font-semibold">{r.topic}</span>
            <span className="tabular-nums text-soft">{Math.round(r.score)}</span>
          </p>
          <div className="flex h-8 items-center">
            <div className="h-2 w-full bg-rule" role="img" aria-label={`${r.topic}: ${Math.round(r.score)} out of 100`}>
              <div className="h-full bg-ink" style={{ width: `${Math.max(2, r.score)}%` }} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function Trajectory({ points }: { points: Report["trajectory"] }) {
  if (points.length < 2) return null;
  const W = 640, H = 192, padX = 24;
  const x = (i: number) => padX + (i * (W - padX * 2)) / (points.length - 1);
  const y = (v: number) => H - 16 - (v / 10) * (H - 32);
  const diff = points.map((p, i) => `${i === 0 ? "M" : "L"}${x(i)} ${y(p.difficulty * 2)}`).join(" ");
  const score = points.map((p, i) => `${i === 0 ? "M" : "L"}${x(i)} ${y(p.score)}`).join(" ");
  return (
    <figure>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Score and difficulty by question">
        {[0, 2.5, 5, 7.5, 10].map((v) => (
          <line key={v} x1={padX} x2={W - padX} y1={y(v)} y2={y(v)} stroke="var(--rule)" strokeWidth="1" />
        ))}
        <path d={diff} fill="none" stroke="var(--ink)" strokeWidth="2" strokeDasharray="6 5" />
        <path d={score} fill="none" stroke="var(--margin)" strokeWidth="2.5" />
        {points.map((p, i) => (
          <g key={p.order}>
            <circle cx={x(i)} cy={y(p.score)} r="5" fill="var(--margin)" />
            <text x={x(i)} y={H - 2} textAnchor="middle" fontSize="12" fill="var(--ink-soft)">Q{p.order}</text>
          </g>
        ))}
      </svg>
      <figcaption className="leading-8 text-[14px] text-soft">
        Red line: score out of 10. Dashed line: difficulty, 1 to 5 (drawn at twice its value).
      </figcaption>
    </figure>
  );
}

function QA({ q }: { q: QuestionOut }) {
  const ev = q.answer?.evaluation;
  return (
    <details className="group border-b border-rule">
      <summary className="flex min-h-16 cursor-pointer list-none items-center justify-between gap-4 py-0 leading-8">
        <span>
          <span className="block font-semibold">{q.order + 1}. {q.topic}</span>
          <span className="block text-[14px] text-soft">
            {qtypeLabel[q.qtype] ?? q.qtype}, {q.difficulty_label.toLowerCase()}{q.is_follow_up ? ", follow-up" : ""}
          </span>
        </span>
        <span className={`text-[22px] font-bold tabular-nums ${ev ? scoreTone(ev.score) : "text-soft"}`}>
          {ev ? ev.score.toFixed(1) : "n/a"}
        </span>
      </summary>
      <div className="pb-8">
        <p className="mt-8 font-serif text-[18px] font-medium leading-8">{q.text}</p>
        <p className="mt-8 font-semibold">Your answer</p>
        <p className="whitespace-pre-wrap font-serif leading-8">{q.answer?.text}</p>
        {ev && (
          <>
            <p className="mt-8 font-semibold">Feedback</p>
            <p className="font-serif leading-8">{ev.feedback}</p>
            {ev.missed_points.length > 0 && (
              <>
                <p className="mt-8 font-semibold">A strong answer would also have covered</p>
                <ul className="list-disc pl-5 font-serif">{ev.missed_points.map((p) => <li key={p}>{p}</li>)}</ul>
              </>
            )}
          </>
        )}
        <p className="mt-8 font-semibold">How the question was written</p>
        <p className="font-serif leading-8">{q.rationale}</p>
        <p className="text-[14px] leading-8 text-soft">{originLabel[q.resume_signals.length ? "resume" : "role_core"]}.
          Searched: {q.retrieval.queries.map((x) => `"${x}"`).join(", ")}</p>
        {q.sources.filter((s) => s.used).map((s) => (
          <p key={s.chunk_id} className="text-[14px] leading-8 text-soft">
            Drew on {s.section}, {s.source}, {pages(s.page_start, s.page_end)}
          </p>
        ))}
      </div>
    </details>
  );
}

export function ResultsView({ session, report }: { session: SessionOut; report: Report }) {
  const download = () => {
    const blob = new Blob([JSON.stringify({ session, report }, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `viva-${session.id}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  };
  const who = session.candidate_name ? `${session.candidate_name}, ` : "";

  return (
    <div>
      <p className="h-8 text-[15px] text-soft">{who}{session.role_label}</p>
      <div className="flex flex-wrap items-center gap-8">
        <CircledScore score={report.overall_score} />
        <div className="min-w-[220px] flex-1">
          <h1 className="text-[40px] font-bold leading-[64px] tracking-tight">{report.band}</h1>
          <p className="font-serif text-[18px] leading-8">{report.recommendation}</p>
        </div>
      </div>

      <p className="mt-8 font-serif text-[18px] leading-8">{report.summary}</p>

      {(report.strengths.length > 0 || report.gaps.length > 0) && (
        <div className="mt-8 grid gap-x-10 sm:grid-cols-2">
          <div>
            <h2 className="font-semibold leading-8">What went well</h2>
            <ul className="list-disc pl-5 font-serif leading-8">{report.strengths.map((s) => <li key={s}>{s}</li>)}</ul>
          </div>
          <div>
            <h2 className="mt-8 font-semibold leading-8 sm:mt-0">What to work on</h2>
            <ul className="list-disc pl-5 font-serif leading-8">{report.gaps.map((s) => <li key={s}>{s}</li>)}</ul>
          </div>
        </div>
      )}

      {report.next_steps.length > 0 && (
        <>
          <h2 className="mt-8 font-semibold leading-8">Next steps</h2>
          <ul className="list-disc pl-5 font-serif leading-8">{report.next_steps.map((s) => <li key={s}>{s}</li>)}</ul>
        </>
      )}

      <h2 className="mt-8 text-[22px] font-bold leading-8">Score by topic</h2>
      <div className="mt-8"><TopicBars rows={report.topic_scores} /></div>

      {report.trajectory.length > 1 && (
        <>
          <h2 className="text-[22px] font-bold leading-8">How difficulty adapted</h2>
          <div className="mt-8"><Trajectory points={report.trajectory} /></div>
        </>
      )}

      <h2 className="mt-8 text-[22px] font-bold leading-8">Every question and answer</h2>
      <div className="mt-8 border-t border-rule">
        {session.questions.map((q) => <QA key={q.id} q={q} />)}
      </div>

      <div className="no-print mt-8 flex h-16 flex-wrap items-center gap-4">
        <button type="button" className="btn" onClick={download}>Download as JSON</button>
        <button type="button" className="btn btn-quiet" onClick={() => window.print()}>Print</button>
        <Link href="/" className="link-quiet">Start a new interview</Link>
      </div>
    </div>
  );
}
