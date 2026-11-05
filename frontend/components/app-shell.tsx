"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpen, ChevronDown, FileText, Home, Menu, Mic2, ShieldCheck, X } from "lucide-react";
import { useAuth } from "@/lib/auth";

const links = [
  { href: "/", label: "Home", icon: Home },
  { href: "/resume", label: "Resume", icon: FileText },
  { href: "/interview", label: "Take interview", icon: Mic2 },
  { href: "/history", label: "Past interviews", icon: BookOpen },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, signOut } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [showPrivacyModal, setShowPrivacyModal] = useState(false);
  const [showTosModal, setShowTosModal] = useState(false);

  return (
    <div className="flex min-h-screen flex-col bg-[#0a0d14] text-slate-100">
      <header className="sticky top-0 z-40 border-b border-slate-800 bg-[#0a0d14] print:hidden">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
          <Link href="/" className="flex shrink-0 items-center gap-2.5" aria-label="HireSense AI home">
            <span className="grid h-8 w-8 place-items-center rounded-md bg-blue-600 text-sm font-bold text-white shadow-sm">
              H
            </span>
            <span className="text-sm font-bold tracking-tight text-white sm:text-base">
              HireSense <span className="font-semibold text-blue-400">AI</span>
            </span>
          </Link>

          <nav aria-label="Main navigation" className="hidden items-center gap-1 lg:flex">
            {links.map(({ href, label, icon: Icon }) => {
              const active = href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
              return (
                <Link
                  key={href}
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={`inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-xs font-medium transition ${
                    active
                      ? "bg-slate-800 text-white"
                      : "text-slate-400 hover:bg-slate-850 hover:text-slate-200"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                  {label}
                </Link>
              );
            })}
          </nav>

          <div className="relative flex items-center gap-2">
            <button
              type="button"
              onClick={() => setAccountOpen((open) => !open)}
              aria-expanded={accountOpen}
              aria-label="Account menu"
              className="hidden items-center gap-2 rounded-md border border-slate-800 bg-slate-900 px-2.5 py-1.5 text-left hover:bg-slate-800 sm:flex"
            >
              <span className="grid h-6 w-6 place-items-center rounded bg-blue-900/50 text-xs font-bold text-blue-300 border border-blue-700/50">
                {(user?.full_name || user?.email || "C").slice(0, 1).toUpperCase()}
              </span>
              <span className="hidden max-w-28 truncate text-xs font-medium text-slate-200 xl:block">
                {user?.full_name || "Candidate"}
              </span>
              <ChevronDown className="h-3 w-3 text-slate-400" aria-hidden="true" />
            </button>
            <button
              type="button"
              onClick={() => setMobileOpen((open) => !open)}
              aria-label={mobileOpen ? "Close navigation menu" : "Open navigation menu"}
              aria-expanded={mobileOpen}
              className="grid h-9 w-9 place-items-center rounded-md border border-slate-800 text-slate-300 hover:bg-slate-800 lg:hidden"
            >
              {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
            {accountOpen && (
              <div className="absolute right-0 top-11 z-50 w-52 rounded-md border border-slate-800 bg-[#101522] p-1.5 shadow-lg">
                <p className="truncate px-2.5 py-1.5 text-xs text-slate-400">{user?.email}</p>
                <div className="my-1 border-t border-slate-800" />
                <button
                  type="button"
                  onClick={signOut}
                  className="w-full rounded px-2.5 py-1.5 text-left text-xs font-medium text-slate-200 hover:bg-slate-800"
                >
                  Sign out
                </button>
              </div>
            )}
          </div>
        </div>
        {mobileOpen && (
          <nav aria-label="Mobile navigation" className="border-t border-slate-800 bg-[#0a0d14] px-4 py-2.5 lg:hidden">
            <div className="mx-auto grid max-w-7xl gap-1 sm:grid-cols-2">
              {links.map(({ href, label, icon: Icon }) => {
                const active = href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
                return (
                  <Link
                    key={href}
                    href={href}
                    onClick={() => setMobileOpen(false)}
                    aria-current={active ? "page" : undefined}
                    className={`flex items-center gap-2.5 rounded-md px-3 py-2 text-xs font-medium ${
                      active ? "bg-slate-800 text-white" : "text-slate-400 hover:bg-slate-850"
                    }`}
                  >
                    <Icon className="h-4 w-4" aria-hidden="true" />
                    {label}
                  </Link>
                );
              })}
              <button
                type="button"
                onClick={signOut}
                className="rounded-md px-3 py-2 text-left text-xs font-medium text-slate-400 hover:bg-slate-850 sm:col-span-2"
              >
                Sign out
              </button>
            </div>
          </nav>
        )}
      </header>

      <div className="flex-1">{children}</div>

      <footer className="mt-auto border-t border-slate-800 bg-[#0a0d14] py-6 text-xs text-slate-400 print:hidden">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-4 sm:flex-row sm:px-6 lg:px-8">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-300">HireSense AI</span>
            <span>·</span>
            <span>Multi-Agent Interview & Career Simulation Platform</span>
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
                  All session histories, feedback, and transcripts are strictly scoped to your authenticated account ID. You may request full account deletion at any time, which cascades across all session records.
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
                  This service is intended solely for interview practice, skill assessment, and candidate self-improvement. Feedback generated by the multi-agent system serves as educational guidance.
                </p>
              </div>
              <div>
                <h3 className="font-semibold text-white">2. Fair Usage</h3>
                <p className="mt-1 text-slate-400">
                  Users agree to use the service in accordance with standard academic and professional standards. Automated scraping or denial-of-service attempts are strictly prohibited.
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
