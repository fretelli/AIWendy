"use client";

import { researchRequest } from "./client";
import type {
  DigestDetail,
  NotificationResponse,
  RecommendationResponse,
  ReportBriefingState,
  ReportDetail,
  ReportFreshness,
  ReportNoteState,
} from "./types";

export function getRecommendations(limit = 12, mode: "personalized" | "public" = "public") {
  return researchRequest<RecommendationResponse>(
    `/reports/recommendations?limit=${limit}&mode=${encodeURIComponent(mode)}`,
    {},
    { auth: mode === "personalized" ? "required" : "optional" }
  );
}

export function getPublicRecommendations(limit = 12) {
  return getRecommendations(limit, "public");
}

export function getReportFreshness() {
  return researchRequest<ReportFreshness>("/reports/freshness", {}, { auth: "required" });
}

export function getReportDetail(id: string, digestId?: string | number | null) {
  const suffix = digestId ? `?digest_id=${encodeURIComponent(String(digestId))}` : "";
  return researchRequest<ReportDetail>(`/reports/${encodeURIComponent(id)}${suffix}`, {}, { auth: "optional" });
}

export function getReportNoteState(id: string) {
  return researchRequest<ReportNoteState>(`/reports/${encodeURIComponent(id)}/note`, {}, { auth: "required" });
}

export function triggerReportNote(id: string) {
  return researchRequest<ReportNoteState>(`/reports/${encodeURIComponent(id)}/note`, {
    method: "POST",
    body: JSON.stringify({}),
  }, { auth: "required" });
}

export function getHomeFeed() {
  return researchRequest<DigestDetail>("/home/feed", {}, { auth: "required" });
}

export function getDigestDetail(id: string | number) {
  return researchRequest<DigestDetail>(`/digests/${encodeURIComponent(String(id))}`, {}, { auth: "required" });
}

export function getNotifications(limit = 20) {
  return researchRequest<NotificationResponse>(`/notifications?limit=${limit}`, {}, { auth: "required" });
}

export function refreshNotifications(limit = 20) {
  return researchRequest<NotificationResponse & { ok: boolean }>(`/notifications/refresh?limit=${limit}`, {
    method: "POST",
    body: JSON.stringify({}),
  }, { auth: "required" });
}

export function markNotificationRead(id: number) {
  return researchRequest<{ ok: boolean }>(`/notifications/${id}/read`, {
    method: "POST",
    body: JSON.stringify({}),
  }, { auth: "required" });
}

export function markAllNotificationsRead() {
  return researchRequest<{ ok: boolean }>("/notifications/read-all", {
    method: "POST",
    body: JSON.stringify({}),
  }, { auth: "required" });
}

export function synthesizeReportBriefing(reportId: string) {
  return researchRequest<ReportBriefingState>("/speech/report-briefing", {
    method: "POST",
    body: JSON.stringify({ report_id: reportId }),
  }, { auth: "required" });
}

export function getReportBriefingStatus(reportId: string) {
  return researchRequest<ReportBriefingState>(`/speech/report-briefing/${encodeURIComponent(reportId)}`, {}, { auth: "required" });
}
