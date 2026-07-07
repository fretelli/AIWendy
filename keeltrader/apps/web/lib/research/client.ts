"use client";

import type { ApiErrorPayload } from "./types";

export function getErrorMessage(payload: ApiErrorPayload): string | null {
  if ("detail" in payload) {
    const detail = payload.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0] && typeof detail[0] === "object") {
      const msg = (detail[0] as { msg?: unknown }).msg;
      if (typeof msg === "string") return msg;
    }
  }

  if ("error" in payload) {
    const msg = payload.error?.message;
    if (msg) return msg;
  }

  return null;
}

export function getResearchToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("research_access_token") || localStorage.getItem("research_token") || "";
}

export function setResearchToken(token: string) {
  if (typeof window === "undefined") return;
  const normalized = token.trim();
  if (normalized) {
    localStorage.setItem("research_access_token", normalized);
  } else {
    localStorage.removeItem("research_access_token");
  }
}

export function createSessionId() {
  if (typeof window === "undefined") return "web-server";
  const key = "research_web_session_id";
  const existing = localStorage.getItem(key);
  if (existing) return existing;
  const next = `web_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 12)}`;
  localStorage.setItem(key, next);
  return next;
}

export async function researchRequest<T>(path: string, init: RequestInit = {}, options: { auth?: "required" | "optional" | "none" } = {}) {
  const token = getResearchToken();
  const headers = new Headers(init.headers);
  headers.set("Content-Type", headers.get("Content-Type") || "application/json");
  headers.set("X-Session-ID", createSessionId());
  if (token && options.auth !== "none") {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`/api/research${path}`, {
    ...init,
    headers,
  });
  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const payload = isJson ? await response.json().catch(() => null) : null;

  if (!response.ok) {
    const message =
      payload && typeof payload === "object"
        ? getErrorMessage(payload as ApiErrorPayload)
        : null;
    throw new Error(message || response.statusText || "请求失败");
  }

  return payload as T;
}

export async function researchUpload<T>(path: string, file: File, options: { auth?: "required" | "optional" | "none" } = {}) {
  const token = getResearchToken();
  const headers = new Headers();
  headers.set("X-Session-ID", createSessionId());
  if (token && options.auth !== "none") {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const form = new FormData();
  form.set("file", file);

  const response = await fetch(`/api/research${path}`, {
    method: "POST",
    headers,
    body: form,
  });
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      payload && typeof payload === "object"
        ? getErrorMessage(payload as ApiErrorPayload)
        : null;
    throw new Error(message || response.statusText || "上传失败");
  }

  return payload as T;
}
