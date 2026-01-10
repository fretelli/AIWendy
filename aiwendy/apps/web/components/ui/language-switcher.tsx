'use client';

import * as React from 'react';
import { Check, ChevronDown, Globe } from 'lucide-react';
import { useI18n } from '@/lib/i18n/provider';
import { languages, Locale, i18nConfig } from '@/lib/i18n/config';
import { cn } from '@/lib/utils';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';

interface LanguageSwitcherProps {
  className?: string;
  variant?: 'default' | 'outline' | 'ghost';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  showFlag?: boolean;
  showName?: boolean;
  align?: 'start' | 'center' | 'end';
}

export function LanguageSwitcher({
  className,
  variant = 'ghost',
  size = 'default',
  showFlag = true,
  showName = true,
  align = 'end',
}: LanguageSwitcherProps) {
  const { locale, setLocale } = useI18n();

  const currentLanguage = languages[locale];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant={variant}
          size={size}
          className={cn('gap-2', className)}
          aria-label="Select language"
        >
          <Globe className="h-4 w-4" />
          {showFlag && <span className="text-base">{currentLanguage.flag}</span>}
          {showName && (
            <span className="hidden sm:inline-block">{currentLanguage.name}</span>
          )}
          <ChevronDown className="h-3 w-3 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align={align} className="min-w-[150px]">
        {i18nConfig.locales.map((loc) => (
          <DropdownMenuItem
            key={loc}
            onClick={() => setLocale(loc)}
            className="gap-2"
          >
            <span className="text-base">{languages[loc].flag}</span>
            <span className="flex-1">{languages[loc].name}</span>
            {locale === loc && <Check className="h-4 w-4" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// Compact version for mobile
export function LanguageSwitcherCompact({ className }: { className?: string }) {
  const { locale, setLocale } = useI18n();

  return (
    <div className={cn('flex items-center gap-1', className)}>
      {i18nConfig.locales.map((loc) => (
        <Button
          key={loc}
          variant={locale === loc ? 'default' : 'ghost'}
          size="sm"
          onClick={() => setLocale(loc)}
          className="px-2 py-1"
          aria-label={`Switch to ${languages[loc].name}`}
        >
          <span className="text-base">{languages[loc].flag}</span>
        </Button>
      ))}
    </div>
  );
}

// Simple select version
export function LanguageSwitcherSelect({ className }: { className?: string }) {
  const { locale, setLocale } = useI18n();

  return (
    <select
      value={locale}
      onChange={(e) => setLocale(e.target.value as Locale)}
      className={cn(
        'px-3 py-1.5 rounded-md border border-gray-300 dark:border-gray-600',
        'bg-white dark:bg-gray-800 text-sm focus:outline-none',
        'focus:ring-2 focus:ring-blue-500',
        className
      )}
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

// Footer language links
export function LanguageLinks({ className }: { className?: string }) {
  const { locale, setLocale } = useI18n();

  return (
    <div className={cn('flex items-center gap-3 text-sm', className)}>
      <Globe className="h-4 w-4 text-gray-500" />
      {i18nConfig.locales.map((loc, index) => (
        <React.Fragment key={loc}>
          {index > 0 && <span className="text-gray-400">|</span>}
          <button
            onClick={() => setLocale(loc)}
            className={cn(
              'hover:text-primary transition-colors',
              locale === loc ? 'text-primary font-medium' : 'text-gray-600 dark:text-gray-400'
            )}
          >
            {languages[loc].name}
          </button>
        </React.Fragment>
      ))}
    </div>
  );
}