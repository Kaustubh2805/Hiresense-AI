"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { GoogleLogin } from "@react-oauth/google";
import { ArrowRight, AudioLines, BookOpen, Clock, FileText, Mic, ShieldCheck, Video, X } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { Badge, Button, Card } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { GOOGLE_CLIENT_ID } from "@/lib/config";

function RealProductPreview() {
  return (
    <div className="w-full rounded-lg border border-slate-800 bg-[#101522] p-5 shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3.5">
        <div className="flex items-center gap-2.5">
          <span className="h-2 w-2 rounded-full bg-emerald-400" />
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
            Active Interview Simulation
          </span>
        </div>
        <div className="flex items-center gap-3 text-xs text-slate-400">
          <span className="inline-flex items-center gap-1">
            <Clock className="h-3.5 w-3.5 text-slate-400" /> 02:45
          </span>
          <Badge tone="brand">Question 2 of 5</Badge>
        </div>
      </div>

      <div className="mt-4 rounded-md border border-slate-800 bg-[#0a0d14] p-4">
        <div className="flex items-center justify-between">
          <p className="text-[11px] font-medium uppercase tracking-wider text-blue-400">
            Interviewer · Lead Architect Agent
          </p>
          <span className="text-[11px] text-slate-400">Target Role: Senior Full Stack Engineer</span>
        </div>
        <p className="mt-2.5 text-sm font-medium leading-relaxed text-slate-100">
          "How would you approach handling state synchronization and cache invalidation when scaling a distributed client-server application under high concurrency?"
        </p>
      </div>

      <div className="mt-3.5 grid grid-cols-2 gap-3 text-xs">
        <div className="rounded-md border border-slate-800 bg-[#0a0d14] p-3">
          <div className="flex items-center justify-between text-slate-400">
            <span className="flex items-center gap-1.5 font-medium text-slate-300">
              <Mic className="h-3.5 w-3.5 text-blue-400" /> Speech Cadence
            </span>
            <span className="font-semibold text-emerald-400">Optimal (135 WPM)</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">
            Real-time faster-whisper transcription with Silero-VAD segmenting.
          </p>
        </div>

        <div className="rounded-md border border-slate-800 bg-[#0a0d14] p-3">
          <div className="flex items-center justify-between text-slate-400">
            <span className="flex items-center gap-1.5 font-medium text-slate-300">
              <Video className="h-3.5 w-3.5 text-blue-400" /> Non-Verbal Signals
            </span>
            <span className="font-semibold text-blue-400">8.4 / 10 Gaze</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">
            MediaPipe FaceMesh & Pose stability (ephemeral, zero video stored).
          </p>
        </div>
      </div>

      <div className="mt-3.5 flex items-center justify-between rounded-md border border-slate-800 bg-slate-900/60 px-3.5 py-2.5 text-xs text-slate-400">
        <span className="flex items-center gap-2">
          <AudioLines className="h-3.5 w-3.5 text-slate-300" /> Adaptive Follow-up Logic Armed
        </span>
        <span className="text-[11px] font-medium text-slate-300">Rubric: LangGraph State Machine</span>
      </div>
    </div>
  );
}

export default function HomePage() {
  const { token, user, loading, signIn } = useAuth();
  const [signInError, setSignInError] = useState("");
  const [signingIn, setSigningIn] = useState(false);
  const [showPrivacyModal, setShowPrivacyModal] = useState(false);
  const [showTosModal, setShowTosModal] = useState(false);

  useEffect(() => {
    try {
      sessionStorage.removeItem("hiresense_interview_complete");
    } catch (storageError) {
      console.warn("[home] Could not clear interview completion flag:", storageError);
    }
  }, []);

  if (loading) {
    return (
      <main className="grid min-h-screen place-items-center bg-[#0a0d14] text-xs font-medium text-slate-400" role="status">
        <div className="flex items-center gap-2">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
          <span>Authenticating HireSense session…</span>
        </div>
      </main>
    );
  }

  if (!token || !user) {
    return (
      <div className="flex min-h-screen flex-col bg-[#0a0d14] text-slate-100">
        <header className="border-b border-slate-800 bg-[#0a0d14] px-4 py-3.5 sm:px-6 lg:px-8">
          <div className="mx-auto flex max-w-7xl items-center justify-between">
            <Link href="/" className="flex items-center gap-2.5">
              <span className="grid h-8 w-8 place-items-center rounded-md bg-blue-600 text-sm font-bold text-white shadow-sm">
                H
              </span>
              <span className="text-sm font-bold tracking-tight text-white sm:text-base">
                HireSense <span className="font-semibold text-blue-400">AI</span>
              </span>
            </Link>
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded border border-slate-700 bg-slate-850 px-2.5 py-1 text-xs font-medium text-slate-300">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                Zero-Persistence Privacy
              </span>
            </div>
          </div>
        </header>

        <main className="flex-1 px-4 py-12 sm:px-6 lg:px-8">
          <section className="mx-auto grid max-w-7xl items-center gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:gap-14">
            <div className="max-w-xl">
              <p className="text-xs font-semibold uppercase tracking-wider text-blue-400">
                Multi-Agent Interview & Career Simulation
              </p>
              <h1 className="mt-3 text-3xl font-bold tracking-tight text-white sm:text-5xl">
                Rigorous interview practice with real-time feedback.
              </h1>
              <p className="mt-4 text-base leading-relaxed text-slate-300">
                Practice role-specific technical interviews with adaptive follow-ups, precise speech transcription, and comprehensive rubric evaluation.
              </p>

              <div className="mt-6 flex flex-wrap gap-2 text-xs">
                <span className="rounded border border-slate-800 bg-slate-900 px-2.5 py-1 text-slate-300">
                  Adaptive Follow-Up Questions
                </span>
                <span className="rounded border border-slate-800 bg-slate-900 px-2.5 py-1 text-slate-300">
                  Non-Verbal Engagement Scoring
                </span>
                <span className="rounded border border-slate-800 bg-slate-900 px-2.5 py-1 text-slate-300">
                  Detailed Rubric Reports
                </span>
              </div>

              <Card className="mt-8 max-w-md p-5">
                <h2 className="text-sm font-semibold text-white">Sign In to Practice Space</h2>
                <p className="mt-1 text-xs text-slate-400">
                  Your interview sessions, transcripts, and evaluation history are private to your account.
                </p>
                <div className={`mt-4 flex min-h-10 items-center ${signingIn ? "pointer-events-none opacity-60" : ""}`}>
                  {GOOGLE_CLIENT_ID ? (
                    <GoogleLogin
                      onSuccess={async ({ credential }) => {
                        if (!credential) {
                          setSignInError("Google did not return a sign-in credential.");
                          return;
                        }
                        setSigningIn(true);
                        setSignInError("");
                        try {
                          await signIn(credential);
                        } catch (error) {
                          setSignInError(error instanceof Error ? error.message : "Google sign-in failed.");
                        } finally {
                          setSigningIn(false);
                        }
                      }}
                      onError={() => setSignInError("Google sign-in could not be completed. Please try again.")}
                      text="continue_with"
                      shape="rectangular"
                      theme="filled_black"
                    />
                  ) : (
                    <p className="rounded border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs leading-normal text-amber-200">
                      Google sign-in is not configured. Set NEXT_PUBLIC_GOOGLE_CLIENT_ID in frontend/.env.local.
                    </p>
                  )}
                </div>
                {signingIn && <p role="status" className="mt-2.5 text-xs text-slate-400">Signing you in…</p>}
                {signInError && <p role="alert" className="mt-2.5 text-xs text-rose-300">{signInError}</p>}
              </Card>

              <div className="mt-4 flex items-center gap-2 text-xs text-slate-400">
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                <span>Camera & microphone data processed ephemerally. Raw video is never stored.</span>
              </div>
            </div>

            <RealProductPreview />
          </section>
        </main>

        <footer className="border-t border-slate-800 bg-[#0a0d14] py-6 text-xs text-slate-400">
          <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-4 sm:flex-row sm:px-6 lg:px-8">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-300">HireSense AI</span>
              <span>·</span>
              <span>Academic Capstone Project</span>
            </div>
            <div className="flex items-center gap-5">
              <button
                type="button"
                onClick={() => setShowPrivacyModal(true)}
                className="text-slate-400 hover:text-slate-200 underline-offset-4 hover:underline"
              >
                Privacy Policy
              </button>
              <button
                type="button"
                onClick={() => setShowTosModal(true)}
                className="text-slate-400 hover:text-slate-200 underline-offset-4 hover:underline"
              >
                Terms of Service
              </button>
            </div>
          </div>
        </footer>

        {showPrivacyModal && (
          <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4">
            <div className="max-h-[85vh] w-full max-w-xl overflow-y-auto rounded-lg border border-slate-800 bg-[#101522] p-6 shadow-2xl">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-5 w-5 text-emerald-400" />
                  <h2 className="text-base font-semibold text-white">Privacy Policy & Data Security</h2>
                </div>
                <button
                  type="button"
                  onClick={() => setShowPrivacyModal(false)}
                  className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="mt-4 space-y-3.5 text-xs leading-relaxed text-slate-300">
                <p>
                  HireSense AI is an academic research and interview simulation platform designed with strict zero-persistence privacy guarantees per TRD §15 and Backend Schema §9.
                </p>
                <div>
                  <h3 className="font-semibold text-white">1. Vision & Audio Consent (FR-7.1)</h3>
                  <p className="mt-1 text-slate-400">
                    Camera and microphone feeds are optional and require explicit, active candidate consent. The platform enforces consent checks server-side on every sample write.
                  </p>
                </div>
                <div>
                  <h3 className="font-semibold text-white">2. Ephemeral Processing & Zero Video Storage</h3>
                  <p className="mt-1 text-slate-400">
                    Raw video and audio streams are processed ephemerally in real time. We never persist raw candidate video or audio files. Only derived numerical engagement signals (e.g., eye contact stability, posture confidence) and interview transcripts are stored.
                  </p>
                </div>
                <div>
                  <h3 className="font-semibold text-white">3. User Isolation & Data Rights</h3>
                  <p className="mt-1 text-slate-400">
                    All session histories, feedback, and transcripts are strictly scoped to your authenticated account ID.
                  </p>
                </div>
              </div>
              <div className="mt-6 flex justify-end border-t border-slate-800 pt-3">
                <button
                  type="button"
                  onClick={() => setShowPrivacyModal(false)}
                  className="rounded-md border border-slate-700 bg-slate-800 px-3.5 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}

        {showTosModal && (
          <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4">
            <div className="max-h-[85vh] w-full max-w-xl overflow-y-auto rounded-lg border border-slate-800 bg-[#101522] p-6 shadow-2xl">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h2 className="text-base font-semibold text-white">Terms of Service</h2>
                <button
                  type="button"
                  onClick={() => setShowTosModal(false)}
                  className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="mt-4 space-y-3.5 text-xs leading-relaxed text-slate-300">
                <p>
                  HireSense AI is provided free of charge as an educational and technical interview coaching platform.
                </p>
                <div>
                  <h3 className="font-semibold text-white">1. Intended Use</h3>
                  <p className="mt-1 text-slate-400">
                    This service is intended solely for interview practice, skill assessment, and candidate self-improvement.
                  </p>
                </div>
                <div>
                  <h3 className="font-semibold text-white">2. Fair Usage</h3>
                  <p className="mt-1 text-slate-400">
                    Users agree to use the service in accordance with standard academic and professional standards.
                  </p>
                </div>
              </div>
              <div className="mt-6 flex justify-end border-t border-slate-800 pt-3">
                <button
                  type="button"
                  onClick={() => setShowTosModal(false)}
                  className="rounded-md border border-slate-700 bg-slate-800 px-3.5 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <section className="rounded-lg border border-slate-800 bg-[#101522] p-6 sm:p-8">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-blue-400">Candidate Dashboard</p>
              <h1 className="mt-1.5 text-2xl font-bold tracking-tight text-white sm:text-3xl">
                Welcome back{user.full_name ? `, ${user.full_name.split(" ")[0]}` : ""}.
              </h1>
              <p className="mt-1.5 text-xs text-slate-400">
                Select your target profile and resume to begin a simulated technical interview.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Badge tone={user.has_resume ? "success" : "warning"}>
                {user.has_resume ? "Resume Profile Ready" : "Resume Not Uploaded"}
              </Badge>
            </div>
          </div>
        </section>

        <section className="mt-8 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <Card className="flex flex-col justify-between p-5">
            <div>
              <div className="flex items-center justify-between">
                <span className="grid h-8 w-8 place-items-center rounded bg-blue-600/20 text-blue-400">
                  <Mic className="h-4 w-4" />
                </span>
                <Badge tone="brand">Simulate</Badge>
              </div>
              <h2 className="mt-4 text-base font-semibold text-white">Start New Interview</h2>
              <p className="mt-2 text-xs leading-relaxed text-slate-400">
                Begin a role-tailored technical interview with dynamic follow-up questioning and real-time signals.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-slate-800/80">
              <Link href="/interview">
                <Button className="w-full">
                  Enter Interview Studio <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </Link>
            </div>
          </Card>

          <Card className="flex flex-col justify-between p-5">
            <div>
              <div className="flex items-center justify-between">
                <span className="grid h-8 w-8 place-items-center rounded bg-slate-800 text-slate-300">
                  <FileText className="h-4 w-4" />
                </span>
                <Badge tone="neutral">Profile</Badge>
              </div>
              <h2 className="mt-4 text-base font-semibold text-white">Resume & Skill Extraction</h2>
              <p className="mt-2 text-xs leading-relaxed text-slate-400">
                Upload your latest PDF resume to extract skills, project context, and custom interview focuses.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-slate-800/80">
              <Link href="/resume">
                <Button variant="secondary" className="w-full">
                  Manage Resume Profile <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </Link>
            </div>
          </Card>

          <Card className="flex flex-col justify-between p-5">
            <div>
              <div className="flex items-center justify-between">
                <span className="grid h-8 w-8 place-items-center rounded bg-slate-800 text-slate-300">
                  <BookOpen className="h-4 w-4" />
                </span>
                <Badge tone="neutral">History</Badge>
              </div>
              <h2 className="mt-4 text-base font-semibold text-white">Past Sessions & Evaluation</h2>
              <p className="mt-2 text-xs leading-relaxed text-slate-400">
                Review past interview sessions, question transcripts, audio pacing, and MediaPipe non-verbal scores.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-slate-800/80">
              <Link href="/history">
                <Button variant="secondary" className="w-full">
                  View Past Sessions <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </Link>
            </div>
          </Card>
        </section>

        <section className="mt-6">
          <div className="rounded-lg border border-slate-800 bg-[#101522] p-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-400">
            <div className="flex items-center gap-2.5">
              <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0" />
              <span>
                Privacy compliance verified: Server-side vision consent enforced (FR-7.1), zero raw video persisted (TRD §15).
              </span>
            </div>
            <span className="shrink-0 text-slate-400 font-medium">PostgreSQL Checkpoint Active</span>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
