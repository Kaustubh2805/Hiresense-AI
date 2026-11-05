"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { AuthGuard } from "@/components/auth-guard";
import { Badge, Button, Card, PageHeader, ProgressBar } from "@/components/ui";
import { apiFetch } from "@/lib/api";
import { API_BASE_URL } from "@/lib/config";
import { ArrowUpRight, FileCheck2, FileText, FileUp } from "lucide-react";

type Experience = {
  title: string;
  company: string;
  duration: string;
  highlights: string[];
};

type ResumeProfile = {
  skills: string[];
  experiences: Experience[];
  education: string[];
  summary: string;
  total_years_experience: number;
  filename: string | null;
  updated_at: string | null;
  parse_quality?: "full" | "basic";
};

function ResumePageContent() {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [profile, setProfile] = useState<ResumeProfile | null>(null);
  const [skills, setSkills] = useState<string[]>([]);
  const [newSkill, setNewSkill] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [savingSkills, setSavingSkills] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    async function loadProfile() {
      try {
        const response = await apiFetch("/me/profile", { cache: "no-store" });
        if (!response.ok) throw new Error("Could not load your saved resume profile.");
        const result = (await response.json()) as ResumeProfile;
        setProfile(result);
        setSkills(result.skills || []);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Could not load your profile.");
      } finally {
        setLoading(false);
      }
    }
    void loadProfile();
  }, []);

  function chooseFile(file: File | undefined) {
    if (!file) return;
    setError(null);
    setNotice(null);
    if (!/\.(pdf|docx)$/i.test(file.name)) {
      setError("Choose a PDF or DOCX file.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setError("Resume must be 5 MB or smaller.");
      return;
    }
    setSelectedFile(file);
  }

  function uploadResume() {
    if (!selectedFile || uploading) return;
    setUploading(true);
    setProgress(0);
    setError(null);
    setNotice(null);
    const body = new FormData();
    body.append("file", selectedFile);

    let token: string | null = null;
    try {
      token = localStorage.getItem("hiresense_access_token");
    } catch (storageError) {
      setUploading(false);
      setError("Could not access the saved sign-in session.");
      console.error("[resume] Could not read token:", storageError);
      return;
    }
    const request = new XMLHttpRequest();
    request.open("POST", `${API_BASE_URL}/me/resume`);
    if (token) request.setRequestHeader("Authorization", `Bearer ${token}`);
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) setProgress(Math.round((event.loaded / event.total) * 100));
    };
    request.onerror = () => {
      setUploading(false);
      setError("Resume upload failed. Check your connection and try again.");
    };
    request.onload = () => {
      setUploading(false);
      if (request.status === 401) {
        try {
          localStorage.removeItem("hiresense_access_token");
          localStorage.removeItem("hiresense_user");
        } catch (storageError) {
          console.warn("[resume] Could not clear expired session:", storageError);
        }
        window.location.assign("/");
        return;
      }
      let payload: ResumeProfile & { detail?: string };
      try {
        payload = JSON.parse(request.responseText) as ResumeProfile & { detail?: string };
      } catch {
        setError("The server returned an unreadable response.");
        return;
      }
      if (request.status < 200 || request.status >= 300) {
        setError(payload.detail || "Could not parse this resume.");
        return;
      }
      setProfile(payload);
      setSkills(payload.skills || []);
      setSelectedFile(null);
      setProgress(100);
      setNotice(`Resume processed (${payload.parse_quality || "basic"} parse). Review your skills below.`);
    };
    request.send(body);
  }

  async function saveSkills() {
    setSavingSkills(true);
    setError(null);
    setNotice(null);
    try {
      const response = await apiFetch("/me/profile/skills", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skills }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || "Could not save your skills.");
      setSkills(result.skills);
      setNotice("Your skills were saved.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Could not save your skills.");
    } finally {
      setSavingSkills(false);
    }
  }

  function addSkill() {
    const value = newSkill.trim();
    if (value && !skills.some((skill) => skill.toLowerCase() === value.toLowerCase()) && skills.length < 60) {
      setSkills((current) => [...current, value]);
    }
    setNewSkill("");
  }

  if (loading) {
    return <main className="mx-auto min-h-[60vh] max-w-6xl px-4 py-12 text-sm text-zinc-300" role="status">Loading resume profile…</main>;
  }

  return (
    <main className="min-h-[calc(100svh-4rem)] px-4 py-8 text-zinc-100 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-5xl">
        <PageHeader
          eyebrow="Your profile"
          title="Resume & skills"
          description="Add your experience and skills to tailor practice to the roles you want."
          action={profile?.filename ? <Badge tone="success"><FileCheck2 className="mr-1.5 h-3.5 w-3.5" />Profile ready</Badge> : undefined}
        />

        {error && <p role="alert" className="mb-5 rounded-md border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</p>}
        {notice && <p role="status" className="mb-5 rounded-md border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">{notice}</p>}

        <Card className="p-5 sm:p-6">
          <div className="flex items-start gap-3">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-blue-600/15 text-blue-400"><FileUp className="h-5 w-5" /></span>
            <div>
              <h2 className="text-base font-semibold text-white">Upload your resume</h2>
              <p className="mt-1 text-xs text-slate-400">We’ll use it to understand your experience and suggest practice roles.</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              chooseFile(event.dataTransfer.files[0]);
            }}
            className="mt-5 flex min-h-36 w-full flex-col items-center justify-center rounded-lg border border-dashed border-slate-700 bg-slate-900/40 px-4 text-center transition hover:border-blue-500/50 hover:bg-slate-850 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500"
          >
            <span className="grid h-10 w-10 place-items-center rounded-md bg-slate-800 text-blue-400"><FileUp className="h-5 w-5" /></span>
            <span className="mt-3 text-sm font-medium text-slate-200">Drop your resume here or browse files</span>
            <span className="mt-1 text-xs text-slate-500">PDF or DOCX · up to 5 MB</span>
          </button>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            className="sr-only"
            onChange={(event) => chooseFile(event.target.files?.[0])}
          />
          {selectedFile && <p className="mt-3 text-xs text-slate-300">Selected: {selectedFile.name}</p>}
          {uploading && (
            <div className="mt-4" aria-label="Resume upload progress">
              <ProgressBar value={Math.min(progress / 10, 10)} label="Upload progress" />
              <p className="mt-2 text-xs text-slate-400">{progress}% uploaded — parsing resume…</p>
            </div>
          )}
          <Button
            variant="primary"
            type="button"
            onClick={uploadResume}
            disabled={!selectedFile || uploading}
            className="mt-4"
          >
            {uploading ? "Uploading…" : profile?.filename ? "Replace resume" : "Upload resume"}
          </Button>
          {profile?.filename && (
            <p className="mt-3 text-xs text-slate-500">
              Current file: {profile.filename}
              {profile.updated_at ? ` · Updated ${new Date(profile.updated_at).toLocaleString()}` : ""}
            </p>
          )}
        </Card>

        {profile?.filename && (
          <>
            <Card className="mt-5 p-5 sm:p-6">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-base font-semibold text-white">Your skills</h2>
                  <p className="mt-1 text-xs text-slate-400">Review what we found. Add or remove skills so your recommendations feel like you.</p>
                </div>
                <Badge tone="neutral">
                  {profile.total_years_experience} years experience
                </Badge>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {skills.map((skill) => (
                  <span key={skill} className="inline-flex items-center gap-1.5 rounded border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-200">
                    {skill}
                    <button
                      type="button"
                      aria-label={`Remove ${skill}`}
                      onClick={() => setSkills((current) => current.filter((item) => item !== skill))}
                      className="rounded text-slate-400 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500"
                    >
                      ×
                    </button>
                  </span>
                ))}
                {skills.length === 0 && <p className="text-xs text-slate-500">No skills found yet.</p>}
              </div>
              <div className="mt-5 flex flex-col gap-2 sm:flex-row">
                <input
                  value={newSkill}
                  onChange={(event) => setNewSkill(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      addSkill();
                    }
                  }}
                  maxLength={60}
                  placeholder="Add a skill"
                  className="min-w-0 flex-1 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-100 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
                <button type="button" onClick={addSkill} className="rounded-md border border-slate-700 bg-slate-800 px-3.5 py-2 text-xs font-medium text-slate-200 hover:bg-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500">
                  Add skill
                </button>
                <button type="button" onClick={saveSkills} disabled={savingSkills} className="rounded-md bg-blue-600 px-3.5 py-2 text-xs font-medium text-white hover:bg-blue-500 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500">
                  {savingSkills ? "Saving…" : "Save skills"}
                </button>
              </div>
            </Card>

            {(profile.experiences?.length > 0 || profile.education?.length > 0 || profile.summary) && (
              <Card className="mt-5 p-5 sm:p-6">
                <h2 className="text-base font-semibold text-white">Experience & education</h2>
                {profile.summary && <p className="mt-3 text-xs leading-relaxed text-slate-400">{profile.summary}</p>}
                {profile.experiences?.map((experience, index) => (
                  <article key={`${experience.title}-${index}`} className="mt-4 border-l-2 border-slate-700 pl-3">
                    <h3 className="text-sm font-medium text-slate-200">{experience.title || "Experience"}{experience.company ? ` · ${experience.company}` : ""}</h3>
                    {experience.duration && <p className="mt-0.5 text-xs text-slate-500">{experience.duration}</p>}
                    {experience.highlights?.length > 0 && (
                      <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-slate-400">
                        {experience.highlights.map((highlight, idx) => <li key={`${idx}-${highlight}`}>{highlight}</li>)}
                      </ul>
                    )}
                  </article>
                ))}
                {profile.education?.length > 0 && (
                  <div className="mt-5">
                    <h3 className="text-xs font-semibold text-slate-300">Education</h3>
                    <ul className="mt-2 space-y-1 text-xs text-slate-400">
                      {profile.education.map((education, index) => <li key={`${index}-${education}`}>{education}</li>)}
                    </ul>
                  </div>
                )}
              </Card>
            )}
            <Card className="mt-5 flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
              <div className="flex items-start gap-3">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-blue-600/10 text-blue-400"><FileText className="h-5 w-5" /></span>
                <div>
                  <h2 className="text-sm font-semibold text-white">Ready to explore roles?</h2>
                  <p className="mt-0.5 text-xs text-slate-400">Your saved skills help personalize the interview profiles you see.</p>
                </div>
              </div>
              <Link href="/interview" className="inline-flex items-center gap-1.5 self-start text-xs font-medium text-blue-400 hover:text-blue-300 sm:self-center">
                View role recommendations <ArrowUpRight className="h-4 w-4" />
              </Link>
            </Card>
          </>
        )}
      </div>
    </main>
  );
}

export default function ResumePage() {
  return <AuthGuard><ResumePageContent /></AuthGuard>;
}
