'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Cookies from 'js-cookie';
import { Locale, i18nConfig, LOCALE_COOKIE, languages } from './config';
import en from './translations/en.json';
import zh from './translations/zh.json';

// Translation type
type TranslationKeys = typeof en;
type NestedKeyOf<ObjectType extends object> = {
  [Key in keyof ObjectType & string]: ObjectType[Key] extends object
    ? `${Key}` | `${Key}.${NestedKeyOf<ObjectType[Key]>}`
    : `${Key}`;
}[keyof ObjectType & string];

type TranslationKey = NestedKeyOf<TranslationKeys>;

// Translations object
const translations: Record<Locale, TranslationKeys> = {
  en,
  zh: zh as unknown as TranslationKeys, // Force type assertion to bypass type mismatch temporarily
};

// Context type
interface I18nContextType {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: TranslationKey, params?: Record<string, any>) => string;
  formatDate: (date: Date | string, format?: 'short' | 'long' | 'full') => string;
  formatNumber: (number: number, options?: Intl.NumberFormatOptions) => string;
  formatCurrency: (amount: number, currency?: string) => string;
  formatTime: (date: Date | string, includeSeconds?: boolean) => string;
  isRTL: boolean;
}

// Create context
const I18nContext = createContext<I18nContextType | undefined>(undefined);

// Helper function to get nested translation value
function getNestedTranslation(
  translations: any,
  key: string,
  locale: Locale
): string {
  const keys = key.split('.');
  let value: any = translations[locale];

  for (const k of keys) {
    if (value && typeof value === 'object' && k in value) {
      value = value[k];
    } else {
      console.warn(`Translation key "${key}" not found for locale "${locale}"`);
      return key; // Return the key itself as fallback
    }
  }

  return typeof value === 'string' ? value : key;
}

// Helper function to replace parameters in translation
function replaceParams(text: string, params?: Record<string, any>): string {
  if (!params) return text;

  let result = text;
  Object.keys(params).forEach((key) => {
    const regex = new RegExp(`\\{${key}\\}`, 'g');
    result = result.replace(regex, String(params[key]));
  });

  return result;
}

interface I18nProviderProps {
  children: ReactNode;
  initialLocale?: Locale;
}

export function I18nProvider({ children, initialLocale }: I18nProviderProps) {
  const router = useRouter();
  const pathname = usePathname();

  // Initialize locale from cookie or browser preference
  const [locale, setLocaleState] = useState<Locale>(() => {
    if (initialLocale) return initialLocale;

    // Try to get from cookie
    const cookieLocale = Cookies.get(LOCALE_COOKIE) as Locale;
    if (cookieLocale && i18nConfig.locales.includes(cookieLocale)) {
      return cookieLocale;
    }

    // Try to detect from browser
    if (typeof window !== 'undefined') {
      const browserLang = navigator.language.toLowerCase();
      if (browserLang.startsWith('zh')) return 'zh';
      if (browserLang.startsWith('en')) return 'en';
    }

    return i18nConfig.defaultLocale;
  });

  // Update locale and save to cookie
  const setLocale = (newLocale: Locale) => {
    if (!i18nConfig.locales.includes(newLocale)) return;

    setLocaleState(newLocale);
    Cookies.set(LOCALE_COOKIE, newLocale, { expires: 365, sameSite: 'lax' });

    // Update HTML lang attribute
    if (typeof document !== 'undefined') {
      document.documentElement.lang = languages[newLocale].code;
    }

    // Refresh the page to update all translations
    // You might want to implement a more sophisticated approach
    // to avoid full page refresh
    router.refresh();
  };

  // Translation function
  const t = (key: TranslationKey, params?: Record<string, any>): string => {
    const translation = getNestedTranslation(translations, key, locale);
    return replaceParams(translation, params);
  };

  // Date formatting
  const formatDate = (
    date: Date | string,
    format: 'short' | 'long' | 'full' = 'short'
  ): string => {
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
  };

  // Number formatting
  const formatNumber = (
    number: number,
    options?: Intl.NumberFormatOptions
  ): string => {
    return new Intl.NumberFormat(languages[locale].code, options).format(number);
  };

  // Currency formatting
  const formatCurrency = (amount: number, currency?: string): string => {
    const curr = currency || (locale === 'zh' ? 'CNY' : 'USD');
    return new Intl.NumberFormat(languages[locale].code, {
      style: 'currency',
      currency: curr,
    }).format(amount);
  };

  // Time formatting
  const formatTime = (
    date: Date | string,
    includeSeconds: boolean = false
  ): string => {
    const d = typeof date === 'string' ? new Date(date) : date;
    const options: Intl.DateTimeFormatOptions = {
      hour: '2-digit',
      minute: '2-digit',
      ...(includeSeconds && { second: '2-digit' }),
    };

    return new Intl.DateTimeFormat(languages[locale].code, options).format(d);
  };

  // Check if locale is RTL (for future support of Arabic, Hebrew, etc.)
  const isRTL = false; // Currently we only support LTR languages

  // Update HTML attributes on locale change
  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.lang = languages[locale].code;
      document.documentElement.dir = isRTL ? 'rtl' : 'ltr';
    }
  }, [locale, isRTL]);

  const value: I18nContextType = {
    locale,
    setLocale,
    t,
    formatDate,
    formatNumber,
    formatCurrency,
    formatTime,
    isRTL,
  };

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

// Hook to use i18n
export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useI18n must be used within an I18nProvider');
  }
  return context;
}

// Hook to get translation function
export function useTranslation() {
  const { t } = useI18n();
  return t;
}

// Hook to get current locale
export function useLocale() {
  const { locale } = useI18n();
  return locale;
}

// Language switcher component
export function LanguageSwitcher({ className }: { className?: string }) {
  const { locale, setLocale } = useI18n();

  return (
    <select
      value={locale}
      onChange={(e) => setLocale(e.target.value as Locale)}
      className={`px-3 py-1.5 rounded-md border border-gray-300 dark:border-gray-600
                 bg-white dark:bg-gray-800 text-sm focus:outline-none
                 focus:ring-2 focus:ring-blue-500 ${className}`}
      aria-label="Select language"
    >
      {i18nConfig.locales.map((loc) => (
        <option key={loc} value={loc}>
          {languages[loc].flag} {languages[loc].name}
        </option>
      ))}
    </select>
  );
}

// Export types
export type { TranslationKey, I18nContextType };