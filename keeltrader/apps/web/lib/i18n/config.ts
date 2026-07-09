/**
 * Internationalization (i18n) Configuration
 * Supports English and Chinese languages
 */

export const i18nConfig = {
  defaultLocale: 'zh',
  locales: ['en', 'zh'] as const,
} as const;

export type Locale = (typeof i18nConfig.locales)[number];

export function isValidLocale(locale: string): locale is Locale {
  return (i18nConfig.locales as readonly string[]).includes(locale);
}

export const languages = {
  en: {
    name: 'English',
    flag: '🇺🇸',
    code: 'en-US',
  },
  zh: {
    name: '中文',
    flag: '🇨🇳',
    code: 'zh-CN',
  },
} as const;

// Cookie name for storing language preference
export const LOCALE_COOKIE = 'keeltrader-locale';

// Language detection settings
export const languageDetection = {
  // Try to detect from browser
  detectBrowserLanguage: true,
  // Cookie settings
  cookieName: LOCALE_COOKIE,
  cookieMaxAge: 365 * 24 * 60 * 60, // 1 year
  cookieSameSite: 'lax' as const,
  // Redirect settings
  alwaysRedirect: false,
  fallbackLocale: 'zh',
};

// Locale paths for different regions
export const localeNames: Record<Locale, string> = {
  en: 'English',
  zh: '简体中文',
};

// Currency settings per locale
export const localeCurrencies: Record<Locale, string> = {
  en: 'USD',
  zh: 'CNY',
};

// Date formats per locale
export const localeDateFormats: Record<Locale, string> = {
  en: 'MM/dd/yyyy',
  zh: 'yyyy年MM月dd日',
};

// Time formats per locale
export const localeTimeFormats: Record<Locale, string> = {
  en: 'h:mm a',
  zh: 'HH:mm',
};

// Number formats per locale
export const localeNumberFormats: Record<Locale, Intl.NumberFormatOptions> = {
  en: {
    style: 'decimal',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  },
  zh: {
    style: 'decimal',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  },
};
