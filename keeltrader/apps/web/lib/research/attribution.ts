"use client";

import type { PendingInvite, WebOfficialArticleAttribution } from "./types";

const ATTRIBUTION_STORAGE_KEY = "research_web_official_article_attribution";
const PENDING_INVITE_STORAGE_KEY = "research_web_pending_invite";
const ATTRIBUTION_TTL_MS = 7 * 24 * 60 * 60 * 1000;

function normalizeSearchValue(value: string | null) {
  return String(value || "").trim();
}

export function captureOfficialArticleAttribution(params: URLSearchParams) {
  if (typeof window === "undefined") return null;
  const source = normalizeSearchValue(params.get("source"));
  const campaignKey = normalizeSearchValue(params.get("campaign_key"));
  const articleType = normalizeSearchValue(params.get("article_type"));
  const entry = normalizeSearchValue(params.get("entry"));
  if (source !== "official_article" || !campaignKey) return null;
  const attribution: WebOfficialArticleAttribution = {
    source,
    campaign_key: campaignKey.slice(0, 120),
    article_type: articleType.slice(0, 80),
    entry: (entry || "unknown").slice(0, 60),
    captured_at: Date.now(),
  };
  localStorage.setItem(ATTRIBUTION_STORAGE_KEY, JSON.stringify(attribution));
  return attribution;
}

export function getOfficialArticleAttribution() {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(ATTRIBUTION_STORAGE_KEY);
  if (!raw) return null;
  try {
    const attribution = JSON.parse(raw) as WebOfficialArticleAttribution;
    if (!attribution.campaign_key || Date.now() - Number(attribution.captured_at || 0) > ATTRIBUTION_TTL_MS) {
      localStorage.removeItem(ATTRIBUTION_STORAGE_KEY);
      return null;
    }
    return attribution;
  } catch {
    localStorage.removeItem(ATTRIBUTION_STORAGE_KEY);
    return null;
  }
}

export function savePendingInviteFromParams(params: URLSearchParams, defaultSource = "web_share", defaultSourceId = "") {
  if (typeof window === "undefined") return null;
  const inviterId = Number(params.get("inviter_id") || 0);
  const inviteCode = normalizeSearchValue(params.get("invite_code"));
  if (inviterId <= 0 && !inviteCode) return null;
  const pendingInvite: PendingInvite = {
    inviter_user_id: inviterId,
    invite_code: inviteCode || undefined,
    source_type: normalizeSearchValue(params.get("source")) || defaultSource,
    source_id: normalizeSearchValue(params.get("source_id")) || defaultSourceId,
    captured_at: Date.now(),
  };
  localStorage.setItem(PENDING_INVITE_STORAGE_KEY, JSON.stringify(pendingInvite));
  return pendingInvite;
}

export function getPendingInvite() {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(PENDING_INVITE_STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as PendingInvite;
  } catch {
    localStorage.removeItem(PENDING_INVITE_STORAGE_KEY);
    return null;
  }
}
