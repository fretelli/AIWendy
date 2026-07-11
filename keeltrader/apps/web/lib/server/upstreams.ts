import { normalizeBaseUrl, unique } from "@/lib/server/proxy";

export function getApiBaseUrlCandidates(
  env: Partial<NodeJS.ProcessEnv> = process.env
): string[] {
  const configuredRaw =
    env.KEELTRADER_API_URL ||
    env.API_URL ||
    env.NEXT_PUBLIC_API_URL ||
    "";

  const candidates: string[] = [];
  const configured = normalizeBaseUrl(configuredRaw);

  if (configured) {
    candidates.push(configured);

    try {
      const url = new URL(configured);
      const host = url.hostname.toLowerCase();

      if (host === "api") {
        candidates.push("http://localhost:8000");
      }

      if (host === "localhost" || host === "127.0.0.1") {
        candidates.push("http://api:8000");
      }
    } catch {
      // Keep the configured value; fetch will report the real connection error.
    }

    return unique(candidates);
  }

  return unique(["http://localhost:8000", "http://api:8000"]);
}
