"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";

export function useUrlTab(valid: readonly string[], fallback: string, aliases: Record<string, string> = {}) {
  const pathname = usePathname();
  const router = useRouter();
  const params = useSearchParams();
  const requested = params.get("tab") || "";
  const aliased = aliases[requested] || requested;
  const value = valid.includes(aliased) ? aliased : fallback;
  useEffect(() => {
    if (requested === value) return;
    const query = new URLSearchParams(params.toString());
    query.set("tab", value);
    router.replace(`${pathname}?${query}`);
  }, [params, pathname, requested, router, value]);
  const setValue = (next: string) => {
    if (!valid.includes(next)) return;
    const query = new URLSearchParams(params.toString());
    query.set("tab", next);
    router.replace(`${pathname}?${query}`);
  };
  return [value, setValue] as const;
}
