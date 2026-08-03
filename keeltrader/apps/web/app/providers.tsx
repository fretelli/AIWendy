"use client";

import { ThemeProvider } from "next-themes";
import { ReactNode } from "react";
import { SWRConfig } from "swr";

export function Providers({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="dark"
      forcedTheme="dark"
      enableSystem={false}
      disableTransitionOnChange
    >
      <SWRConfig value={{ dedupingInterval: 30_000, revalidateOnFocus: false, keepPreviousData: true }}>
        {children}
      </SWRConfig>
    </ThemeProvider>
  );
}
