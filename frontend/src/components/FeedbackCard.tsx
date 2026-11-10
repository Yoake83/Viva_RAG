import { scoreTone } from "@/lib/format";
import type { Evaluation } from "@/lib/types";

export function FeedbackCard({
  evaluation, last, onNext, busy,
}: { evaluation: Evaluation | null; last: boolean; onNext: () => void; busy: boolean }) {
  return (
    <section aria-label="Feedback on your answer">
      {evaluation ? (
        <>
          <p className="flex items-baseline gap-3 leading-[64px]">
            <span className={`text-[56px] font-extrabold tabular-nums ${scoreTone(evaluation.score)}`}>
              {evaluation.score.toFixed(1)}
            </span>
            <span className="text-[18px] text-soft">out of 10, {evaluation.depth} answer</span>
          </p>
          <p className="font-serif text-[18px] leading-8">{evaluation.feedback}</p>
          {evaluation.covered_points.length > 0 && (
            <>
              <p className="mt-8 font-semibold">You covered</p>
              <ul className="list-disc pl-5 font-serif">{evaluation.covered_points.map((p) => <li key={p}>{p}</li>)}</ul>
            </>
          )}
          {evaluation.missed_points.length > 0 && (
            <>
              <p className="mt-8 font-semibold">Still missing</p>
              <ul className="list-disc pl-5 font-serif">{evaluation.missed_points.map((p) => <li key={p}>{p}</li>)}</ul>
            </>
          )}
        </>
      ) : (
        <p className="font-serif text-[18px] leading-8">
          Your answer is saved. The language model could not grade it right now, so it will be graded when you finish.
        </p>
      )}
      <div className="mt-8 flex h-16 items-center">
        <button type="button" className="btn" disabled={busy} onClick={onNext}>
          {last ? "See my report" : "Next question"}
        </button>
      </div>
    </section>
  );
}
