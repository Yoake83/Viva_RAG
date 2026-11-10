import Link from "next/link";

const STAGES = ["Resume", "Briefing", "Interview", "Report"];

export function Header({ stage }: { stage: 0 | 1 | 2 | 3 }) {
  return (
    <header className="flex h-16 items-center justify-between px-6 lg:px-10">
      <Link href="/" className="text-[28px] font-extrabold leading-8 tracking-tight">
        Viva
      </Link>
      <ol className="flex gap-5 text-[15px] leading-8" aria-label="Progress">
        {STAGES.map((label, i) => (
          <li
            key={label}
            aria-current={i === stage ? "step" : undefined}
            className={
              i === stage
                ? "font-semibold underline decoration-margin decoration-2 underline-offset-[6px]"
                : i < stage
                ? "text-soft"
                : "hidden text-soft/60 sm:block"
            }
          >
            {label}
          </li>
        ))}
      </ol>
    </header>
  );
}
