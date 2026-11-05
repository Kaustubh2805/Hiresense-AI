const defaultApiBase =
  typeof window === "undefined"
    ? "http://localhost:8000"
    : `http://${window.location.hostname}:8000`;

export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? defaultApiBase
).replace(/\/+$/, "");

export const GOOGLE_CLIENT_ID =
  process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "";
