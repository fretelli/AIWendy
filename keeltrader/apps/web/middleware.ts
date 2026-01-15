import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { i18nConfig, LOCALE_COOKIE, Locale } from '@/lib/i18n/config';

// Paths that should not be localized
const PUBLIC_FILE = /\.(.*)$/;
const EXCLUDED_PATHS = [
  '/api',
  '/_next',
  '/favicon.ico',
  '/robots.txt',
  '/sitemap.xml',
];

export function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  // Skip public files and excluded paths
  if (
    PUBLIC_FILE.test(pathname) ||
    EXCLUDED_PATHS.some((path) => pathname.startsWith(path))
  ) {
    return NextResponse.next();
  }

  // Get locale from cookie or Accept-Language header
  const cookieLocale = request.cookies.get(LOCALE_COOKIE)?.value as Locale;
  let locale: Locale = i18nConfig.defaultLocale;

  if (cookieLocale && i18nConfig.locales.includes(cookieLocale)) {
    locale = cookieLocale;
  } else {
    // Try to detect from Accept-Language header
    const acceptLanguage = request.headers.get('Accept-Language');
    if (acceptLanguage) {
      const detectedLocale = detectLocaleFromHeader(acceptLanguage);
      if (detectedLocale) {
        locale = detectedLocale;
      }
    }
  }

  // Create response
  const response = NextResponse.next();

  // Set locale cookie if not present
  if (!cookieLocale) {
    response.cookies.set(LOCALE_COOKIE, locale, {
      maxAge: 365 * 24 * 60 * 60, // 1 year
      sameSite: 'lax',
      secure: process.env.NODE_ENV === 'production',
    });
  }

  // Add locale header for server components
  response.headers.set('x-locale', locale);

  return response;
}

/**
 * Detect locale from Accept-Language header
 */
function detectLocaleFromHeader(acceptLanguage: string): Locale | null {
  const languages = acceptLanguage
    .split(',')
    .map((lang) => {
      const [code, priority = '1'] = lang.trim().split(';q=');
      return {
        code: code.toLowerCase(),
        priority: parseFloat(priority.replace('q=', '')),
      };
    })
    .sort((a, b) => b.priority - a.priority);

  for (const lang of languages) {
    // Check for exact match
    if (lang.code === 'zh' || lang.code.startsWith('zh-')) {
      return 'zh';
    }
    if (lang.code === 'en' || lang.code.startsWith('en-')) {
      return 'en';
    }
  }

  return null;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    '/((?!api|_next/static|_next/image|favicon.ico|public).*)',
  ],
};