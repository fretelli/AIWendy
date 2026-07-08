import { type Locale } from './config';
import en from './translations/en.json';
import zh from './translations/zh.json';
import type { JsonPrimitive } from '@/lib/types/json';

export type TranslationDictionary = typeof en;

type NestedKeyOf<ObjectType extends object> = {
  [Key in keyof ObjectType & string]: ObjectType[Key] extends object
    ? `${Key}` | `${Key}.${NestedKeyOf<ObjectType[Key]>}`
    : `${Key}`;
}[keyof ObjectType & string];

export type TranslationKey = NestedKeyOf<TranslationDictionary>;
export type TranslationParams = Record<string, JsonPrimitive>;

export const translations: Record<Locale, TranslationDictionary> = {
  en,
  zh,
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

export function readNestedValue(source: unknown, path: string): unknown {
  let value = source;

  for (const key of path.split('.')) {
    if (isRecord(value) && key in value) {
      value = value[key];
    } else {
      return undefined;
    }
  }

  return value;
}

export function getNestedTranslation(key: string, locale: Locale): string {
  const value = readNestedValue(translations[locale], key);
  if (value === undefined) {
    console.warn(`Translation key "${key}" not found for locale "${locale}"`);
    return key;
  }

  return typeof value === 'string' ? value : key;
}

export function replaceParams(text: string, params?: TranslationParams): string {
  if (!params) return text;

  let result = text;
  Object.keys(params).forEach((key) => {
    const regex = new RegExp(`\\{${key}\\}`, 'g');
    result = result.replace(regex, String(params[key]));
  });

  return result;
}
