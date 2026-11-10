"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { PipelineLoader } from "@/components/PipelineLoader";
import { SheetFrame } from "@/components/SheetFrame";
import { api, ApiError } from "@/lib/api";
import { LAST_SESSION_KEY } from "@/lib/format";
import type { KnowledgeStatus, Mode, RoleInfo } from "@/lib/types";

const MAX_MB = 5;

export default function CoverPage() {
  const router = useRouter();
  const [roles, setRoles] = useState<RoleInfo[]>([]);
  const [kb, setKb] = useState<KnowledgeStatus | null>(null);
  const [role, setRole] = useState("");
  const [mode, setMode] = useState<Mode>("interview");
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [paste, setPaste] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastId, setLastId] = useState<string | null>(null);

  useEffect(() => {
    setLastId(localStorage.getItem(LAST_SESSION_KEY));
    Promise.all([api.roles(), api.knowledge()])
      .then(([r, k]) => { setRoles(r); setKb(k); setRole(r[0]?.id ?? ""); })
      .catch((e: unknown) => setError(e instanceof ApiError ? e.message : "Could not load the page data."));
  }, []);

  const roleChunks = kb?.roles[role] ?? 0;
  const kbEmpty = kb !== null && roleChunks === 0;

  const pick = (f: File | null) => {
    setError(null);
    if (!f) return setFile(null);
    if (!/\.(pdf|txt|md)$/i.test(f.name)) return setError("Upload a PDF or a plain text file.");
    if (f.size > MAX_MB * 1024 * 1024) return setError(`That file is over ${MAX_MB} MB. Export a smaller PDF.`);
    setFile(f);
  };

  const ready = !!role && (paste ? text.trim().length >= 200 : !!file) && !kbEmpty;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ready || busy) return;
    setBusy(true);
    setError(null);
    try {
      const s = await api.createSession({ role, mode, name: name.trim(), file: paste ? null : file, text: paste ? text : undefined });
      localStorage.setItem(LAST_SESSION_KEY, s.id);
      router.push(`/interview/${s.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
      setBusy(false);
    }
  };

  const aside = (
    <div className="font-serif text-[15px] leading-8">
      <p className="font-sans font-semibold">How the interview is made</p>
      <p>
        Your resume sets <span className="hl">the topics and how hard the first question is.</span>
      </p>
      <p className="mt-8">
        Each question is written from passages <span className="hl">retrieved out of the textbook for your role.</span> You can
        see exactly which pages.
      </p>
      <p className="mt-8">
        Your answers are graded against <span className="hl">those same passages,</span> and the next question adapts.
      </p>
      {lastId && (
        <p className="mt-8 font-sans text-[15px]">
          <Link className="link-quiet" href={`/interview/${lastId}`}>Continue your last interview</Link>
        </p>
      )}
    </div>
  );

  return (
    <SheetFrame stage={0} aside={aside}>
      {busy ? (
        <div className="pt-8">
          <PipelineLoader
            title="Reading your resume"
            steps={["Extracting the text", "Finding your skills, projects and level", "Choosing topics for this role"]}
          />
        </div>
      ) : (
        <form onSubmit={submit} noValidate>
          <h1 className="text-[52px] font-extrabold leading-[64px] tracking-tight">Your resume decides the questions.</h1>
          <p className="mt-0 font-serif text-[18px] leading-8">
            Upload it, choose a role, and Viva sits you through an oral exam written from the textbook. No two candidates
            get the same one.
          </p>

          <div className="mt-8">
            <label htmlFor="name" className="block text-[15px] font-semibold leading-8">Name (optional)</label>
            <input id="name" className="field-line" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} autoComplete="name" />
          </div>

          <fieldset className="mt-8">
            <legend className="text-[15px] font-semibold leading-8">Role you are sitting for</legend>
            {roles.map((r) => (
              <label key={r.id} className="flex min-h-16 cursor-pointer items-start gap-3 py-0">
                <input type="radio" name="role" className="sr-only" checked={role === r.id} onChange={() => setRole(r.id)} />
                <span aria-hidden className={`mt-[6px] block h-5 w-5 shrink-0 rounded-full border-2 ${role === r.id ? "border-margin bg-margin" : "border-ink"}`} />
                <span>
                  <span className={`block text-[17px] font-semibold leading-8 ${role === r.id ? "hl" : ""}`}>{r.label}</span>
                  <span className="block text-[15px] leading-8 text-soft">{r.tagline}</span>
                </span>
              </label>
            ))}
          </fieldset>

          <div className="mt-8">
            <div className="flex h-8 items-center justify-between">
              <span className="text-[15px] font-semibold">Resume</span>
              <button type="button" className="link-quiet text-[14px]" onClick={() => { setPaste(!paste); setError(null); }}>
                {paste ? "Upload a file instead" : "Paste text instead"}
              </button>
            </div>
            {paste ? (
              <>
                <label htmlFor="resume-text" className="sr-only">Resume text</label>
                <textarea id="resume-text" className="lined" style={{ height: 256 }} value={text} onChange={(e) => setText(e.target.value)}
                  placeholder="Paste your resume text here." />
                <p className="h-8 text-[14px] text-soft">{text.trim().length} characters. At least 200 are needed.</p>
              </>
            ) : (
              <label
                className={`flex h-32 cursor-pointer flex-col items-center justify-center border-2 border-dashed text-center ${dragging ? "border-margin bg-hl/30" : "border-ink bg-paper"}`}
                onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={(e) => { e.preventDefault(); setDragging(false); pick(e.dataTransfer.files?.[0] ?? null); }}
              >
                <input type="file" accept=".pdf,.txt,.md" className="sr-only" onChange={(e) => pick(e.target.files?.[0] ?? null)} />
                {file ? (
                  <>
                    <span className="font-semibold leading-8">{file.name}</span>
                    <span className="text-[14px] leading-8 text-soft">{(file.size / 1024).toFixed(0)} KB. Choose another to replace it.</span>
                  </>
                ) : (
                  <>
                    <span className="font-semibold leading-8">Drop your resume here</span>
                    <span className="text-[14px] leading-8 text-soft">or choose a PDF or text file, up to {MAX_MB} MB</span>
                  </>
                )}
              </label>
            )}
          </div>

          <fieldset className="mt-8">
            <legend className="text-[15px] font-semibold leading-8">Format</legend>
            {([
              ["interview", "Interview", "Scores and feedback appear in your report at the end."],
              ["practice", "Practice", "See feedback and the model answer points after every question."],
            ] as [Mode, string, string][]).map(([id, label, hint]) => (
              <label key={id} className="flex min-h-16 cursor-pointer items-start gap-3">
                <input type="radio" name="mode" className="sr-only" checked={mode === id} onChange={() => setMode(id)} />
                <span aria-hidden className={`mt-[6px] block h-5 w-5 shrink-0 rounded-full border-2 ${mode === id ? "border-margin bg-margin" : "border-ink"}`} />
                <span>
                  <span className={`block text-[17px] font-semibold leading-8 ${mode === id ? "hl" : ""}`}>{label}</span>
                  <span className="block text-[15px] leading-8 text-soft">{hint}</span>
                </span>
              </label>
            ))}
          </fieldset>

          {kbEmpty && (
            <p className="mt-8 leading-8 text-warn" role="status">
              No book is ingested for this role yet. In the backend folder run <code className="font-semibold">python -m app.cli ingest</code>, then reload.
            </p>
          )}
          {error && <p role="alert" className="mt-8 font-semibold leading-8 text-margin">{error}</p>}

          <div className="mt-8 flex h-16 items-center">
            <button type="submit" className="btn" disabled={!ready}>Begin interview</button>
          </div>
        </form>
      )}
    </SheetFrame>
  );
}
