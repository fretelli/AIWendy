"use client";

import { researchRequest } from "./client";
import type { ClientEventPayload, FeedbackCreatePayload } from "./types";

export function submitFeedback(data: FeedbackCreatePayload) {
  return researchRequest<{ ok: boolean; id: number; message: string }>("/feedback", {
    method: "POST",
    body: JSON.stringify({
      ...data,
      contact: data.contact || "",
      page_path: data.page_path || "/research",
      report_id: data.report_id || "",
      digest_id: data.digest_id || null,
      client_version: "keeltrader-web",
      metadata: {
        source: "keeltrader_web",
        ...(data.metadata || {}),
      },
    }),
  }, { auth: "optional" });
}

export function trackClientEvent(data: ClientEventPayload) {
  return researchRequest<{ ok: boolean; id: number }>("/client-events", {
    method: "POST",
    body: JSON.stringify({
      ...data,
      page_path: data.page_path || "/research",
      status: data.status || "info",
      client_version: "keeltrader-web",
      metadata: {
        source: "keeltrader_web",
        ...(data.metadata || {}),
      },
    }),
  }, { auth: "optional" });
}
