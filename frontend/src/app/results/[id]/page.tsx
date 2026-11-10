"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { PipelineLoader } from "@/components/PipelineLoader";
import { ResultsView, ResultsAside } from "@/components/ResultsView";
import { SheetFrame } from "@/components/SheetFrame";
import { api, ApiError } from "@/lib/api";
import type { Report, SessionOut } from "@/lib/types";

export default function ResultsPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [session, setSession] = useState<SessionOut | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const s = await api.session(params.id);
        if (s.status !== "completed") return router.replace(`/interview/${params.id}`);
        setSession(s);
        setReport(await api.report(params.id));
      } catch (e) { setError(e instanceof ApiError ? e.message : "Could not load the report."); }
    })();
  }, [params.id, router]);

  if (!session || !report) {
    return (
      <SheetFrame stage={3}>
        <div className="pt-8">
          {error ? <p role="alert" className="font-semibold leading-8 text-margin">{error}</p> : <PipelineLoader title="Loading your report" steps={["Fetching the session"]} />}
        </div>
      </SheetFrame>
    );
  }
  return (
    <SheetFrame stage={3} aside={<ResultsAside report={report} />}>
      <ResultsView session={session} report={report} />
    </SheetFrame>
  );
}
