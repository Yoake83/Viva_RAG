"use client";

import { useEffect, useState } from "react";

export function PipelineLoader({ title, steps }: { title: string; steps: string[] }) {
  const [active, setActive] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setActive((v) => Math.min(v + 1, steps.length - 1)), 2400);
    return () => clearInterval(t);
  }, [steps.length]);

  return (
    <div role="status" aria-live="polite">
      <p className="font-serif text-[22px] font-medium leading-8">{title}</p>
      <ul className="mt-8">
        {steps.map((step, i) => (
          <li key={step} className={`flex h-8 items-center gap-3 text-[16px] ${i > active ? "text-soft/50" : ""}`}>
            <span aria-hidden className="inline-flex h-4 w-4 items-center justify-center">
              {i < active ? (
                <svg viewBox="0 0 16 16" className="h-4 w-4 text-ok" fill="none" stroke="currentColor" strokeWidth="2.2">
                  <path d="M2 8.5l4 4 8-9" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              ) : i === active ? (
                <span className="pen-blink block h-4 w-[3px] bg-margin" />
              ) : null}
            </span>
            {step}
          </li>
        ))}
      </ul>
    </div>
  );
}
