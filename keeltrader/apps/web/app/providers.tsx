"use client";

import { ThemeProvider } from "next-themes";
import { ReactNode } from "react";

import { LanguageProvider } from "@/components/language-provider";
import { type Language } from "@/lib/i18n";

export function Providers({
  children,
  initialLanguage,
}: {
  children: ReactNode;
  initialLanguage?: Language;
}) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      <LanguageProvider initialLanguage={initialLanguage}>
        {children}
      </LanguageProvider>
    </ThemeProvider>
  );
}
