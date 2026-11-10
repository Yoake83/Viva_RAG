import { Header } from "./Header";

export function SheetFrame({
  stage, aside, children,
}: { stage: 0 | 1 | 2 | 3; aside?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="sheet sheet-margin">
      <Header stage={stage} />
      <div className="grid lg:grid-cols-[340px_1fr]">
        <aside className="px-6 pb-8 lg:pl-10 lg:pr-8">{aside}</aside>
        <main className="min-w-0 px-6 pb-16 lg:px-12">
          <div className="max-w-[700px]">{children}</div>
        </main>
      </div>
    </div>
  );
}
