

"use client";

import { useEffect, useId, useMemo, useState, type ReactNode } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { AuthGuard } from "@/components/auth-guard";
import { Badge, ProgressRing, Tabs } from "@/components/ui";
import { apiFetch } from "@/lib/api";
import {
  Download,
  AlertTriangle,
  TrendingUp,
  PieChart as PieChartIcon,
  Video,
  Mic,
  BookOpen,
  Award,
  Sparkles,
  ChevronDown,
  ChevronUp,
  FileText,
  Check,
  Loader2,
  Info,
  ArrowRight,
  ShieldCheck,
  Brain,
  Volume2,
  Eye,
  UserCheck,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Evaluation = Record<string, unknown> | null;

type SessionQuestion = {
  id: string;
  question_order: number;
  question_text: string;
  source: string;
  transcript_text: string | null;
  transcript_source?: "whisper" | "browser" | null;
  transcript_confidence?: number | null;
  transcript_languages?: string[];
  time_taken_seconds: number | null;
  answer_evaluation: Evaluation;
  audio_evaluation: Evaluation;
  nlp_evaluation: Evaluation;
  video_evaluation: Evaluation;
};

type FactorItem = {
  key?: string;
  name: string;
  percentage: number;
  weight?: number;
  earned?: number | null;
  score: number | null;
  basis: string;
  measured?: { value: number; unit: string } | null;
};

type DomainBreakdown = {
  id: string;
  label: string;
  percentage: number;
  weight?: number;
  earned?: number;
  score: number | null;
  color: string;
  citation?: string;
  reasoning?: string;
  factors: FactorItem[];
};

type BenchmarkItem = {
  domain: string;
  key: string;
  name: string;
  score: number;
  ideal_min: number;
  ideal_max: number;
  weak_below?: number;
  strong_from?: number;
  paper: string;
  unit: string;
  extra_stat?: string;
  category: "Strength" | "Meets expectation" | "Weakness";
  reason: string;
  what_happened?: string;
  why_it_matters?: string;
  what_to_do_next?: string;
  reasoning_source?: "llm" | "template_fallback";
};

type StageBehaviorItem = {
  stage: string;
  stage_title: string;
  available: boolean;
  question_id: string | null;
  question_number: number | null;
  question_text: string;
  answer_excerpt: string;
  score: number | null;
  presence_status: string;
  short_reason: string;
  citation?: string;
  what_happened?: string;
  why_it_matters?: string;
  what_to_do_next?: string;
  reasoning_source?: "llm" | "template_fallback";
  followup_count: number;
};

type PillarImprovement = {
  pillar: string;
  score: number | null;
  citation?: string;
  focus: string;
  how_to: string[];
  what_happened?: string;
  why_it_matters?: string;
  reasoning_source?: "llm" | "template_fallback";
};

type ChartFactor = {
  key: string;
  name: string;
  score: number;
  weak_below: number;
  strong_from: number;
  classification: "strength" | "developing" | "weakness";
  measured: { value: number; unit: string } | null;
};

type TrendBase = { question: string; source: "baseline" | "bank" | "ai_followup" };
type VoiceTrendPoint = TrendBase & {
  wpm?: number;
  filler_count?: number;
  pause_ratio?: number;
  fluency?: number;
};
type PresenceTrendPoint = TrendBase & {
  eye_contact_pct?: number;
  posture?: number;
  facial_expression?: number;
};
type LanguageTrendPoint = TrendBase & {
  grammar_errors?: number;
  word_count?: number;
  clarity?: number;
  vocabulary?: number;
};
type ProgressionPoint = TrendBase & { answer_score?: number };
type DomainPoint = { domain: string; score: number };
type GraphData = {
  audio_factors: ChartFactor[];
  audio_takeaway: string;
  video_factors: ChartFactor[];
  video_takeaway: string;
  nlp_factors: ChartFactor[];
  nlp_takeaway: string;
  voice_trend: VoiceTrendPoint[];
  voice_trend_takeaway: string;
  presence_trend: PresenceTrendPoint[];
  presence_trend_takeaway: string;
  video_coverage: string;
  language_trend: LanguageTrendPoint[];
  language_trend_takeaway: string;
  progression_trend: ProgressionPoint[];
  progression_trend_takeaway: string;
  domain_radar: DomainPoint[];
  domain_radar_takeaway: string;
  score_scale: { min: number; max: number };
  voice_rate_band: { low: number; high: number };
  audio_coverage: string;
  language_coverage: string;
};

type InsightReport = {
  overall_assessment?: string;
  strengths?: string[];
  weaknesses?: string[];
  improvements?: string[];
  recommendations?: string[];
  technical_summary?: string;
  communication_summary?: string;
  audio_summary?: string;
  visual_summary?: string;
  question_evaluations?: Array<Record<string, unknown>>;
  measurement_notes?: string[];
  performance_patterns?: Record<string, unknown>;
  behavior_analysis?: Record<string, unknown>;
  graph_data?: GraphData;
  confidence?: number | string;
  internal_metrics?: Record<string, unknown>;
  overall_scores?: {
    answer: number | null;
    audio: number | null;
    nlp: number | null;
    video: number | null;
    overall_session: number | null;
    overall_out_of_100?: number | null;
  };
  contribution_breakdown?: {
    pie_chart: Array<{
      domain: string;
      label: string;
      percentage: number;
      weight?: number;
      earned?: number;
      lost?: number;
      share_of_total_earned?: number;
      score: number | null;
      color: string;
    }>;
    pie_not_earned?: number;
    domains: DomainBreakdown[];
    factor_decomposition: Record<string, FactorItem[]>;
    reasoning: string;
    reasoning_source?: "llm" | "template_fallback";
  };
  research_benchmarks?: {
    strengths: BenchmarkItem[];
    meets_expectation: BenchmarkItem[];
    weaknesses: BenchmarkItem[];
    insufficient_signal: Array<{
      domain: string;
      key: string;
      name: string;
      score: number | null;
      reason: string;
    }>;
  };
  stage_behavior_analysis?: StageBehaviorItem[];
  pillar_improvements?: Record<string, PillarImprovement>;
  candidate_summary?: {
    headline: string;
    what_went_well: string[];
    what_to_work_on: string[];
    next_steps: string[];
    reasoning_source?: "llm" | "template_fallback";
  };
  soft_skill_summary?: {
    content_score: number | null;
    soft_skill_score: number | null;
    voice_score: number | null;
    body_language_score: number | null;
    language_score: number | null;
    takeaway: string;
  };
  evidence?: Array<{ source: string; note: string }>;
  language_analysis?: {
    data_available: boolean;
    analyzed_answer_count: number;
    total_word_count: number;
    english_word_count: number;
    hindi_word_count: number;
    english_word_percentage: number;
    hindi_word_percentage: number;
    code_switching_count: number;
    code_switching_ratio: number;
    dominant_language: string;
    language_pattern: string;
    hindi_words: Record<string, number>;
    english_words: Record<string, number>;
    language_switching_examples: Array<{
      question_number: number;
      example: string;
    }>;
    answers: Array<{
      question_number: number;
      dominant_language: string;
      word_count: number;
      english_word_count: number;
      hindi_word_count: number;
      english_word_percentage: number;
      hindi_word_percentage: number;
      code_switching_count: number;
      code_switching_ratio: number;
    }>;
    summary: string;
    feedback?: string;
    transcription_method?: string;
    interpretation_note: string;
  };
  disclaimer?: string;
  status?: string;
};

type AnalysisResponse = {
  session: {
    id: string;
    status: string;
    target_question_count: number;
    started_at: string | null;
    ended_at: string | null;
  };
  questions: SessionQuestion[];
  insights?: InsightReport | null;
  analysis_status?: string;
  analysis_error?: string | null;
};

function numVal(value: unknown): number | null {
  return typeof value === "number" && !isNaN(value) ? value : null;
}

function parseCountMap(value: unknown): Record<string, number> {
  let parsed = value;
  if (typeof value === "string") {
    try {
      parsed = JSON.parse(value);
    } catch {
      return {};
    }
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
  return Object.fromEntries(
    Object.entries(parsed).filter((entry): entry is [string, number] =>
      typeof entry[1] === "number"
    )
  );
}

function parseStringList(value: unknown): string[] {
  let parsed = value;
  if (typeof value === "string") {
    try {
      parsed = JSON.parse(value);
    } catch {
      return [];
    }
  }
  return Array.isArray(parsed)
    ? parsed.filter((item): item is string => typeof item === "string")
    : [];
}

function parseWordLabels(
  value: unknown
): Array<{ word: string; language: string }> {
  let parsed = value;
  if (typeof value === "string") {
    try {
      parsed = JSON.parse(value);
    } catch {
      return [];
    }
  }
  if (!Array.isArray(parsed)) return [];
  return parsed.filter(
    (item): item is { word: string; language: string } =>
      !!item
      && typeof item === "object"
      && "word" in item
      && typeof item.word === "string"
      && "language" in item
      && typeof item.language === "string"
  );
}

const DONUT_RADIUS = 38;
const DONUT_CIRCUMFERENCE = 2 * Math.PI * DONUT_RADIUS;
const CHART_PALETTE = {
  violet: "#3b82f6",
  cyan: "#0ea5e9",
  emerald: "#34d399",
  amber: "#fbbf24",
  red: "#f87171",
  muted: "#64748b",
  grid: "#1e293b",
  text: "#94a3b8",
};
const FACTOR_COLORS: Record<ChartFactor["classification"], string> = {
  strength: CHART_PALETTE.emerald,
  developing: CHART_PALETTE.amber,
  weakness: CHART_PALETTE.red,
};
const SOURCE_COLORS: Record<TrendBase["source"], string> = {
  baseline: CHART_PALETTE.violet,
  bank: CHART_PALETTE.cyan,
  ai_followup: CHART_PALETTE.amber,
};
const SOURCE_LABELS: Record<TrendBase["source"], string> = {
  baseline: "Opening question",
  bank: "Standard question",
  ai_followup: "Follow-up question",
};

function ChartCard({
  title,
  howToRead,
  takeaway,
  hasData,
  emptyMessage = "Not enough data to display this chart.",
  children,
}: {
  title: string;
  howToRead: string;
  takeaway: string;
  hasData: boolean;
  emptyMessage?: string;
  children: ReactNode;
}) {
  const id = useId();
  const titleId = `${id}-title`;
  const descriptionId = `${id}-description`;
  const takeawayId = `${id}-takeaway`;

  return (
    <section className="studio-surface p-5">
      <h3 id={titleId} className="font-semibold text-white">{title}</h3>
      <p id={descriptionId} className="mt-1 text-xs leading-5 text-zinc-400">
        <strong className="font-semibold text-zinc-300">How to read this: </strong>{howToRead}
      </p>
      {hasData ? (
        <div
          role="img"
          aria-labelledby={titleId}
          aria-describedby={`${descriptionId} ${takeawayId}`}
          className="mt-4 h-72 w-full"
        >
          {children}
        </div>
      ) : (
        <p role="status" className="mt-4 flex h-72 items-center justify-center rounded-xl border border-white/[0.05] bg-black/10 text-sm text-zinc-400">
          {emptyMessage}
        </p>
      )}
      <p id={takeawayId} className="mt-3 text-sm leading-6 text-zinc-300">
        <strong className="font-semibold text-zinc-100">Takeaway: </strong>{takeaway}
      </p>
    </section>
  );
}

function FactorLegend() {
  return (
    <div className="flex flex-wrap justify-center gap-4 pt-2 text-[11px] text-zinc-400">
      {(Object.entries(FACTOR_COLORS) as Array<[ChartFactor["classification"], string]>).map(([classification, color]) => (
        <span key={classification} className="inline-flex items-center gap-2">
          <span aria-hidden="true" className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: color }} />
          {classification === "weakness" ? "Growth area" : classification === "strength" ? "Strength" : "Developing"}
        </span>
      ))}
    </div>
  );
}

function FactorBarChart({
  factors,
  scoreScale,
}: {
  factors: ChartFactor[];
  scoreScale: GraphData["score_scale"];
}) {
  const thresholds = factors[0];
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={factors} layout="vertical" margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
        <CartesianGrid stroke={CHART_PALETTE.grid} strokeDasharray="3 3" horizontal={false} />
        <XAxis
          type="number"
          domain={[scoreScale.min, scoreScale.max]}
          tick={{ fill: CHART_PALETTE.text, fontSize: 11 }}
          axisLine={{ stroke: CHART_PALETTE.grid }}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={142}
          tick={{ fill: CHART_PALETTE.text, fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          cursor={{ fill: "rgba(161, 161, 170, 0.08)" }}
          contentStyle={{ backgroundColor: "#09090b", borderColor: CHART_PALETTE.grid, borderRadius: 12 }}
          labelStyle={{ color: "#fafafa" }}
        />
        <Legend content={<FactorLegend />} />
        {thresholds && (
          <>
            <ReferenceLine
              x={thresholds.weak_below}
              stroke={CHART_PALETTE.red}
              strokeDasharray="4 4"
              label={`Growth ${thresholds.weak_below}`}
            />
            <ReferenceLine
              x={thresholds.strong_from}
              stroke={CHART_PALETTE.emerald}
              strokeDasharray="4 4"
              label={`Strength ${thresholds.strong_from}`}
            />
          </>
        )}
        <Bar dataKey="score" name="Score" radius={[0, 5, 5, 0]}>
          {factors.map((factor) => <Cell key={factor.key} fill={FACTOR_COLORS[factor.classification]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function ResultsContent() {
  const params = useParams();
  const sessionId = useMemo(() => {
    if (params?.sessionId) return String(params.sessionId);
    if (typeof window !== "undefined") {
      const parts = window.location.pathname.split("/").filter(Boolean);
      return parts.at(-2) || parts.at(-1) || null;
    }
    return null;
  }, [params]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<AnalysisResponse | null>(null);
  const [activeDomainId, setActiveDomainId] = useState<string>("answer");
  const [activeChartTab, setActiveChartTab] = useState<"Overview" | "Voice" | "Presence" | "Language" | "Answers" | "Plan">("Overview");
  const [benchmarkFilter, setBenchmarkFilter] = useState<"all" | "strengths" | "weaknesses" | "meets">("all");
  const [expandedQuestions, setExpandedQuestions] = useState<Record<number, boolean>>({ 1: true });
  const [isSavingReport, setIsSavingReport] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      queueMicrotask(() => {
        setError("Interview session ID is missing.");
        setLoading(false);
      });
      return;
    }

    let cancelled = false;
    const pause = () => new Promise<void>((resolve) => setTimeout(resolve, 2000));

    async function fetchResults() {
      try {
        setLoading(true);
        let resultData: AnalysisResponse | null = null;
        let status: string | undefined;

        while (!cancelled) {
          const res = await apiFetch(`/interviews/${sessionId}/analysis-results`, {
            cache: "no-store",
          });
          if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || "Unable to load interview analysis.");
          }
          resultData = await res.json();
          status = resultData?.analysis_status;

          if (status === "pending") {
            const startResponse = await apiFetch(`/interviews/${sessionId}/video-analysis`, {
              method: "POST",
            });
            if (!startResponse.ok) {
              const errData = await startResponse.json().catch(() => ({}));
              throw new Error(errData.detail || "Unable to start interview analysis.");
            }
            status = "running";
          }
          if (status === "running") {
            const statusResponse = await apiFetch(`/interviews/${sessionId}/analysis-status`, {
              cache: "no-store",
            });
            if (!statusResponse.ok) {
              const errData = await statusResponse.json().catch(() => ({}));
              throw new Error(errData.detail || "Unable to check analysis status.");
            }
            const statusData = await statusResponse.json();
            if (statusData.analysis_status === "completed") continue;
            if (statusData.analysis_status === "failed") {
              throw new Error(statusData.error || "Interview analysis failed.");
            }
            await pause();
            continue;
          }
          if (status === "failed") {
            throw new Error(resultData?.analysis_error || "Interview analysis failed.");
          }
          if (status === "completed" && resultData?.insights) break;
          if (cancelled) return;
          throw new Error("Interview analysis is not available yet.");
        }
        if (!cancelled && resultData) setData(resultData);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Error loading analysis results.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void fetchResults();

    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const attemptedQuestions = useMemo(() => {
    if (!data?.questions) return [];
    return data.questions.filter(
      (q) => q.transcript_text !== null || q.answer_evaluation !== null
    );
  }, [data]);

  // Fallback averages if insights object doesn't supply overall_scores
  const computedAverages = useMemo(() => {
    if (!attemptedQuestions.length) {
      return { answer: null, audio: null, nlp: null, video: null, overall: null };
    }
    const qList = attemptedQuestions;

    const calc = (key: keyof SessionQuestion, field: string) => {
      const vals = qList
        .map((q) => {
          const evalObj = q[key] as Record<string, unknown> | null;
          return evalObj ? numVal(evalObj[field]) : null;
        })
        .filter((v): v is number => v !== null);
      return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
    };

    const ans = calc("answer_evaluation", "rating");
    const aud = calc("audio_evaluation", "overall_score");
    const nlp = calc("nlp_evaluation", "overall_score");
    const vid = calc("video_evaluation", "overall_score");

    const valid = [ans, aud, nlp, vid].filter((v): v is number => v !== null);
    const ovr = valid.length ? valid.reduce((a, b) => a + b, 0) / valid.length : null;

    return { answer: ans, audio: aud, nlp, video: vid, overall: ovr };
  }, [attemptedQuestions]);

  const insights = data?.insights;
  const graphData = insights?.graph_data;
  const hasModalityGraphData = Boolean(
    graphData
    && Array.isArray(graphData.audio_factors)
    && Array.isArray(graphData.video_factors)
    && Array.isArray(graphData.nlp_factors)
    && Array.isArray(graphData.voice_trend)
    && Array.isArray(graphData.presence_trend)
    && Array.isArray(graphData.language_trend)
    && Array.isArray(graphData.progression_trend)
    && Array.isArray(graphData.domain_radar)
    && typeof graphData.video_coverage === "string"
    && typeof graphData.audio_takeaway === "string"
    && typeof graphData.voice_rate_band?.low === "number"
    && typeof graphData.voice_rate_band?.high === "number"
    && typeof graphData.score_scale?.min === "number"
    && typeof graphData.score_scale?.max === "number"
  );
  const voiceWpmValues = graphData?.voice_trend
    .map((point) => point.wpm)
    .filter((value): value is number => typeof value === "number");
  const voiceWpmDomain: [number, number] | undefined =
    hasModalityGraphData && graphData
      ? [
          Math.min(graphData.voice_rate_band.low, ...(voiceWpmValues ?? [])),
          Math.max(graphData.voice_rate_band.high, ...(voiceWpmValues ?? [])),
        ]
      : undefined;
  const overallScores = {
    answer: insights?.overall_scores?.answer ?? (computedAverages.answer !== null ? Number(computedAverages.answer.toFixed(1)) : null),
    audio: insights?.overall_scores?.audio ?? (computedAverages.audio !== null ? Number(computedAverages.audio.toFixed(1)) : null),
    nlp: insights?.overall_scores?.nlp ?? (computedAverages.nlp !== null ? Number(computedAverages.nlp.toFixed(1)) : null),
    video: insights?.overall_scores?.video ?? (computedAverages.video !== null ? Number(computedAverages.video.toFixed(1)) : null),
    overall: insights?.overall_scores?.overall_session ?? (computedAverages.overall !== null ? Number(computedAverages.overall.toFixed(1)) : null),
  };

  const contributionData = insights?.contribution_breakdown;
  const activeDomain = useMemo(() => {
    if (!contributionData?.domains) return null;
    return contributionData.domains.find((d) => d.id === activeDomainId) || contributionData.domains[0];
  }, [contributionData, activeDomainId]);

  const benchmarks = insights?.research_benchmarks;
  const filteredBenchmarks = useMemo(() => {
    if (!benchmarks) return [];
    if (benchmarkFilter === "strengths") return benchmarks.strengths;
    if (benchmarkFilter === "weaknesses") return benchmarks.weaknesses;
    if (benchmarkFilter === "meets") return benchmarks.meets_expectation;
    return [...benchmarks.strengths, ...benchmarks.weaknesses, ...benchmarks.meets_expectation];
  }, [benchmarks, benchmarkFilter]);

  const stages = insights?.stage_behavior_analysis || [];
  const pillars = insights?.pillar_improvements;

  const toggleQuestion = (qNum: number) => {
    setExpandedQuestions((prev) => ({
      ...prev,
      [qNum]: !prev[qNum],
    }));
  };

  const handleDownloadPdf = async () => {
    if (!sessionId) return;
    setIsSavingReport(true);
    setSaveError(null);

    try {
      const response = await apiFetch(`/interviews/${sessionId}/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          report_json: insights,
          pdf_data: `HIRESENSE-PDF-REPORT-SESSION-${sessionId}`,
        }),
      });
      if (!response.ok) {
        const failure = await response.json().catch(() => ({}));
        throw new Error(failure.detail || "Could not save the interview report.");
      }

      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 4000);

      // 2. Open standard system print dialog with executive printable layout
      printReport();
    } catch (err) {
      console.error("Failed to save report to database:", err);
      setSaveError(err instanceof Error ? err.message : "Could not save the report.");
      // Still trigger print for candidate
      printReport();
    } finally {
      setIsSavingReport(false);
    }
  };

  const printReport = () => {
    document.documentElement.dataset.pdf = "true";
    window.addEventListener(
      "afterprint",
      () => {
        delete document.documentElement.dataset.pdf;
      },
      { once: true },
    );
    window.print();
  };

  if (loading) {
    return (
      <main className="flex min-h-[calc(100svh-4rem)] items-center justify-center px-4 py-10 text-white sm:px-6">
        <div className="rounded-lg border border-slate-800 bg-[#101522] w-full max-w-2xl p-6 sm:p-8">
          <div className="relative mx-auto h-12 w-12">
            <div className="h-12 w-12 rounded-full border-2 border-blue-500/20 border-t-blue-500 animate-spin" />
          </div>
          <div role="status" aria-live="polite" className="text-center">
            <h2 className="mt-5 text-lg font-semibold tracking-tight text-white">Preparing your feedback report</h2>
            <p className="mt-1.5 text-xs leading-relaxed text-slate-400">
              We’re reviewing your recorded answers and building feedback from the data available.
            </p>
          </div>
          <ol aria-label="Analysis stages" className="mt-6 grid gap-2.5 sm:grid-cols-2">
            {[
              ["Transcribing", "Preparing your spoken answers"],
              ["Analysing voice", "Reviewing delivery patterns"],
              ["Analysing body language", "Reviewing visual presence"],
              ["Writing your feedback", "Putting your practice insights together"],
            ].map(([title, description], index) => (
              <li key={title} className="flex items-start gap-3 rounded-md border border-slate-800 bg-[#0a0d14] p-3.5">
                <span className={`grid h-7 w-7 shrink-0 place-items-center rounded text-xs font-semibold ${
                  index === 0 ? "bg-blue-600/15 text-blue-300" : "bg-slate-800 text-slate-400"
                }`}>
                  {index === 0 ? <span className="h-3 w-3 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" /> : index + 1}
                </span>
                <span>
                  <span className="block text-xs font-semibold text-slate-200">{title}</span>
                  <span className="mt-0.5 block text-[11px] text-slate-500">{description}</span>
                </span>
              </li>
            ))}
          </ol>
          <p className="mt-5 text-center text-xs text-slate-500">
            These steps may overlap. We’ll open your report as soon as the analysis-status check is complete.
          </p>
        </div>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="min-h-screen bg-[#0a0d14] text-white flex items-center justify-center p-6">
        <div className="w-full max-w-md rounded-lg border border-red-500/20 bg-red-950/20 p-8 text-center">
          <AlertTriangle className="mx-auto h-12 w-12 text-red-400" />
          <h1 className="mt-4 text-xl font-bold">Analysis Unavailable</h1>
          <p className="mt-2 text-xs text-slate-400">{error ?? "Unable to retrieve interview report."}</p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="mt-6 rounded-md border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-medium text-slate-200 transition hover:bg-slate-700"
          >
            Retry Analysis
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-[calc(100svh-4rem)] bg-transparent text-slate-100 selection:bg-blue-600 selection:text-white print:bg-white print:text-black">
      {/* Printable Title Bar for PDF */}
      <div className="hidden print:block p-8 border-b border-zinc-300">
        <h1 className="text-3xl font-bold text-zinc-900">HireSense AI — Interview Practice Feedback</h1>
        <p className="text-sm text-zinc-600 mt-1">Session ID: {sessionId} • Candidate Performance Report</p>
      </div>

      <div className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:px-8 space-y-10">
        {/* =========================================================================
            HEADER & ACTIONS
        ========================================================================= */}
        <header className="sticky top-14 z-30 -mx-4 flex flex-col gap-4 border-b border-slate-800 bg-[#0a0d14] px-4 pb-4 pt-3 print:hidden sm:-mx-6 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:-mx-8 lg:px-8">
          <div>
            <div className="inline-flex items-center gap-1.5 rounded border border-blue-500/30 bg-blue-500/10 px-2.5 py-0.5 text-xs font-medium text-blue-300">
              <ShieldCheck className="h-3.5 w-3.5" />
              <span>HireSense Insight Agent</span>
            </div>
            <h1 className="mt-2 text-2xl font-bold tracking-tight text-white sm:text-3xl">
              Your practice report
            </h1>
            <p className="mt-1 text-xs text-slate-400">
              A personal review of {attemptedQuestions.length} practice answers
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <Link
              href="/"
              className="rounded-md border border-slate-700 bg-slate-800 px-3.5 py-2 text-xs font-medium text-slate-200 transition hover:bg-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500"
            >
              Back to Home
            </Link>
            <Link
              href="/history"
              className="rounded-md border border-slate-700 bg-slate-800 px-3.5 py-2 text-xs font-medium text-slate-200 transition hover:bg-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500"
            >
              Past interviews
            </Link>
            <button
              type="button"
              onClick={handleDownloadPdf}
              disabled={isSavingReport}
              className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-xs font-medium text-white shadow-sm transition hover:bg-blue-500 active:scale-[0.98] disabled:opacity-50"
            >
              {isSavingReport ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>Saving to DB...</span>
                </>
              ) : saveSuccess ? (
                <>
                  <Check className="h-4 w-4 text-emerald-300" />
                  <span>Report Saved!</span>
                </>
              ) : (
                <>
                  <Download className="h-4 w-4" />
                  <span>Download PDF Report</span>
                </>
              )}
            </button>
          </div>
        </header>
        {saveError && (
          <p role="alert" className="print:hidden -mt-6 text-sm text-red-300">
            {saveError}
          </p>
        )}

        {insights?.status === "failed" && (
          <div role="alert" className="rounded-2xl border border-red-500/30 bg-red-950/30 p-5 text-sm text-red-200">
            Analysis could not be completed. Your interview answers are saved, but this report is unavailable.
          </div>
        )}
        {insights?.status === "insufficient_data" && (
          <div role="status" className="rounded-2xl border border-amber-500/30 bg-amber-950/20 p-5 text-sm text-amber-100">
            There is not enough analysed data to score this interview. Try recording and submitting more answers, then review the results again.
          </div>
        )}
        {insights?.status === "partial" && (
          <div role="status" className="rounded-2xl border border-amber-500/30 bg-amber-950/20 p-5 text-sm text-amber-100">
            This is a partial report. Scores use only the interview data that was available for analysis.
          </div>
        )}

        {insights?.candidate_summary && (
          <section aria-labelledby="candidate-summary-title" className="rounded-lg border border-slate-800 bg-[#101522] p-6">
            <div className="flex flex-wrap items-center gap-2">
              <h2 id="candidate-summary-title" className="text-lg font-bold text-white">Your practice summary</h2>
              <span className="rounded border border-slate-700 bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-300">
                {insights.candidate_summary.reasoning_source === "llm" ? "AI-assisted wording" : "Data-based"}
              </span>
            </div>
            <p className="mt-2 text-base font-medium text-slate-200">{insights.candidate_summary.headline}</p>
            <div className="mt-5 grid gap-5 md:grid-cols-3">
              {[
                ["What went well", insights.candidate_summary.what_went_well],
                ["What to work on", insights.candidate_summary.what_to_work_on],
                ["Your next steps", insights.candidate_summary.next_steps],
              ].map(([heading, items]) => (
                <div key={heading as string}>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">{heading}</h3>
                  <ul className="mt-2 space-y-1.5 text-xs leading-relaxed text-slate-300">
                    {(items as string[]).map((item, index) => <li key={`${heading}-${index}`}>{item}</li>)}
                  </ul>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* =========================================================================
            1. OVERALL SCORES HERO GRID
        ========================================================================= */}
        <section aria-labelledby="overall-scores-title" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 id="overall-scores-title" className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
              <Award className="h-5 w-5 text-blue-400" />
              <span>Overall Session Scores</span>
            </h2>
            <span className="text-xs text-slate-400">Based on available recorded analysis</span>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {/* Overall Session Average */}
            <div className="flex flex-col justify-between rounded-lg border border-slate-800 bg-[#101522] p-4 shadow-sm">
              <div>
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Session average</span>
                <div className="mt-3 flex items-center gap-3">
                  <ProgressRing value={overallScores.overall} size={64} stroke={5} />
                  <span className="text-xs leading-snug text-slate-400">Overall<br />practice score</span>
                </div>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-800">
                <span className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-400">
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Practice feedback</span>
                </span>
              </div>
            </div>

            {/* Answer Content Score */}
            <div className="studio-surface flex flex-col justify-between p-4 transition hover:border-violet-300/20">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-zinc-300">Answer content</span>
                  <BookOpen className="h-4 w-4 text-violet-400" />
                </div>
                <div className="mt-3 flex justify-center"><ProgressRing value={overallScores.answer} size={62} stroke={5} /></div>
              </div>
              <div className="mt-3 pt-3 border-t border-zinc-800 text-[11px] text-zinc-500">
                {contributionData?.pie_chart.find((item) => item.domain === "answer")?.weight ?? 40}% importance weight
              </div>
            </div>

            {/* Speaking Delivery (Audio) Score */}
            <div className="studio-surface flex flex-col justify-between p-4 transition hover:border-emerald-300/20">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-zinc-300">Speaking audio</span>
                  <Mic className="h-4 w-4 text-emerald-400" />
                </div>
                <div className="mt-3 flex justify-center"><ProgressRing value={overallScores.audio} size={62} stroke={5} /></div>
              </div>
              <div className="mt-3 pt-3 border-t border-zinc-800 text-[11px] text-zinc-500">
                {contributionData?.pie_chart.find((item) => item.domain === "audio")?.weight ?? 20}% importance weight
              </div>
            </div>

            {/* Visual Presence (Video) Score */}
            <div className="studio-surface flex flex-col justify-between p-4 transition hover:border-cyan-300/20">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-zinc-300">Visual presence</span>
                  <Video className="h-4 w-4 text-cyan-400" />
                </div>
                <div className="mt-3 flex justify-center"><ProgressRing value={overallScores.video} size={62} stroke={5} /></div>
              </div>
              <div className="mt-3 pt-3 border-t border-zinc-800 text-[11px] text-zinc-500">
                {contributionData?.pie_chart.find((item) => item.domain === "video")?.weight ?? 20}% importance weight
              </div>
            </div>

            {/* Language Quality (NLP) Score */}
            <div className="studio-surface flex flex-col justify-between p-4 transition hover:border-amber-300/20">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-zinc-300">Language</span>
                  <Brain className="h-4 w-4 text-amber-400" />
                </div>
                <div className="mt-3 flex justify-center"><ProgressRing value={overallScores.nlp} size={62} stroke={5} /></div>
              </div>
              <div className="mt-3 pt-3 border-t border-zinc-800 text-[11px] text-zinc-500">
                {contributionData?.pie_chart.find((item) => item.domain === "nlp")?.weight ?? 20}% importance weight
              </div>
            </div>
          </div>

          {/* Holistic Assessment Callout */}
          {insights?.overall_assessment && (
            <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5 text-sm leading-relaxed text-zinc-300">
              <span className="font-semibold text-white">Your overall feedback: </span>
              {insights.overall_assessment}
            </div>
          )}
          {insights?.measurement_notes?.length ? (
            <aside
              aria-label="Measurement notes"
              className="rounded-xl border border-sky-900/60 bg-sky-950/20 p-4 text-xs leading-5 text-sky-100/80"
            >
              <h3 className="font-semibold text-sky-100">Measurement notes</h3>
              <ul className="mt-1 list-disc space-y-1 pl-4">
                {insights.measurement_notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </aside>
          ) : null}
          {insights?.soft_skill_summary && (
            <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-5">
              <h3 className="font-semibold text-white">Content vs soft skills</h3>
              <p className="mt-2 text-sm leading-6 text-zinc-300">{insights.soft_skill_summary.takeaway}</p>
              <div className="mt-4 grid grid-cols-2 gap-3 text-xs sm:grid-cols-5">
                {[
                  ["Content", insights.soft_skill_summary.content_score],
                  ["Soft skills", insights.soft_skill_summary.soft_skill_score],
                  ["Voice", insights.soft_skill_summary.voice_score],
                  ["Body language", insights.soft_skill_summary.body_language_score],
                  ["Language", insights.soft_skill_summary.language_score],
                ].map(([label, score]) => (
                  <div key={label as string} className="rounded-lg bg-zinc-950/70 p-3">
                    <span className="text-zinc-500">{label as string}</span>
                    <p className="mt-1 font-mono font-semibold text-zinc-100">
                      {typeof score === "number" ? `${score.toFixed(1)}/10` : "Not analysed"}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        <section aria-labelledby="modality-charts-title" className="space-y-5">
          <div>
            <h2 id="modality-charts-title" className="text-xl font-bold text-white">
              Modality charts
            </h2>
            <p className="mt-1 text-sm text-zinc-400">
              Explore measured voice, presence, language, and answer patterns from this interview.
            </p>
          </div>
          <Tabs
            tabs={["Overview", "Voice", "Presence", "Language", "Answers", "Plan"]}
            value={activeChartTab}
            onChange={(tab) => setActiveChartTab(tab as typeof activeChartTab)}
          />
          <div aria-label={`${activeChartTab} charts`} className="grid gap-4 lg:grid-cols-2" aria-live="polite">
            {!hasModalityGraphData && activeChartTab !== "Plan" && (
              <p role="status" className="lg:col-span-2 rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 text-sm text-zinc-400">
                Not enough chart data is available in this saved report. Run the analysis again to create modality charts.
              </p>
            )}
            {activeChartTab === "Overview" && hasModalityGraphData && graphData && (
              <>
                <ChartCard
                  title="Overview by modality"
                  howToRead="Each spoke shows an available modality score on the report scale."
                  takeaway={graphData.domain_radar_takeaway}
                  hasData={graphData.domain_radar.length > 0}
                  emptyMessage="Not enough data to display the overview radar."
                >
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart data={graphData.domain_radar} outerRadius="72%">
                      <PolarGrid stroke={CHART_PALETTE.grid} />
                      <PolarAngleAxis dataKey="domain" tick={{ fill: CHART_PALETTE.text, fontSize: 12 }} />
                      <PolarRadiusAxis
                        domain={[graphData.score_scale.min, graphData.score_scale.max]}
                        tick={{ fill: CHART_PALETTE.text, fontSize: 10 }}
                      />
                      <Tooltip
                        contentStyle={{ backgroundColor: "#09090b", borderColor: CHART_PALETTE.grid, borderRadius: 12 }}
                      />
                      <Radar
                        name="Score"
                        dataKey="score"
                        stroke={CHART_PALETTE.violet}
                        fill={CHART_PALETTE.violet}
                        fillOpacity={0.3}
                      />
                    </RadarChart>
                  </ResponsiveContainer>
                </ChartCard>
                {graphData.domain_radar.length < 4 && (
                  <p role="status" className="self-start rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 text-sm text-zinc-400">
                    {[
                      ["answer", "Answers"],
                      ["audio", "Voice"],
                      ["video", "Video"],
                      ["nlp", "Language"],
                    ]
                      .filter(([domain]) => !graphData.domain_radar.some((point) => point.domain === domain))
                      .map(([, label]) => `${label} not analysed`)
                      .join(" · ")}
                  </p>
                )}
              </>
            )}

            {activeChartTab === "Voice" && hasModalityGraphData && graphData && (
              <>
                <ChartCard
                  title="Voice factors"
                  howToRead="Bar colours identify strengths, developing areas, and growth areas; dashed lines show the reference cutoffs."
                  takeaway={graphData.audio_takeaway}
                  hasData={graphData.audio_factors.length > 0}
                >
                  <FactorBarChart factors={graphData.audio_factors} scoreScale={graphData.score_scale} />
                </ChartCard>
                <ChartCard
                  title="Speaking pace and fillers by answer"
                  howToRead={`The shaded band marks ${graphData.voice_rate_band.low}–${graphData.voice_rate_band.high} words per minute; bars show filler counts.`}
                  takeaway={graphData.voice_trend_takeaway}
                  hasData={graphData.voice_trend.some((point) => point.wpm !== undefined || point.filler_count !== undefined)}
                >
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={graphData.voice_trend} margin={{ top: 8, right: 12, bottom: 8, left: 4 }}>
                      <CartesianGrid stroke={CHART_PALETTE.grid} strokeDasharray="3 3" />
                      <XAxis dataKey="question" tick={{ fill: CHART_PALETTE.text, fontSize: 11 }} />
                      <YAxis
                        yAxisId="wpm"
                        orientation="left"
                        domain={voiceWpmDomain}
                        tick={{ fill: CHART_PALETTE.text, fontSize: 11 }}
                      />
                      <YAxis yAxisId="fillers" orientation="right" tick={{ fill: CHART_PALETTE.text, fontSize: 11 }} />
                      <Tooltip contentStyle={{ backgroundColor: "#09090b", borderColor: CHART_PALETTE.grid, borderRadius: 12 }} />
                      <Legend />
                      <ReferenceArea
                        yAxisId="wpm"
                        y1={graphData.voice_rate_band.low}
                        y2={graphData.voice_rate_band.high}
                        fill={CHART_PALETTE.violet}
                        fillOpacity={0.12}
                        label="Practice pace band"
                      />
                      <Bar yAxisId="fillers" dataKey="filler_count" name="Filler count" fill={CHART_PALETTE.amber} />
                      <Line yAxisId="wpm" dataKey="wpm" name="Words per minute" stroke={CHART_PALETTE.violet} connectNulls={false} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </ChartCard>
              </>
            )}

            {activeChartTab === "Presence" && hasModalityGraphData && graphData && (
              <>
                <p className="lg:col-span-2 rounded-xl border border-cyan-500/20 bg-cyan-950/10 p-3 text-sm text-cyan-100">
                  {graphData.video_factors.length === 0 && graphData.presence_trend.length === 0
                    ? "Video not analysed."
                    : `Video coverage: ${graphData.video_coverage}.`}
                </p>
                <ChartCard
                  title="Presence factors"
                  howToRead="Bar colours identify strengths, developing areas, and growth areas; dashed lines show the reference cutoffs."
                  takeaway={graphData.video_takeaway}
                  hasData={graphData.video_factors.length > 0}
                  emptyMessage="Video not analysed. There are no presence factor scores for this interview."
                >
                  <FactorBarChart factors={graphData.video_factors} scoreScale={graphData.score_scale} />
                </ChartCard>
                <ChartCard
                  title="Eye contact by analysed answer"
                  howToRead="Each point is the measured eye-contact percentage for an analysed video clip."
                  takeaway={graphData.presence_trend_takeaway}
                  hasData={graphData.presence_trend.some((point) => point.eye_contact_pct !== undefined)}
                  emptyMessage={graphData.video_coverage.startsWith("analysed 0")
                    ? "Video not analysed. There are no eye-contact measurements to plot."
                    : "No eye-contact measurements were recorded for the analysed video clips."}
                >
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={graphData.presence_trend} margin={{ top: 8, right: 12, bottom: 8, left: 4 }}>
                      <CartesianGrid stroke={CHART_PALETTE.grid} strokeDasharray="3 3" />
                      <XAxis dataKey="question" tick={{ fill: CHART_PALETTE.text, fontSize: 11 }} />
                      <YAxis tick={{ fill: CHART_PALETTE.text, fontSize: 11 }} />
                      <Tooltip contentStyle={{ backgroundColor: "#09090b", borderColor: CHART_PALETTE.grid, borderRadius: 12 }} />
                      <Line dataKey="eye_contact_pct" name="Eye contact (%)" stroke={CHART_PALETTE.cyan} connectNulls={false} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </ChartCard>
              </>
            )}

            {activeChartTab === "Language" && hasModalityGraphData && graphData && (
              <>
                <p className="lg:col-span-2 rounded-xl border border-amber-500/20 bg-amber-950/10 p-3 text-sm text-amber-100">
                  Language coverage: {graphData.language_coverage}.
                </p>
                <ChartCard
                  title="Language factors"
                  howToRead="Bar colours identify strengths, developing areas, and growth areas; dashed lines show the reference cutoffs."
                  takeaway={graphData.nlp_takeaway}
                  hasData={graphData.nlp_factors.length > 0}
                >
                  <FactorBarChart factors={graphData.nlp_factors} scoreScale={graphData.score_scale} />
                </ChartCard>
                <ChartCard
                  title="Grammar errors and answer length"
                  howToRead="Bars show detected grammar errors; the line shows the analysed word count for each answer."
                  takeaway={graphData.language_trend_takeaway}
                  hasData={graphData.language_trend.some((point) => point.grammar_errors !== undefined || point.word_count !== undefined)}
                >
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={graphData.language_trend} margin={{ top: 8, right: 12, bottom: 8, left: 4 }}>
                      <CartesianGrid stroke={CHART_PALETTE.grid} strokeDasharray="3 3" />
                      <XAxis dataKey="question" tick={{ fill: CHART_PALETTE.text, fontSize: 11 }} />
                      <YAxis yAxisId="errors" orientation="left" tick={{ fill: CHART_PALETTE.text, fontSize: 11 }} />
                      <YAxis yAxisId="words" orientation="right" tick={{ fill: CHART_PALETTE.text, fontSize: 11 }} />
                      <Tooltip contentStyle={{ backgroundColor: "#09090b", borderColor: CHART_PALETTE.grid, borderRadius: 12 }} />
                      <Legend />
                      <Bar yAxisId="errors" dataKey="grammar_errors" name="Grammar errors" fill={CHART_PALETTE.amber} />
                      <Line yAxisId="words" dataKey="word_count" name="Word count" stroke={CHART_PALETTE.violet} connectNulls={false} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </ChartCard>
              </>
            )}

            {activeChartTab === "Answers" && hasModalityGraphData && graphData && (
              <ChartCard
                title="Answer score by question"
                howToRead="Each bar is coloured by question source: opening, standard, or follow-up."
                takeaway={graphData.progression_trend_takeaway}
                hasData={graphData.progression_trend.some((point) => point.answer_score !== undefined)}
              >
                <ResponsiveContainer width="100%" height="84%">
                  <BarChart data={graphData.progression_trend} margin={{ top: 8, right: 12, bottom: 8, left: 4 }}>
                    <CartesianGrid stroke={CHART_PALETTE.grid} strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="question" tick={{ fill: CHART_PALETTE.text, fontSize: 11 }} />
                    <YAxis
                      domain={[graphData.score_scale.min, graphData.score_scale.max]}
                      tick={{ fill: CHART_PALETTE.text, fontSize: 11 }}
                    />
                    <Tooltip contentStyle={{ backgroundColor: "#09090b", borderColor: CHART_PALETTE.grid, borderRadius: 12 }} />
                    <Bar dataKey="answer_score" name="Answer score" radius={[5, 5, 0, 0]}>
                      {graphData.progression_trend.map((point) => (
                        <Cell key={`${point.question}-${point.source}`} fill={SOURCE_COLORS[point.source]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <div aria-label="Answer source legend" className="flex flex-wrap justify-center gap-4 pt-1 text-xs text-zinc-400">
                  {(Object.keys(SOURCE_LABELS) as TrendBase["source"][]).map((source) => (
                    <span key={source} className="inline-flex items-center gap-2">
                      <span aria-hidden="true" className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: SOURCE_COLORS[source] }} />
                      {SOURCE_LABELS[source]}
                    </span>
                  ))}
                </div>
              </ChartCard>
            )}
            {activeChartTab === "Plan" && (
              <section className="studio-surface lg:col-span-2 p-5 sm:p-7" aria-labelledby="practice-plan-title">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-violet-300">Your next practice</p>
                    <h3 id="practice-plan-title" className="mt-1 text-xl font-bold text-white">A focused plan for what comes next</h3>
                  </div>
                  <Badge tone="brand">Built from this session</Badge>
                </div>
                {insights?.candidate_summary?.next_steps?.length ? (
                  <ol className="mt-6 grid gap-3 md:grid-cols-3">
                    {insights.candidate_summary.next_steps.map((step, index) => (
                      <li key={`${index}-${step}`} className="rounded-2xl border border-white/[0.07] bg-black/10 p-4">
                        <span className="grid h-8 w-8 place-items-center rounded-full bg-violet-500/15 text-xs font-bold text-violet-200">{index + 1}</span>
                        <p className="mt-3 text-sm leading-6 text-zinc-200">{step}</p>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="mt-5 rounded-xl border border-white/[0.07] bg-black/10 p-4 text-sm text-zinc-400">
                    A personalized practice plan is not available for this report yet.
                  </p>
                )}
              </section>
            )}
          </div>
        </section>

        {/* =========================================================================
            Contribution graph (pie chart and factor decomposition)
        ========================================================================= */}
        <section aria-labelledby="contribution-title" className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div>
              <h2 id="contribution-title" className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                <PieChartIcon className="h-5 w-5 text-cyan-400" />
                <span>Session Contribution Graph & Factor Decomposition</span>
              </h2>
              <p className="text-xs text-zinc-400 mt-1">
                How Answer, Audio, Video, and NLP contribute to the complete interview session (100% total)
              </p>
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-12 rounded-3xl border border-zinc-800 bg-zinc-900/40 p-6 sm:p-8 backdrop-blur-sm">
            {/* Visual Pie / Donut Chart Representation */}
            <div className="lg:col-span-5 flex flex-col items-center justify-center space-y-6">
              <div className="relative w-56 h-56 flex items-center justify-center">
                  {/* SVG donut uses earned points and points still available. */}
                  <svg
                    className="w-full h-full -rotate-90"
                    viewBox="0 0 100 100"
                    role="img"
                    aria-labelledby="contribution-donut-title contribution-donut-desc"
                  >
                    <title id="contribution-donut-title">Earned interview contribution</title>
                    <desc id="contribution-donut-desc">
                      Coloured slices show earned points by analysed domain; grey shows points not earned.
                    </desc>
                    <circle
                      cx="50"
                      cy="50"
                      r={DONUT_RADIUS}
                      className="stroke-zinc-800 fill-none"
                      strokeWidth="12"
                    />
                    {(contributionData?.pie_chart || []).map((slice, index, slices) => {
                      const earnedBefore = slices
                        .slice(0, index)
                        .reduce((sum, item) => sum + (item.earned ?? 0), 0);
                      const earnedLength = ((slice.earned ?? 0) / 100) * DONUT_CIRCUMFERENCE;
                      if (earnedLength <= 0) return null;
                      return (
                        <circle
                          key={slice.domain}
                          cx="50"
                          cy="50"
                          r={DONUT_RADIUS}
                          className="cursor-pointer transition-all hover:opacity-80"
                          stroke={slice.color}
                          strokeWidth={activeDomainId === slice.domain ? "15" : "12"}
                          strokeDasharray={`${earnedLength} ${DONUT_CIRCUMFERENCE}`}
                          strokeDashoffset={-((earnedBefore / 100) * DONUT_CIRCUMFERENCE)}
                          fill="none"
                          role="button"
                          tabIndex={0}
                          aria-label={`${slice.label}: ${slice.earned ?? 0} points earned`}
                          onClick={() => setActiveDomainId(slice.domain)}
                          onKeyDown={(event) => {
                            if (event.key === "Enter" || event.key === " ") {
                              event.preventDefault();
                              setActiveDomainId(slice.domain);
                            }
                          }}
                        />
                      );
                    })}
                    {(() => {
                      const earned = (contributionData?.pie_chart || [])
                        .reduce((sum, item) => sum + (item.earned ?? 0), 0);
                      const remaining = Math.max(0, 100 - earned);
                      if (remaining <= 0) return null;
                      return (
                        <circle
                          cx="50"
                          cy="50"
                          r={DONUT_RADIUS}
                          className="stroke-zinc-600 fill-none"
                          strokeWidth="12"
                          strokeDasharray={`${(remaining / 100) * DONUT_CIRCUMFERENCE} ${DONUT_CIRCUMFERENCE}`}
                          strokeDashoffset={-((earned / 100) * DONUT_CIRCUMFERENCE)}
                        />
                      );
                    })()}
                  </svg>

                {/* Donut Center Display */}
                <div className="absolute flex flex-col items-center justify-center text-center">
                  <span className="text-xs uppercase tracking-wider text-zinc-500">Overall</span>
                  <span className="text-2xl font-black text-white capitalize">
                    {insights?.overall_scores?.overall_out_of_100 !== null
                      && insights?.overall_scores?.overall_out_of_100 !== undefined
                      ? `${insights.overall_scores.overall_out_of_100.toFixed(1)}/100`
                      : "—"}
                  </span>
                  <span className="text-[11px] font-medium text-zinc-400 capitalize">
                    Earned points
                  </span>
                </div>
              </div>

              {/* Interactive Slice Buttons */}
              <div className="grid grid-cols-2 gap-2 w-full">
                {(contributionData?.domains || []).map((dom) => (
                  <button
                    key={dom.id}
                    type="button"
                    onClick={() => setActiveDomainId(dom.id)}
                    className={`flex items-center gap-2 rounded-xl border p-2.5 text-left text-xs transition ${activeDomainId === dom.id
                      ? "border-violet-500 bg-violet-500/10 text-white"
                      : "border-zinc-800 bg-zinc-950/40 text-zinc-400 hover:border-zinc-700"
                      }`}
                  >
                    <span className="h-3 w-3 rounded-full shrink-0" style={{ backgroundColor: dom.color }} />
                    <div className="truncate">
                      <div className="font-semibold text-white truncate">{dom.label.split(" ")[0]}</div>
                      <div className="text-[11px] text-zinc-400">
                        {dom.earned ?? 0} earned / {dom.weight ?? dom.percentage} available
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Factor Decomposition Breakdown for Selected Domain */}
            <div className="lg:col-span-7 flex flex-col justify-between space-y-5">
              <div>
                <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                  <div>
                    <span className="text-xs font-semibold text-violet-400 uppercase tracking-wider">
                      Constituent Factors Breakdown
                    </span>
                    <h3 className="text-lg font-bold text-white mt-0.5">
                      {activeDomain ? `${activeDomain.label} (${activeDomain.percentage}%)` : "Factors"}
                    </h3>
                  </div>
                  <span className="rounded-lg bg-zinc-800 px-2.5 py-1 text-xs text-zinc-300 font-mono">
                    Score: {activeDomain?.score !== null && activeDomain?.score !== undefined ? `${activeDomain.score}/10` : "—"}
                  </span>
                </div>

                {/* Granular Sub-Factors List */}
                <div className="mt-4 space-y-3">
                  {(activeDomain?.factors || []).map((factor, idx) => (
                    <div
                      key={idx}
                      className="rounded-xl border border-zinc-800/80 bg-zinc-950/60 p-3.5 hover:border-zinc-700 transition"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-semibold text-zinc-200">{factor.name}</span>
                        <div className="flex items-center gap-2">
                          {factor.score !== null ? (
                            <span className="rounded bg-violet-500/20 px-2 py-0.5 text-xs font-bold text-violet-300">
                              {factor.earned ?? 0}/{factor.weight ?? factor.percentage} earned
                            </span>
                          ) : (
                            <span className="rounded bg-zinc-800 px-2 py-0.5 text-xs text-zinc-400">Not analysed</span>
                          )}
                          <span className="text-xs text-zinc-400 font-mono">
                            {factor.score !== null ? `${factor.score.toFixed(1)}/10` : "—"}
                          </span>
                        </div>
                      </div>
                      {factor.measured && (
                        <p className="mt-1 text-xs text-zinc-400">
                          Measured: {factor.measured.value} {factor.measured.unit}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {activeDomain?.reasoning && (
                <div className="rounded-xl bg-zinc-950/70 p-3 text-xs text-zinc-400 border border-zinc-800/50 flex items-start gap-2">
                  <Info className="h-4 w-4 shrink-0 text-violet-400 mt-0.5" />
                  <span>
                    <strong className="text-zinc-300">Your data: </strong>
                    {activeDomain.reasoning}
                  </span>
                </div>
              )}
            </div>

            {/* Contribution explanation */}
            {contributionData?.reasoning && (
              <div className="lg:col-span-12 mt-4 pt-4 border-t border-zinc-800/80">
                <div className="rounded-2xl border border-violet-500/20 bg-violet-950/10 p-5">
                  <div className="flex items-center gap-2 text-violet-400 text-xs font-bold uppercase tracking-wider">
                    <Sparkles className="h-4 w-4" />
                    <span>How your contribution score is calculated</span>
                  </div>
                  <p className="mt-2 text-sm text-zinc-300 leading-relaxed">
                    {contributionData.reasoning}
                  </p>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* =========================================================================
            3. STRENGTHS & WEAKNESSES (BENCHMARKED TO IDEAL MIN/MAX)
        ========================================================================= */}
        <section aria-labelledby="benchmarks-title" className="space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <h2 id="benchmarks-title" className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-emerald-400" />
                <span>Your Strengths & Growth Areas</span>
              </h2>
              <p className="text-xs text-zinc-400 mt-1">
                Strengths start at 8/10 and growth areas are scores below 6/10; these are internal practice thresholds.
              </p>
            </div>

            {/* Filter Tabs */}
            <div className="inline-flex rounded-xl bg-zinc-900 p-1 border border-zinc-800 text-xs font-semibold">
              <button
                type="button"
                onClick={() => setBenchmarkFilter("all")}
                className={`rounded-lg px-3 py-1.5 transition ${benchmarkFilter === "all" ? "bg-violet-600 text-white" : "text-zinc-400 hover:text-white"
                  }`}
              >
                All
              </button>
              <button
                type="button"
                onClick={() => setBenchmarkFilter("strengths")}
                className={`rounded-lg px-3 py-1.5 transition ${benchmarkFilter === "strengths" ? "bg-emerald-600 text-white" : "text-zinc-400 hover:text-white"
                  }`}
              >
                Strengths ({benchmarks?.strengths.length || 0})
              </button>
              <button
                type="button"
                onClick={() => setBenchmarkFilter("weaknesses")}
                className={`rounded-lg px-3 py-1.5 transition ${benchmarkFilter === "weaknesses" ? "bg-red-600 text-white" : "text-zinc-400 hover:text-white"
                  }`}
              >
                Weaknesses ({benchmarks?.weaknesses.length || 0})
              </button>
              <button
                type="button"
                onClick={() => setBenchmarkFilter("meets")}
                className={`rounded-lg px-3 py-1.5 transition ${benchmarkFilter === "meets" ? "bg-zinc-700 text-white" : "text-zinc-400 hover:text-white"
                  }`}
              >
                Expected ({benchmarks?.meets_expectation.length || 0})
              </button>
            </div>
          </div>

          {/* Cards Grid */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filteredBenchmarks.map((bm, idx) => {
              const isStrength = bm.category === "Strength";
              const isWeakness = bm.category === "Weakness";

              const badgeColor = isStrength
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                : isWeakness
                  ? "border-red-500/30 bg-red-500/10 text-red-300"
                  : "border-zinc-700 bg-zinc-800 text-zinc-300";

              return (
                <div
                  key={`${bm.key}-${idx}`}
                  className={`rounded-2xl border p-5 flex flex-col justify-between transition ${isStrength
                    ? "border-emerald-500/20 bg-emerald-950/10 hover:border-emerald-500/40"
                    : isWeakness
                      ? "border-red-500/20 bg-red-950/10 hover:border-red-500/40"
                      : "border-zinc-800 bg-zinc-900/40 hover:border-zinc-700"
                    }`}
                >
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <span className="text-xs uppercase font-bold tracking-wider text-zinc-400">{bm.domain}</span>
                      <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${badgeColor}`}>
                        {bm.category}
                      </span>
                    </div>

                    <h4 className="mt-2 text-base font-bold text-white">{bm.name}</h4>

                    <div className="mt-3 flex items-baseline gap-2">
                      <span className="text-2xl font-black text-white">{bm.score.toFixed(1)}</span>
                      <span className="text-xs text-zinc-400">/ 10</span>
                    </div>

                    <div className="mt-3 space-y-2 text-xs leading-relaxed text-zinc-300">
                      <p><strong className="text-zinc-100">What happened: </strong>{bm.what_happened ?? bm.reason}</p>
                      <p><strong className="text-zinc-100">Why it matters: </strong>{bm.why_it_matters ?? "This reflects your measured practice performance."}</p>
                      {bm.what_to_do_next && (
                        <p><strong className="text-zinc-100">What to do next: </strong>{bm.what_to_do_next}</p>
                      )}
                    </div>
                    <span className="mt-3 inline-flex w-fit rounded-full border border-zinc-700/80 px-2 py-0.5 text-[10px] text-zinc-500">
                      {bm.reasoning_source === "llm" ? "AI-assisted wording" : "Data-based"}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Flat-factor Guard Callout */}
          {benchmarks?.insufficient_signal && benchmarks.insufficient_signal.length > 0 && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 text-xs text-zinc-400">
              <span className="font-semibold text-zinc-300">Flat-Factor Guard Notice: </span>
              {benchmarks.insufficient_signal.map((item) => (
                <span key={item.key} className="mr-3">
                  <code className="text-zinc-200">{item.name}</code> (Score: {item.score}) showed ~0 variance and was
                  excluded from strengths/weaknesses to avoid praising defaults.
                </span>
              ))}
            </div>
          )}
        </section>

        {/* =========================================================================
            4. BEHAVIOUR ANALYSIS (FIRST QUESTION, NORMAL, FOLLOWUP, LAST)
        ========================================================================= */}
        <section aria-labelledby="behavior-title" className="space-y-5">
          <div>
            <h2 id="behavior-title" className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              <UserCheck className="h-5 w-5 text-violet-400" />
              <span>              Changes Across Your Interview</span>
            </h2>
            <p className="text-xs text-zinc-400 mt-1">
              Compare the measured scores across your opening, standard, follow-up, and closing answers.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {stages.map((stg, idx) => (
              <div
                key={stg.stage}
                className={`rounded-2xl border p-5 flex flex-col justify-between transition ${
                  stg.available
                    ? "border-zinc-800 bg-zinc-900/50 hover:border-violet-500/30"
                    : "border-zinc-800/60 bg-zinc-950/40 opacity-70"
                }`}
              >
                <div>
                  <div className="flex items-center justify-between text-xs text-zinc-500 font-mono">
                    <span>STAGE 0{idx + 1}</span>
                    {stg.available && stg.question_number !== null && (
                      <span className="rounded bg-zinc-800 px-2 py-0.5 text-zinc-300 font-bold">
                        Q{stg.question_number}
                      </span>
                    )}
                  </div>

                  <h3 className="mt-2 text-sm font-bold text-white">{stg.stage_title}</h3>

                  {stg.available && (
                    <div className="mt-3 inline-block rounded-lg border border-violet-500/20 bg-violet-500/10 px-2.5 py-1 text-xs font-semibold text-violet-300">
                      {stg.presence_status}
                    </div>
                  )}

                  {!stg.available && (
                    <p className="mt-3 text-xs text-zinc-300 leading-relaxed">{stg.short_reason}</p>
                  )}
                  {stg.available && (
                    <div className="mt-3 space-y-2 text-xs leading-relaxed text-zinc-300">
                      {stg.what_happened && <p><strong className="text-zinc-100">What happened: </strong>{stg.what_happened}</p>}
                      {stg.why_it_matters && <p><strong className="text-zinc-100">Why it matters: </strong>{stg.why_it_matters}</p>}
                      {stg.what_to_do_next && <p><strong className="text-zinc-100">What to do next: </strong>{stg.what_to_do_next}</p>}
                    </div>
                  )}
                  {stg.available && stg.stage === "followup_question" && (
                    <div className="mt-3 space-y-2 rounded-lg bg-zinc-950/70 p-3 text-xs text-zinc-400">
                      <p className="text-zinc-300">{stg.question_text}</p>
                      {stg.answer_excerpt && (
                        <p className="border-l border-violet-500/40 pl-2 italic">
                          “{stg.answer_excerpt}”
                        </p>
                      )}
                      <p className="text-[10px] text-zinc-500">
                        {stg.followup_count} follow-up{stg.followup_count === 1 ? "" : "s"} asked
                      </p>
                    </div>
                  )}
                </div>

              </div>
            ))}
          </div>
        </section>

        {/* =========================================================================
            5. IMPROVEMENT SUGGESTIONS: PRESENCE, POSTURE & VOICE
        ========================================================================= */}
        <section aria-labelledby="improvements-title" className="space-y-5">
          <div>
            <h2 id="improvements-title" className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-amber-400" />
              <span>Targeted Improvement Suggestions (Presence, Posture & Voice)</span>
            </h2>
            <p className="text-xs text-zinc-400 mt-1">
              Use these measured scores and practice actions to guide your next attempt.
            </p>
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            {/* Voice Pillar */}
            {pillars?.voice && (
              <div className="rounded-2xl border border-emerald-500/20 bg-emerald-950/10 p-6 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                      <Volume2 className="h-4 w-4" />
                      <span>Voice & Cadence</span>
                    </span>
                    <span className="rounded-full bg-emerald-500/20 px-2.5 py-0.5 text-xs font-bold text-emerald-300 font-mono">
                      {pillars.voice.score !== null ? `${pillars.voice.score}/10` : "Not analysed"}
                    </span>
                  </div>

                  <h3 className="mt-3 text-base font-bold text-white">What to Focus On</h3>
                  <p className="mt-2 text-xs text-zinc-300 leading-relaxed">{pillars.voice.focus}</p>

                  <h4 className="mt-5 text-xs font-bold uppercase tracking-wider text-zinc-400">Actionable Drills:</h4>
                  <ul className="mt-2 space-y-2 text-xs text-zinc-300">
                    {pillars.voice.how_to.map((drill, dIdx) => (
                      <li key={dIdx} className="flex gap-2">
                        <ArrowRight className="h-3.5 w-3.5 shrink-0 text-emerald-400 mt-0.5" />
                        <span>{drill}</span>
                      </li>
                    ))}
                  </ul>
                </div>

              </div>
            )}

            {/* Posture Pillar */}
            {pillars?.posture && (
              <div className="rounded-2xl border border-cyan-500/20 bg-cyan-950/10 p-6 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-1.5">
                      <ShieldCheck className="h-4 w-4" />
                      <span>Posture & Composure</span>
                    </span>
                    <span className="rounded-full bg-cyan-500/20 px-2.5 py-0.5 text-xs font-bold text-cyan-300 font-mono">
                      {pillars.posture.score !== null ? `${pillars.posture.score}/10` : "Not analysed"}
                    </span>
                  </div>

                  <h3 className="mt-3 text-base font-bold text-white">What to Focus On</h3>
                  <p className="mt-2 text-xs text-zinc-300 leading-relaxed">{pillars.posture.focus}</p>

                  <h4 className="mt-5 text-xs font-bold uppercase tracking-wider text-zinc-400">Actionable Drills:</h4>
                  <ul className="mt-2 space-y-2 text-xs text-zinc-300">
                    {pillars.posture.how_to.map((drill, dIdx) => (
                      <li key={dIdx} className="flex gap-2">
                        <ArrowRight className="h-3.5 w-3.5 shrink-0 text-cyan-400 mt-0.5" />
                        <span>{drill}</span>
                      </li>
                    ))}
                  </ul>
                </div>

              </div>
            )}

            {/* Presence Pillar */}
            {pillars?.presence && (
              <div className="rounded-2xl border border-violet-500/20 bg-violet-950/10 p-6 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider text-violet-400 flex items-center gap-1.5">
                      <Eye className="h-4 w-4" />
                      <span>Executive Presence</span>
                    </span>
                    <span className="rounded-full bg-violet-500/20 px-2.5 py-0.5 text-xs font-bold text-violet-300 font-mono">
                      {pillars.presence.score !== null ? `${pillars.presence.score}/10` : "Not analysed"}
                    </span>
                  </div>

                  <h3 className="mt-3 text-base font-bold text-white">What to Focus On</h3>
                  <p className="mt-2 text-xs text-zinc-300 leading-relaxed">{pillars.presence.focus}</p>

                  <h4 className="mt-5 text-xs font-bold uppercase tracking-wider text-zinc-400">Actionable Drills:</h4>
                  <ul className="mt-2 space-y-2 text-xs text-zinc-300">
                    {pillars.presence.how_to.map((drill, dIdx) => (
                      <li key={dIdx} className="flex gap-2">
                        <ArrowRight className="h-3.5 w-3.5 shrink-0 text-violet-400 mt-0.5" />
                        <span>{drill}</span>
                      </li>
                    ))}
                  </ul>
                </div>

              </div>
            )}
          </div>
        </section>

        {insights && (
          <section aria-labelledby="language-analysis-title" className="space-y-4">
            <div>
              <h2 id="language-analysis-title" className="text-xl font-bold tracking-tight text-white">
                Hindi–English Transcription & Code-Switching
              </h2>
              <p className="mt-1 text-sm text-zinc-300">
                {insights.language_analysis?.transcription_method
                  || "Interview audio uses multilingual Whisper with Hindi-English language auto-detection. Code-switching is counted from the selected transcript."}
              </p>
            </div>
            {insights.language_analysis?.data_available ? (
              <>
                <p className="text-sm text-zinc-300">
                  {insights.language_analysis.summary}
                </p>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  {[
                    ["Dominant language", insights.language_analysis.dominant_language],
                    ["English words", `${insights.language_analysis.english_word_count} (${insights.language_analysis.english_word_percentage}%)`],
                    ["Hindi words", `${insights.language_analysis.hindi_word_count} (${insights.language_analysis.hindi_word_percentage}%)`],
                    ["Language switches", String(insights.language_analysis.code_switching_count)],
                  ].map(([label, value]) => (
                    <div key={label} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
                      <p className="text-xs uppercase tracking-wide text-zinc-400">{label}</p>
                      <p className="mt-1 text-lg font-semibold capitalize text-white">{value}</p>
                    </div>
                  ))}
                </div>
                {insights.language_analysis.language_switching_examples.length > 0 && (
                  <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
                    <h3 className="text-sm font-semibold text-white">Detected switching examples</h3>
                    <ul className="mt-2 flex flex-wrap gap-2">
                      {insights.language_analysis.language_switching_examples.map((item, index) => (
                        <li key={`${item.question_number}-${item.example}-${index}`} className="rounded-lg bg-zinc-950 px-3 py-1.5 text-xs text-zinc-300">
                          Q{item.question_number}: {item.example}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            ) : (
              <div className="rounded-xl border border-amber-500/20 bg-amber-950/10 p-4 text-sm text-amber-100">
                Hindi-English switch counts are unavailable because there was not
                enough analyzable transcript text in this report.
              </div>
            )}
            <div className="rounded-xl border border-cyan-500/20 bg-cyan-950/10 p-4">
              <h3 className="text-sm font-semibold text-cyan-200">Code-switching feedback</h3>
              <p className="mt-1 text-sm text-zinc-300">
                {insights.language_analysis?.feedback
                  || "Language-pattern feedback will appear after transcript analysis completes."}
              </p>
            </div>
            <p className="text-xs text-zinc-500">
              {insights.language_analysis?.interpretation_note
                || "Language-pattern metrics describe the transcript and do not measure technical ability."}
            </p>
          </section>
        )}

        {/* =========================================================================
            6. QUESTION-WISE SCORES (FOCUSED ON ANSWER EVALUATION)
        ========================================================================= */}
        <section aria-labelledby="questions-title" className="space-y-5">
          <div>
            <h2 id="questions-title" className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              <FileText className="h-5 w-5 text-violet-400" />
              <span>Question-by-Question Technical Answer Evaluations</span>
            </h2>
            <p className="text-xs text-zinc-400 mt-1">
              Detailed technical correctness, completeness, and model answers across each answered question
            </p>
          </div>

          <div className="space-y-4">
            {attemptedQuestions.length === 0 ? (
              <div className="rounded-2xl border border-zinc-800 bg-zinc-900/30 p-8 text-center text-zinc-400">
                No answered questions were recorded for this session.
              </div>
            ) : (
              attemptedQuestions.map((q) => {
                const qNum = q.question_order;
                const ansEval = q.answer_evaluation as Record<string, unknown> | null;
                const languageEval = q.nlp_evaluation as Record<string, unknown> | null;
                const rating = ansEval ? numVal(ansEval.rating) : null;
                const correctness = ansEval ? numVal(ansEval.correctness) : null;
                const completeness = ansEval ? numVal(ansEval.completeness) : null;
                const relevance = ansEval ? numVal(ansEval.relevance) : null;
                const understanding = ansEval ? numVal(ansEval.technical_understanding) : null;
                const verdict = ansEval ? String(ansEval.verdict || "Evaluated") : "Attempted";
                const isExpanded = !!expandedQuestions[qNum];
                const hindiWordCount = languageEval
                  ? numVal(languageEval.hindi_word_count)
                  : null;
                const englishWordCount = languageEval
                  ? numVal(languageEval.english_word_count)
                  : null;
                const hindiWordCounts = parseCountMap(languageEval?.hindi_words);
                const englishWordCounts = parseCountMap(languageEval?.english_words);
                const switchingExamples = parseStringList(
                  languageEval?.language_switching_examples
                );
                const wordLanguageLabels = parseWordLabels(
                  languageEval?.word_language_identification
                );

                return (
                  <div
                    key={q.id}
                    className="rounded-2xl border border-zinc-800 bg-zinc-900/40 overflow-hidden transition"
                  >
                    {/* Card Header Accordion Bar */}
                    <button
                      type="button"
                      onClick={() => toggleQuestion(qNum)}
                      className="w-full p-5 flex items-center justify-between text-left hover:bg-zinc-800/30 transition"
                    >
                      <div className="flex items-center gap-4">
                        <span className="h-9 w-9 rounded-xl bg-violet-600/20 text-violet-400 font-bold flex items-center justify-center text-sm border border-violet-500/30">
                          {qNum}
                        </span>
                        <div>
                          <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                            Question {qNum} • {q.source}
                          </span>
                          <h3 className="text-base font-semibold text-white line-clamp-1">{q.question_text}</h3>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        <div className="text-right">
                          <div className="text-base font-black text-white">
                            {rating !== null ? `${rating.toFixed(1)}/10` : "—"}
                          </div>
                          <div className="text-[11px] font-semibold capitalize text-emerald-400">{verdict}</div>
                        </div>
                        {isExpanded ? (
                          <ChevronUp className="h-5 w-5 text-zinc-400" />
                        ) : (
                          <ChevronDown className="h-5 w-5 text-zinc-400" />
                        )}
                      </div>
                    </button>

                    {/* Expanded Body: Strictly Answer Evaluation Focus */}
                    {isExpanded && (
                      <div className="p-5 pt-0 border-t border-zinc-800/80 space-y-5">
                        {/* Full Question & Transcript */}
                        <div className="mt-4 space-y-3">
                          <div className="rounded-xl bg-zinc-950/80 p-4 border border-zinc-800/60">
                            <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Full Prompt</span>
                            <p className="mt-1 text-sm text-zinc-200">{q.question_text}</p>
                          </div>

                          {q.transcript_text && (
                            <div className="rounded-xl bg-zinc-950/40 p-4 border border-zinc-800/40">
                              <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider">
                                Candidate Transcript
                                <span className="ml-2 rounded-full border border-violet-500/30 px-2 py-0.5 text-[10px] text-violet-300 normal-case">
                                  {q.transcript_source === "whisper"
                                    ? `Whisper · ${
                                        q.transcript_languages?.length
                                          ? q.transcript_languages.map((language) => (
                                              language === "hi" ? "Hindi"
                                                : language === "en" ? "English"
                                                  : language
                                            )).join(" + ")
                                          : "Hindi/English auto-detect"
                                      }`
                                    : "Live transcript"}
                                </span>
                              </span>
                              <p className="mt-1 text-xs text-zinc-400 italic leading-relaxed">
                                &ldquo;{q.transcript_text}&rdquo;
                              </p>
                            </div>
                          )}
                        </div>

                        {languageEval && (hindiWordCount !== null || englishWordCount !== null) && (
                          <div className="rounded-xl border border-cyan-500/20 bg-cyan-950/10 p-4">
                            <h4 className="text-xs font-bold uppercase tracking-wider text-cyan-300">
                              Language pattern
                            </h4>
                            <div className="mt-3 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                              <div>
                                <span className="text-xs text-zinc-400">Dominant</span>
                                <p className="font-semibold capitalize text-white">
                                  {String(languageEval.dominant_language || "unknown")}
                                </p>
                              </div>
                              <div>
                                <span className="text-xs text-zinc-400">English</span>
                                <p className="font-semibold text-white">
                                  {englishWordCount ?? 0} ({((numVal(languageEval.english_word_ratio) ?? 0) * 100).toFixed(1)}%)
                                </p>
                              </div>
                              <div>
                                <span className="text-xs text-zinc-400">Hindi</span>
                                <p className="font-semibold text-white">
                                  {hindiWordCount ?? 0} ({((numVal(languageEval.hindi_word_ratio) ?? 0) * 100).toFixed(1)}%)
                                </p>
                              </div>
                              <div>
                                <span className="text-xs text-zinc-400">Hindi-English switches</span>
                                <p className="font-semibold text-white">
                                  {numVal(languageEval.code_switching_count) ?? 0}
                                </p>
                              </div>
                            </div>
                            {(Object.keys(hindiWordCounts).length > 0 || Object.keys(englishWordCounts).length > 0) && (
                              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                                {[
                                  ["Detected Hindi words", hindiWordCounts],
                                  ["Detected English words", englishWordCounts],
                                ].map(([title, counts]) => (
                                  <div key={title as string}>
                                    <p className="text-xs font-medium text-zinc-400">{title as string}</p>
                                    <p className="mt-1 text-xs text-zinc-300">
                                      {Object.entries(counts as Record<string, number>)
                                        .slice(0, 10)
                                        .map(([word, count]) => `${word} (${count})`)
                                        .join(", ") || "None detected"}
                                    </p>
                                  </div>
                                ))}
                              </div>
                            )}
                            {switchingExamples.length > 0 && (
                              <p className="mt-3 text-xs text-zinc-300">
                                <span className="font-semibold text-zinc-100">Switches: </span>
                                {switchingExamples.slice(0, 8).join("; ")}
                              </p>
                            )}
                            {wordLanguageLabels.length > 0 && (
                              <div className="mt-3">
                                <p className="text-xs font-medium text-zinc-400">Word-level identification</p>
                                <div className="mt-1 flex flex-wrap gap-1.5">
                                  {wordLanguageLabels.slice(0, 40).map((item, index) => (
                                    <span
                                      key={`${item.word}-${index}`}
                                      className={`rounded px-1.5 py-0.5 text-[10px] ${
                                        item.language === "hindi"
                                          ? "bg-amber-500/10 text-amber-200"
                                          : item.language === "english"
                                            ? "bg-cyan-500/10 text-cyan-200"
                                            : "bg-zinc-800 text-zinc-400"
                                      }`}
                                    >
                                      {item.word}: {item.language}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                            <p className="mt-3 text-[11px] text-zinc-500">
                              This describes language use only; it is not a technical-ability or intelligibility score.
                            </p>
                          </div>
                        )}

                        {!ansEval && (
                          <div className="rounded-xl border border-amber-500/20 bg-amber-950/10 p-4">
                            <span className="text-xs font-bold uppercase tracking-wider text-amber-300">
                              Technical feedback unavailable
                            </span>
                            <p className="mt-1 text-sm leading-relaxed text-zinc-300">
                              This answer did not have a reliable transcript, so it was not scored.
                            </p>
                          </div>
                        )}

                        {/* Technical Rubric Score Tiles */}
                        {ansEval && (
                          <div className="space-y-4">
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                              <div className="rounded-xl bg-zinc-950/60 p-3 border border-zinc-800/60 text-center">
                                <span className="text-[11px] text-zinc-500 uppercase font-semibold">Correctness</span>
                                <div className="text-lg font-bold text-white mt-1">
                                  {correctness !== null ? `${correctness.toFixed(1)}/10` : "—"}
                                </div>
                              </div>
                              <div className="rounded-xl bg-zinc-950/60 p-3 border border-zinc-800/60 text-center">
                                <span className="text-[11px] text-zinc-500 uppercase font-semibold">Completeness</span>
                                <div className="text-lg font-bold text-white mt-1">
                                  {completeness !== null ? `${completeness.toFixed(1)}/10` : "—"}
                                </div>
                              </div>
                              <div className="rounded-xl bg-zinc-950/60 p-3 border border-zinc-800/60 text-center">
                                <span className="text-[11px] text-zinc-500 uppercase font-semibold">Relevance</span>
                                <div className="text-lg font-bold text-white mt-1">
                                  {relevance !== null ? `${relevance.toFixed(1)}/10` : "—"}
                                </div>
                              </div>
                              <div className="rounded-xl bg-zinc-950/60 p-3 border border-zinc-800/60 text-center">
                                <span className="text-[11px] text-zinc-500 uppercase font-semibold">Understanding</span>
                                <div className="text-lg font-bold text-white mt-1">
                                  {understanding !== null
                                    ? `${understanding.toFixed(1)}/10`
                                    : "—"}
                                </div>
                              </div>
                            </div>

                            {/* Technical Feedback */}
                            {Boolean(ansEval.feedback) && (
                              <div className="rounded-xl border border-violet-500/20 bg-violet-950/10 p-4">
                                <span className="text-xs font-bold text-violet-400 uppercase tracking-wider">
                                  Technical Evaluator Feedback
                                </span>
                                <p className="mt-1 text-sm text-zinc-300 leading-relaxed">
                                  {String(ansEval.feedback)}
                                </p>
                              </div>
                            )}

                            {/* Missing Concepts or Ideal Answer */}
                            {Boolean(ansEval.ideal_answer) && (
                              <div className="rounded-xl border border-emerald-500/20 bg-emerald-950/10 p-4">
                                <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">
                                  Example Answer
                                </span>
                                <p className="mt-1 text-xs text-zinc-300 leading-relaxed font-mono whitespace-pre-wrap">
                                  {String(ansEval.ideal_answer)}
                                </p>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </section>

        {insights?.evidence && (
          <details className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5">
            <summary className="cursor-pointer text-sm font-semibold text-zinc-200">
              How we measure this
            </summary>
            <ul className="mt-4 space-y-3 text-xs leading-5 text-zinc-400">
              {insights.evidence.map((item) => (
                <li key={item.source}>
                  <strong className="text-zinc-300">{item.source}: </strong>
                  {item.note}
                </li>
              ))}
            </ul>
          </details>
        )}

        {/* Footer */}
        <footer className="pt-8 border-t border-zinc-900 text-center text-xs text-zinc-500 print:text-zinc-600">
          <div className="mb-6 flex flex-wrap justify-center gap-3 print:hidden">
            <Link
              href="/"
              className="rounded-lg border border-zinc-700 px-4 py-2 text-sm font-semibold text-zinc-300 transition hover:bg-zinc-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet-400"
            >
              Back to Home
            </Link>
            <Link
              href="/history"
              className="rounded-lg border border-zinc-700 px-4 py-2 text-sm font-semibold text-zinc-300 transition hover:bg-zinc-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet-400"
            >
              Past interviews
            </Link>
          </div>
          {insights?.disclaimer ?? "Practice feedback from automated analysis of sampled answers, not a hiring prediction."}
        </footer>
      </div>
    </main>
  );
}

export default function InterviewResultsPage() {
  return (
    <AuthGuard>
      <ResultsContent />
    </AuthGuard>
  );
}
