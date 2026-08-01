"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

export function useUrlTab(valid: readonly string[], fallback: string) {
  const pathname = usePathname();
  const router = useRouter();
  const params = useSearchParams();
  const requested = params.get("tab") || "";
  const value = valid.includes(requested) ? requested : fallback;
  const setValue = (next: string) => {
    if (!valid.includes(next)) return;
    const query = new URLSearchParams(params.toString());
    query.set("tab", next);
    router.replace(`${pathname}?${query}`);
  };
  return [value, setValue] as const;
}
