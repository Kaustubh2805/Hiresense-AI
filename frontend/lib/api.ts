"use client";

import { API_BASE_URL } from "@/lib/config";

export async function apiFetch(
  input: string | URL,
  init: RequestInit = {},
): Promise<Response> {
  let token: string | null = null;
  try {
    token = localStorage.getItem("hiresense_access_token");
  } catch (error) {
    console.warn("[api] Could not read access token:", error);
  }

  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const url =
    typeof input === "string" && input.startsWith("/")
      ? `${API_BASE_URL}${input}`
      : input;
  const response = await fetch(url, { ...init, headers });

  if (response.status === 401 && typeof window !== "undefined") {
    try {
      localStorage.removeItem("hiresense_access_token");
      localStorage.removeItem("hiresense_user");
      sessionStorage.removeItem("hiresense_interview_complete");
    } catch (error) {
      console.warn("[api] Could not clear expired session:", error);
    }
    window.location.assign("/");
  }
  return response;
}
