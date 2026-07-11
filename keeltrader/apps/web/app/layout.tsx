import type { Metadata } from "next";
import { IBM_Plex_Mono, Manrope, Newsreader } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { Toaster } from "@/components/ui/toaster";
import { SonnerToaster } from "@/components/sonner-toaster";
import { I18nProvider } from "@/lib/i18n/provider";
import { getLocale, generateMetadata as generateI18nMetadata } from "@/lib/i18n/server";

const bodyFont = Manrope({ subsets: ["latin"], variable: "--font-body" });
const displayFont = Newsreader({ subsets: ["latin"], variable: "--font-display" });
const dataFont = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-data" });
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

export const viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getLocale();
  const i18nMeta = generateI18nMetadata(locale);

  return {
    metadataBase: new URL(siteUrl),
    title: {
      default: i18nMeta.title,
      template: '%s | KeelTrader',
    },
    description: i18nMeta.description,
    keywords: i18nMeta.keywords,
    authors: [{ name: "KeelTrader Team" }],
    creator: 'KeelTrader',
    publisher: 'KeelTrader',
    openGraph: {
      ...i18nMeta.openGraph,
      url: siteUrl,
      siteName: "KeelTrader",
      type: "website",
    },
    twitter: {
      card: 'summary_large_image',
      title: i18nMeta.title,
      description: i18nMeta.description,
      creator: '@keeltrader',
    },
    robots: {
      index: true,
      follow: true,
      googleBot: {
        index: true,
        follow: true,
        'max-video-preview': -1,
        'max-image-preview': 'large',
        'max-snippet': -1,
      },
    },
    icons: {
      icon: [
        { url: '/favicon.ico', sizes: 'any' },
        { url: '/icon.svg', type: 'image/svg+xml' },
      ],
      apple: '/apple-touch-icon.png',
    },
    manifest: '/site.webmanifest',
  };
}

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Get initial locale from server
  const locale = await getLocale();

  return (
    <html lang={locale} suppressHydrationWarning>
      <body className={`${bodyFont.variable} ${displayFont.variable} ${dataFont.variable}`}>
        <I18nProvider initialLocale={locale}>
          <Providers>
            {children}
            <Toaster />
            <SonnerToaster />
          </Providers>
        </I18nProvider>
      </body>
    </html>
  );
}
