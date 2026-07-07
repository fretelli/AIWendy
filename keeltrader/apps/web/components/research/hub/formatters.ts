import { type NotificationResponse, type ReportCardItem } from "@/lib/research-api";

import { type TabValue } from "./types";

export function formatDate(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 10);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

export function formatDateTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${formatDate(value)} ${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

export function dateOnly(value: Date) {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
}

export function digestPeriodKeyFromDate(mode: "daily" | "weekly", value: Date) {
  const date = new Date(value);
  date.setHours(0, 0, 0, 0);
  if (mode === "weekly") {
    const day = date.getDay();
    const offset = day === 0 ? 6 : day - 1;
    date.setDate(date.getDate() - offset);
  }
  return `${mode}:${dateOnly(date)}`;
}

export function digestPeriodKey(item: NotificationResponse["items"][number]) {
  const mode = String(item.payload?.mode || "").replace(/_public$/, "");
  const anchor = String(item.payload?.anchor || "").slice(0, 10);
  return mode && anchor ? `${mode}:${anchor}` : "";
}

export function officialArticleEventName(tab: TabValue, entry?: string) {
  const normalizedEntry = String(entry || "").trim();
  if (normalizedEntry === "interest") return "official_article_interest_open";
  if (normalizedEntry === "market") return "official_article_market_open";
  if (normalizedEntry === "feedback") return "official_article_feedback_open";
  if (tab === "digests") return "official_article_market_open";
  if (tab === "preferences") return "official_article_interest_open";
  if (tab === "feedback") return "official_article_feedback_open";
  return "official_article_home_open";
}

export function formatMoneyFen(value?: number | null) {
  return `¥${((value || 0) / 100).toFixed(2)}`;
}

export function formatNumber(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return Number(value).toLocaleString("zh-CN");
}

export function formatUsd(value?: number | null) {
  if (!value) return "-";
  if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  return `$${formatNumber(value)}`;
}

export function reportTitle(item: ReportCardItem) {
  return item.display_title || item.title?.replace(/\.pdf$/i, "") || "未命名研报";
}

export function imageUrl(path?: string) {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  return `https://research.joyeeassets.com${path}`;
}
