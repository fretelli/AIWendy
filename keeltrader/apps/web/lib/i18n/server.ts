/**
 * Server-side i18n utilities for Next.js App Router
 */

import { cookies, headers } from 'next/headers';
import { Locale, i18nConfig, LOCALE_COOKIE, languages, localeCurrencies, localeDateFormats, isValidLocale as isSupportedLocale } from './config';
import { readNestedValue, replaceParams, translations, type TranslationParams } from './translations';

/**
 * Get the current locale from cookies or headers
 */
export async function getLocale(): Promise<Locale> {
  const cookieStore = await cookies();
  const localeCookie = cookieStore.get(LOCALE_COOKIE);

  if (localeCookie?.value && isSupportedLocale(localeCookie.value)) {
    return localeCookie.value;
  }

  const headerStore = await headers();
  const acceptLanguage = headerStore.get('Accept-Language');
  const detectedLocale = acceptLanguage ? detectLocaleFromHeader(acceptLanguage) : null;
  if (detectedLocale) {
    return detectedLocale;
  }

  return i18nConfig.defaultLocale;
}

function detectLocaleFromHeader(acceptLanguage: string): Locale | null {
  const languagesByPriority = acceptLanguage
    .split(',')
    .map((item) => {
      const [rawCode, rawPriority = 'q=1'] = item.trim().split(';');
      const priority = Number.parseFloat(rawPriority.replace('q=', ''));
      return {
        code: rawCode.toLowerCase(),
        priority: Number.isFinite(priority) ? priority : 1,
      };
    })
    .sort((a, b) => b.priority - a.priority);

  for (const language of languagesByPriority) {
    if (language.code === 'zh' || language.code.startsWith('zh-')) return 'zh';
    if (language.code === 'en' || language.code.startsWith('en-')) return 'en';
  }

  return null;
}

/**
 * Get translations for a specific locale
 */
export async function getTranslations(locale?: Locale) {
  const currentLocale = locale || (await getLocale());
  return translations[currentLocale];
}

/**
 * Get a specific translation key
 */
export async function getTranslation(key: string, locale?: Locale): Promise<string> {
  const currentLocale = locale || (await getLocale());
  const trans = translations[currentLocale];

  const value = readNestedValue(trans, key);
  if (value === undefined) {
    console.warn(`Translation key "${key}" not found for locale "${currentLocale}"`);
    return key;
  }

  return typeof value === 'string' ? value : key;
}

/**
 * Format date for server-side rendering
 */
export function formatDateServer(
  date: Date | string,
  locale: Locale,
  format: 'short' | 'long' | 'full' = 'short'
): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  const options = {
    short: { year: 'numeric', month: '2-digit', day: '2-digit' },
    long: { year: 'numeric', month: 'long', day: 'numeric' },
    full: {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    },
  }[format] as Intl.DateTimeFormatOptions;

  return new Intl.DateTimeFormat(languages[locale].code, options).format(d);
}

/**
 * Format number for server-side rendering
 */
export function formatNumberServer(
  number: number,
  locale: Locale,
  options?: Intl.NumberFormatOptions
): string {
  return new Intl.NumberFormat(languages[locale].code, options).format(number);
}

/**
 * Format currency for server-side rendering
 */
export function formatCurrencyServer(
  amount: number,
  locale: Locale,
  currency?: string
): string {
  const curr = currency || localeCurrencies[locale];
  return new Intl.NumberFormat(languages[locale].code, {
    style: 'currency',
    currency: curr,
  }).format(amount);
}

/**
 * Get dictionary for a specific namespace
 */
export async function getDictionary(namespace: string, locale?: Locale) {
  const currentLocale = locale || (await getLocale());
  const trans = translations[currentLocale];
  const dictionary = readNestedValue(trans, namespace);

  // Return the specific namespace or the entire translations
  return dictionary || trans;
}

/**
 * Generate metadata for different locales
 */
export function generateMetadata(locale: Locale) {
  const meta = translations[locale].meta;

  return {
    title: meta.title,
    description: meta.description,
    keywords: meta.keywords.split(','),
    openGraph: {
      title: meta.ogTitle,
      description: meta.ogDescription,
      locale: languages[locale].code,
      alternateLocale: i18nConfig.locales
        .filter((l) => l !== locale)
        .map((l) => languages[l].code),
    },
  };
}

/**
 * Helper to determine if a locale is Chinese
 */
export function isChineseLocale(locale: Locale): boolean {
  return locale === 'zh';
}

/**
 * Get all available locales
 */
export function getAvailableLocales(): Locale[] {
  return [...i18nConfig.locales];
}

/**
 * Validate if a locale is supported
 */
export function isValidLocale(locale: string): locale is Locale {
  return isSupportedLocale(locale);
}
