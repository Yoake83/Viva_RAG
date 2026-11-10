"use client";

import { useEffect, useState } from "react";
import { pages } from "@/lib/format";
import type { QuestionOut } from "@/lib/types";

const quality: Record<string, string> = {
  high: "Strong matches found.",
  medium: "Few strong matches; used the best available.",
  low: "Weak matches; used the closest passages.",
};

export function Marginalia({ q }: { q: QuestionOut }) {
  const [open, setOpen] = useState(true);
  useEffect(() => {
    if (window.innerWidth < 1024) setOpen(false);
  }, []);

  return (
    <section aria-label="How this question was written">
      <button type="button" className="link-quiet h-8 text-[15px] leading-8" aria-expanded={open} onClick={() => setOpen(!open)}>
        {open ? "Hide how this was written" : "Show how this was written"}
      </button>

      {open && (
        <div className="font-serif text-[15px] leading-8" key={q.id}>
          <p className="mt-8 font-sans font-semibold">Why this question</p>
          <p>{q.rationale || "Chosen from the interview plan for this role."}</p>

          {q.resume_signals.length > 0 && (
            <>
              <p className="mt-8 font-sans font-semibold">Taken from your resume</p>
              <ul>
                {q.resume_signals.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </>
          )}

          <p className="mt-8 font-sans font-semibold">What the books were searched for</p>
          <ul className="italic">
            {q.retrieval.queries.map((query) => (
              <li key={query}>&ldquo;{query}&rdquo;</li>
            ))}
          </ul>
          <p className="text-soft">{quality[q.retrieval.quality] ?? ""}</p>

          <p className="mt-8 font-sans font-semibold">Passages it drew on</p>
          {q.sources.map((s) => (
            <div key={s.chunk_id} className="mb-8">
              <p className="font-sans text-[14px] font-semibold leading-8">
                {s.section}
              </p>
              <p className="flex items-center gap-2 font-sans text-[13px] leading-8 text-soft">
                <span>{s.source}, {pages(s.page_start, s.page_end)}</span>
                <span aria-label={`Match ${Math.round(s.score * 100)} percent`} className="inline-block h-1.5 w-10 bg-rule">
                  <span className="block h-full bg-ink" style={{ width: `${Math.max(6, Math.min(100, s.score * 100))}%` }} />
                </span>
              </p>
              {s.used ? (
                <p>
                  <mark className="hl hl-sweep bg-transparent text-inherit [box-decoration-break:clone]">{s.excerpt}</mark>
                </p>
              ) : (
                <p className="text-soft">Retrieved, not used.</p>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
