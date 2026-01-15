/**
 * Server-side i18n utilities for Next.js App Router
 */

import { cookies } from 'next/headers';
import { Locale, i18nConfig, LOCALE_COOKIE, languages, localeCurrencies, localeDateFormats } from './config';
import en from './translations/en.json';
import zh from './translations/zh.json';

// Translations
const translations: Record<Locale, typeof en> = {
  en,
  zh: zh as unknown as typeof en, // Force type assertion to bypass type mismatch temporarily
};

/**
 * Get the current locale from cookies or headers
 */
export async function getLocale(): Promise<Locale> {
  const cookieStore = cookies();
  const localeCookie = cookieStore.get(LOCALE_COOKIE);

  if (localeCookie?.value && i18nConfig.locales.includes(localeCookie.value as Locale)) {
    return localeCookie.value as Locale;
  }

  // TODO: Could also check Accept-Language header here
  return i18nConfig.defaultLocale;
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

  const keys = key.split('.');
  let value: any = trans;

  for (const k of keys) {
    if (value && typeof value === 'object' && k in value) {
      value = value[k];
    } else {
      console.warn(`Translation key "${key}" not found for locale "${currentLocale}"`);
      return key;
    }
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
 * Replace parameters in translation string
 */
export function replaceParams(text: string, params?: Record<string, any>): string {
  if (!params) return text;

  let result = text;
  Object.keys(params).forEach((key) => {
    const regex = new RegExp(`\\{${key}\\}`, 'g');
    result = result.replace(regex, String(params[key]));
  });

  return result;
}

/**
 * Get dictionary for a specific namespace
 */
export async function getDictionary(namespace: string, locale?: Locale) {
  const currentLocale = locale || (await getLocale());
  const trans = translations[currentLocale];

  // Return the specific namespace or the entire translations
  return (trans as any)[namespace] || trans;
}

/**
 * Generate metadata for different locales
 */
export function generateMetadata(locale: Locale) {
  const isZh = locale === 'zh';

  return {
    title: isZh ? 'KeelTrader - 您的AI交易心理教练' : 'KeelTrader - Your AI Trading Psychology Coach',
    description: isZh
      ? 'KeelTrader 是一个AI驱动的交易心理辅导平台，帮助交易者克服情绪障碍，提升交易表现。'
      : 'KeelTrader is an AI-powered trading psychology coaching platform that helps traders overcome emotional barriers and improve trading performance.',
    keywords: isZh
      ? ['交易心理', 'AI教练', '交易日志', '风险管理', '量化交易', '交易分析']
      : ['trading psychology', 'AI coach', 'trading journal', 'risk management', 'quantitative trading', 'trade analysis'],
    openGraph: {
      title: isZh ? 'KeelTrader - AI交易心理教练' : 'KeelTrader - AI Trading Psychology Coach',
      description: isZh
        ? '使用AI技术提升您的交易心理和表现'
        : 'Enhance your trading psychology and performance with AI',
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
  return i18nConfig.locales.includes(locale as Locale);
}