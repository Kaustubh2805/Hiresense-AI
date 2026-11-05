"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { AppShell } from "@/components/app-shell";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { loading, token } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !token) router.replace("/");
  }, [loading, token, router]);

  if (loading || !token) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-300">
        <p role="status">Checking your session…</p>
      </main>
    );
  }
  return <AppShell>{children}</AppShell>;
}
