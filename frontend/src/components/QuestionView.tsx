"use client";

import { useEffect, useRef, useState } from "react";
import { formatClock, qtypeLabel } from "@/lib/format";
import type { QuestionOut } from "@/lib/types";

const LINE = 32;

export function QuestionView({
  question, index, total, busy, onSubmit, onEndEarly,
}: {
  question: QuestionOut; index: number; total: number; busy: boolean;
  onSubmit: (text: string, seconds: number) => void; onEndEarly: () => void;
}) {
  const draftKey = `viva:draft:${question.id}`;
  const [text, setText] = useState("");
  const [seconds, setSeconds] = useState(0);
  const area = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setText(localStorage.getItem(draftKey) ?? "");
    setSeconds(0);
    const t = setInterval(() => setSeconds((s) => s + 1), 1000);
    area.current?.focus();
    return () => clearInterval(t);
  }, [draftKey]);

  useEffect(() => {
    const el = area.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.max(LINE * 10, Math.ceil(el.scrollHeight / LINE) * LINE)}px`;
  }, [text]);

  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  const submit = (value: string) => {
    if (busy || !value.trim()) return;
    localStorage.removeItem(draftKey);
    onSubmit(value, seconds);
  };

  return (
    <article>
      <div className="flex h-8 items-center justify-between text-[15px] text-soft">
        <span>
          Question {index + 1} of {total}
          {question.is_follow_up ? ", follow-up" : ""}
        </span>
        <span className="tabular-nums" aria-label="Time on this question">{formatClock(seconds)}</span>
      </div>
      <p className="text-[16px] font-semibold leading-8">{question.topic}</p>
      <p className="flex h-8 items-center gap-3 text-[15px] text-soft">
        <span>{qtypeLabel[question.qtype] ?? question.qtype}</span>
        <span className="flex items-center gap-1" role="img" aria-label={`Difficulty ${question.difficulty} of 5, ${question.difficulty_label}`}>
          {[1, 2, 3, 4, 5].map((n) => (
            <span key={n} className={`block h-2.5 w-2.5 ${n <= question.difficulty ? "bg-ink" : "bg-rule"}`} />
          ))}
        </span>
        <span>{question.difficulty_label}</span>
      </p>

      <h2 key={question.id} className="write mt-8 font-serif text-[22px] font-medium leading-8">
        {question.text}
      </h2>

      <label htmlFor="answer" className="sr-only">Your answer</label>
      <textarea
        id="answer" ref={area} className="lined mt-8" style={{ height: LINE * 10 }} value={text} disabled={busy}
        placeholder="Write your answer here. Aim for a few clear sentences."
        onChange={(e) => { setText(e.target.value); localStorage.setItem(draftKey, e.target.value); }}
        onKeyDown={(e) => { if ((e.metaKey || e.ctrlKey) && e.key === "Enter") submit(text); }}
      />
      <div className="flex h-8 items-center justify-between text-[14px] text-soft">
        <span>{words} {words === 1 ? "word" : "words"}</span>
        <span>Ctrl or Cmd + Enter to submit</span>
      </div>

      <div className="mt-8 flex h-16 items-center gap-4">
        <button type="button" className="btn" disabled={busy || words === 0} onClick={() => submit(text)}>
          Submit answer
        </button>
        <button type="button" className="btn btn-quiet" disabled={busy} onClick={() => submit("[Passed]")}>
          Pass on this one
        </button>
      </div>
      <p className="h-8 text-[14px]">
        <button type="button" className="link-quiet" disabled={busy} onClick={onEndEarly}>
          End the interview and see my report
        </button>
      </p>
    </article>
  );
}
