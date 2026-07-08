import { BLOCKED_KEYWORDS } from "../constants";

export type PreferenceTagType = "industry" | "theme" | "custom_keyword";

export function splitTags(value: string) {
  return [...new Set(value.split(/[,\n，、；;\s]/).map((item) => item.trim()).filter(Boolean))];
}

export function parseKeywordInput(rawText: string) {
  return rawText
    .replace(/[。；;、]/g, "，")
    .replace(/\s+/g, "，")
    .split(/[,\n，]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function joinTags(values: string[]) {
  return [...new Set(values.map((item) => item.trim()).filter(Boolean))].join("、");
}

function hasRepeatedNoise(value: string) {
  const compact = value.replace(/\s+/g, "").toLowerCase();
  return compact.length >= 6 && new Set(compact.split("")).size === 1;
}

function validateCustomKeyword(value: string) {
  const normalized = value.trim().replace(/\s+/g, " ");
  if (normalized.length < 2) return { value: normalized, error: "自定义关注点至少 2 个字" };
  if (normalized.length > 20) return { value: normalized, error: "自定义关注点最多 20 个字" };
  if (BLOCKED_KEYWORDS.includes(normalized.toLowerCase())) return { value: normalized, error: "请填写真实关注点" };
  if (/^\d+$/.test(normalized) || !/[\w\u4e00-\u9fff]/.test(normalized)) return { value: normalized, error: "自定义关注点请填写文字内容" };
  if (/https?:\/\/|www\.|[\w.+-]+@[\w-]+(?:\.[\w-]+)+|(?:\+?\d[\d\s-]{6,}\d)/i.test(normalized)) {
    return { value: normalized, error: "自定义关注点不能包含链接或联系方式" };
  }
  if (hasRepeatedNoise(normalized)) return { value: normalized, error: "请填写真实关注点" };
  return { value: normalized, error: "" };
}

export function normalizeCustomKeywords(rawItems: string[]) {
  const normalized: string[] = [];
  for (const item of rawItems) {
    const result = validateCustomKeyword(item);
    if (result.error) return { values: normalized, error: result.error };
    if (!normalized.includes(result.value)) normalized.push(result.value);
    if (normalized.length > 10) return { values: normalized.slice(0, 10), error: "自定义关注点最多 10 个" };
  }
  return { values: normalized, error: "" };
}
