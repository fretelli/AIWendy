import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { Toaster } from "@/components/ui/toaster";
import { SonnerToaster } from "@/components/sonner-toaster";
import { I18nProvider } from "@/lib/i18n/provider";
import { getLocale, generateMetadata as generateI18nMetadata } from "@/lib/i18n/server";

const inter = Inter({ subsets: ["latin"] });

export const viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getLocale();
  const i18nMeta = generateI18nMetadata(locale);

  return {
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
      url: "https://keeltrader.com",
      siteName: "KeelTrader",
      type: "website",
      images: [
        {
          url: '/og-image.png',
          width: 1200,
          height: 630,
          alt: 'KeelTrader - AI Trading Psychology Coach',
        },
      ],
    },
    twitter: {
      card: 'summary_large_image',
      title: i18nMeta.title,
      description: i18nMeta.description,
      images: ['/twitter-image.png'],
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
      <body className={inter.className}>
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
