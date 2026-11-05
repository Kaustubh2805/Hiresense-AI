"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, History as HistoryIcon } from "lucide-react";
import { AuthGuard } from "@/components/auth-guard";
import { Badge, EmptyState, PageHeader, ProgressBar, ProgressRing, Stat } from "@/components/ui";
import { apiFetch } from "@/lib/api";

type InterviewHistoryItem = {
  session_id: string;
  job_title: string;
  started_at: string | null;
  ended_at: string | null;
  duration_seconds: number | null;
  questions_answered: number;
  status: string;
  analysis_status: string | null;
  overall_score: number | null;
  domain_scores: Record<"answer" | "audio" | "nlp" | "video", number | null>;
  top_strength: string | null;
  top_weakness: string | null;
  overall_assessment: string | null;
};

const domains = [
  { key: "answer", label: "Answers" },
  { key: "audio", label: "Voice" },
  { key: "video", label: "Presence" },
  { key: "nlp", label: "Language" },
] as const;

function HistoryContent() {
  const [items, setItems] = useState<InterviewHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [languageAnalysisError, setLanguageAnalysisError] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<"newest" | "score">("newest");
  const recentAnalysisStarted = useRef(false);

  useEffect(() => {
    async function load() {
      try {
        const response = await apiFetch("/me/interviews", { cache: "no-store" });
        const payload = await response.json().catch(() => []);
        if (!response.ok) throw new Error(payload.detail || "Could not load past interviews.");
        setItems(payload);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Could not load interview history.");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, []);

  useEffect(() => {
    if (loading || recentAnalysisStarted.current) return;
    recentAnalysisStarted.current = true;

    const recentPendingSessions = items
      .filter((item) => item.status === "completed" && item.analysis_status === "pending")
      .slice(0, 3);

    async function refreshRecentLanguageAnalysis() {
      for (const item of recentPendingSessions) {
        try {
          setItems((current) => current.map((currentItem) => (
            currentItem.session_id === item.session_id
              ? { ...currentItem, analysis_status: "running" }
              : currentItem
          )));
          const response = await apiFetch(
            `/interviews/${item.session_id}/language-analysis`,
            { method: "POST" },
          );
          const result = await response.json().catch(() => ({}));
          if (!response.ok) {
            throw new Error(result.detail || "Could not evaluate language patterns.");
          }
          setItems((current) => current.map((currentItem) => (
            currentItem.session_id === item.session_id
              ? { ...currentItem, analysis_status: "completed" }
              : currentItem
          )));
        } catch (analysisError) {
          setItems((current) => current.map((currentItem) => (
            currentItem.session_id === item.session_id
              ? { ...currentItem, analysis_status: "failed" }
              : currentItem
          )));
          setLanguageAnalysisError(
            analysisError instanceof Error
              ? analysisError.message
              : "Could not evaluate language patterns for a recent interview.",
          );
        }
      }
    }

    void refreshRecentLanguageAnalysis();
  }, [items, loading]);

  const scored = items.map((item) => item.overall_score).filter((score): score is number => typeof score === "number");
  const bestScore = scored.length ? Math.max(...scored) : null;
  const averageScore = scored.length ? scored.reduce((sum, score) => sum + score, 0) / scored.length : null;
  const sortedItems = useMemo(() => {
    const sorted = [...items];
    if (sortOrder === "score") {
      return sorted.sort((first, second) => (second.overall_score ?? -1) - (first.overall_score ?? -1));
    }
    return sorted.sort((first, second) => {
      const firstDate = first.started_at ? new Date(first.started_at).getTime() : 0;
      const secondDate = second.started_at ? new Date(second.started_at).getTime() : 0;
      return secondDate - firstDate;
    });
  }, [items, sortOrder]);

  return (
    <main className="min-h-[calc(100svh-4rem)] px-4 py-8 text-zinc-100 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <PageHeader
          eyebrow="Your practice"
          title="Past interviews"
          description="See how your practice is adding up and revisit feedback from each session."
          action={
            <label className="flex items-center gap-2 text-xs font-medium text-zinc-400">
              Sort by
              <select value={sortOrder} onChange={(event) => setSortOrder(event.target.value as "newest" | "score")} className="rounded-xl border border-white/10 bg-surface-900 px-3 py-2.5 text-sm text-zinc-200">
                <option value="newest">Most recent</option>
                <option value="score">Highest score</option>
              </select>
            </label>
          }
        />

        {!loading && !error && items.length > 0 && (
          <section aria-label="Interview summary" className="mb-6 grid gap-3 sm:grid-cols-3">
            <Stat label="Practice sessions" value={String(items.length)} detail="Every attempt is a chance to improve." />
            <Stat label="Best overall" value={bestScore === null ? "—" : `${bestScore.toFixed(1)}/10`} />
            <Stat label="Average overall" value={averageScore === null ? "—" : `${averageScore.toFixed(1)}/10`} />
          </section>
        )}

        {loading && (
          <div className="space-y-4" aria-label="Loading past interviews">
            {[1, 2, 3].map((i) => (
              <div key={i} className="rounded-lg border border-slate-800 bg-[#101522] p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="skeleton h-10 w-10 rounded-md" />
                    <div className="space-y-1.5">
                      <div className="skeleton h-4 w-40 rounded" />
                      <div className="skeleton h-3 w-28 rounded" />
                    </div>
                  </div>
                  <div className="skeleton h-12 w-28 rounded-md" />
                </div>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {[1, 2, 3, 4].map((j) => (
                    <div key={j} className="skeleton h-14 rounded-md" />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
        {error && <p role="alert" className="rounded-md border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</p>}
        {languageAnalysisError && <p role="alert" className="rounded-md border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">{languageAnalysisError}</p>}
        {!loading && !error && items.length === 0 && (
          <EmptyState title="Your practice history starts here">
            <p className="text-slate-400">Complete a mock interview to see your scores, strengths, and progress.</p>
            <Link href="/interview" className="mt-5 inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-xs font-medium text-white hover:bg-blue-500">
              Take your first interview <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
          </EmptyState>
        )}

        <div className="space-y-4">
          {sortedItems.map((item) => {
            const statusLabel =
              item.analysis_status === "running" ? "Analyzing…"
                : item.analysis_status === "completed" ? "Completed"
                  : item.analysis_status === "failed" ? "Failed"
                    : item.status === "in_progress" ? "In progress"
                      : item.status === "abandoned" ? "Abandoned"
                        : "Not analyzed";
            const statusTone =
              item.analysis_status === "failed" ? "danger"
                : item.analysis_status === "completed" ? "success"
                  : "warning";
            return (
              <article key={item.session_id} className="rounded-lg border border-slate-800 bg-[#101522] p-5 sm:p-6 transition hover:border-slate-700">
                <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-center">
                  <div>
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="grid h-9 w-9 place-items-center rounded-md bg-blue-600/15 text-blue-400"><HistoryIcon className="h-4 w-4" /></span>
                      <h2 className="text-base font-semibold text-white">{item.job_title}</h2>
                      <Badge tone={statusTone}>{statusLabel}</Badge>
                    </div>
                    <p className="mt-2 text-xs text-slate-400">
                      {item.started_at ? new Date(item.started_at).toLocaleString() : "Date unavailable"}
                      {` · ${item.questions_answered} questions answered`}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 self-start rounded-md border border-slate-800 bg-[#0a0d14] px-3 py-2 sm:self-auto">
                    <ProgressRing value={item.overall_score} size={54} stroke={5} />
                    <span className="text-xs leading-tight text-slate-400">Overall<br />practice score</span>
                  </div>
                </div>

                <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {domains.map(({ key, label }) => {
                    const score = item.domain_scores?.[key] ?? null;
                    return (
                      <div key={key} className="rounded-md border border-slate-800 bg-[#0a0d14] px-3 py-2.5">
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-[11px] font-medium uppercase tracking-wider text-slate-400">{label}</p>
                          <p className="text-xs font-semibold text-slate-200">{score === null ? "—" : `${score.toFixed(1)}/10`}</p>
                        </div>
                        <ProgressBar className="mt-2" value={score} label={`${label} score`} />
                      </div>
                    );
                  })}
                </div>

                {item.overall_assessment && <p className="mt-4 text-xs leading-relaxed text-slate-300">{item.overall_assessment}</p>}
                <div className="mt-4 grid gap-3 text-xs sm:grid-cols-2">
                  <p className="rounded-md border border-emerald-500/20 bg-emerald-500/10 p-3 text-emerald-200"><span className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-emerald-300">Strength</span>{item.top_strength || "Not available yet"}</p>
                  <p className="rounded-md border border-amber-500/20 bg-amber-500/10 p-3 text-amber-200"><span className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-amber-300">Focus area</span>{item.top_weakness || "Not available yet"}</p>
                </div>
                {item.status === "completed" && (
                  <Link href={`/interviews/${item.session_id}/results`} className="mt-5 inline-flex items-center gap-1.5 rounded-md border border-blue-500/30 bg-blue-600/10 px-3.5 py-2 text-xs font-medium text-blue-300 transition hover:bg-blue-600/20">
                    View your feedback <ArrowUpRight className="h-3.5 w-3.5" />
                  </Link>
                )}
              </article>
            );
          })}
        </div>
      </div>
    </main>
  );
}

export default function HistoryPage() {
  return <AuthGuard><HistoryContent /></AuthGuard>;
}
