"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { Briefing, BriefingAside } from "@/components/Briefing";
import { FeedbackCard } from "@/components/FeedbackCard";
import { Marginalia } from "@/components/Marginalia";
import { PipelineLoader } from "@/components/PipelineLoader";
import { QuestionView } from "@/components/QuestionView";
import { SheetFrame } from "@/components/SheetFrame";
import { api, ApiError } from "@/lib/api";
import { LAST_SESSION_KEY } from "@/lib/format";
import type { AnswerOut, QuestionOut, SessionOut } from "@/lib/types";

type Phase = "loading" | "briefing" | "generating" | "answering" | "submitting" | "feedback" | "finishing" | "error";

export default function InterviewPage({ params }: { params: { id: string } }) {
  const { id } = params;
  const router = useRouter();
  const [session, setSession] = useState<SessionOut | null>(null);
  const [current, setCurrent] = useState<QuestionOut | null>(null);
  const [phase, setPhase] = useState<Phase>("loading");
  const [error, setError] = useState<string | null>(null);
  const [lastAnswer, setLastAnswer] = useState<AnswerOut | null>(null);
  const [finished, setFinished] = useState(false);
  const started = useRef(false);

  const retry = useRef<() => void>(() => location.reload());
  const fail = (e: unknown, again: () => void) => {
    setError(e instanceof ApiError ? e.message : "Something went wrong. Try again.");
    retry.current = again;
    setPhase("error");
  };

  const finish = useCallback(async () => {
    setPhase("finishing");
    try {
      await api.complete(id);
      localStorage.removeItem(LAST_SESSION_KEY);
      router.push(`/results/${id}`);
    } catch (e) { fail(e, () => void finish()); }
  }, [id, router]);

  const generate = useCallback(async () => {
    setPhase("generating");
    try {
      const q = await api.nextQuestion(id);
      setSession((s) => (s && !s.questions.some((x) => x.id === q.id) ? { ...s, questions: [...s.questions, q] } : s));
      setCurrent(q);
      setPhase("answering");
    } catch (e) { fail(e, () => void generate()); }
  }, [id]);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    (async () => {
      try {
        const s = await api.session(id);
        setSession(s);
        if (s.status === "completed") return router.replace(`/results/${id}`);
        const pending = s.questions.find((q) => !q.answer);
        if (pending) { setCurrent(pending); setPhase("answering"); }
        else if (s.questions.length === 0) setPhase("briefing");
        else if (s.answered >= s.total_questions) await finish();
        else await generate();
      } catch (e) { fail(e, () => location.reload()); }
    })();
  }, [id, router, finish, generate]);

  const submit = async (text: string, seconds: number) => {
    if (!current || !session) return;
    setPhase("submitting");
    try {
      const res = await api.submitAnswer(id, current.id, text, seconds);
      setSession({
        ...session,
        answered: res.answered_count,
        questions: session.questions.map((q) => (q.id === current.id ? { ...q, answer: res.answer } : q)),
      });
      setLastAnswer(res.answer);
      setFinished(res.finished);
      if (session.mode === "practice") return setPhase("feedback");
      if (res.finished) await finish();
      else await generate();
    } catch (e) { fail(e, () => setPhase("answering")); }
  };

  const next = async () => (finished ? finish() : generate());
  const endEarly = () => {
    if (window.confirm("End the interview now? Unanswered questions will not be scored.")) void finish();
  };

  if (!session) {
    return (
      <SheetFrame stage={2}>
        <div className="pt-8">
          {phase === "error" ? <ErrorNote message={error} onRetry={() => retry.current()} /> : <PipelineLoader title="Opening your interview" steps={["Loading your session"]} />}
        </div>
      </SheetFrame>
    );
  }

  const stage = phase === "briefing" ? 1 : 2;
  const aside = phase === "briefing" ? <BriefingAside s={session} /> : current ? <Marginalia q={current} /> : null;

  return (
    <SheetFrame stage={stage} aside={aside}>
      {phase === "briefing" && <Briefing s={session} busy={false} onBegin={generate} />}

      {phase === "generating" && (
        <div className="pt-8">
          <PipelineLoader
            title={session.questions.length === 0 ? "Writing your first question" : "Writing your next question"}
            steps={["Reading what you wrote", "Searching the textbook for the next topic", "Composing a question from what it found"]}
          />
        </div>
      )}

      {phase === "submitting" && (
        <div className="pt-8">
          <PipelineLoader title="Saving your answer" steps={["Recording your answer", "Checking it against the source passages"]} />
        </div>
      )}

      {phase === "finishing" && (
        <div className="pt-8">
          <PipelineLoader title="Preparing your report" steps={["Scoring every answer", "Comparing topics and difficulty", "Writing the summary"]} />
        </div>
      )}

      {(phase === "answering") && current && (
        <QuestionView
          key={current.id} question={current} index={current.order} total={session.total_questions}
          busy={false} onSubmit={submit} onEndEarly={endEarly}
        />
      )}

      {phase === "feedback" && (
        <FeedbackCard evaluation={lastAnswer?.evaluation ?? null} last={finished} busy={false} onNext={next} />
      )}

      {phase === "error" && <div className="pt-8"><ErrorNote message={error} onRetry={() => { setError(null); retry.current(); }} /></div>}
    </SheetFrame>
  );
}

function ErrorNote({ message, onRetry }: { message: string | null; onRetry: () => void }) {
  return (
    <div role="alert">
      <p className="text-[22px] font-semibold leading-8">That did not go through.</p>
      <p className="font-serif leading-8">{message}</p>
      <div className="mt-8 flex h-16 items-center">
        <button type="button" className="btn" onClick={onRetry}>Try again</button>
      </div>
    </div>
  );
}
