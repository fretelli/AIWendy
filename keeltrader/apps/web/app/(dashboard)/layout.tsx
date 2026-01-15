'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useI18n } from '@/lib/i18n/provider';
import { useAuth } from '@/lib/auth-context';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  Brain,
  MessageSquare,
  FolderKanban,
  Database,
  BookOpen,
  FileText,
  Settings,
  TrendingUp,
  LogOut,
  Menu,
  X,
  ChevronLeft,
  Users,
} from 'lucide-react';
import { ProjectSelector } from '@/components/project-selector';

interface NavItem {
  title: string;
  href: string;
  icon: any;
  translationKey: string;
}

const GUEST_EMAIL = 'guest@local.keeltrader';

const navItems: NavItem[] = [
  {
    title: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
    translationKey: 'nav.dashboard',
  },
  {
    title: 'Projects',
    href: '/projects',
    icon: FolderKanban,
    translationKey: 'nav.projects',
  },
  {
    title: 'AI Coaches',
    href: '/coaches',
    icon: Brain,
    translationKey: 'nav.coaches',
  },
  {
    title: 'Chat',
    href: '/chat',
    icon: MessageSquare,
    translationKey: 'nav.chat',
  },
  {
    title: 'Roundtable',
    href: '/roundtable',
    icon: Users,
    translationKey: 'nav.roundtable',
  },
  {
    title: 'Knowledge Base',
    href: '/knowledge',
    icon: Database,
    translationKey: 'nav.knowledge',
  },
  {
    title: 'Trading Journal',
    href: '/journal',
    icon: BookOpen,
    translationKey: 'nav.journal',
  },
  {
    title: 'Analysis',
    href: '/journal/stats',
    icon: TrendingUp,
    translationKey: 'nav.analysis',
  },
  {
    title: 'Reports',
    href: '/reports',
    icon: FileText,
    translationKey: 'nav.reports',
  },
  {
    title: 'Settings',
    href: '/settings',
    icon: Settings,
    translationKey: 'nav.settings',
  },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { t } = useI18n();
  const { user } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
      if (window.innerWidth < 768) {
        setSidebarOpen(false);
      }
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const handleLogout = async () => {
    // Clear auth tokens and redirect to login
    localStorage.removeItem('aiwendy_access_token');
    localStorage.removeItem('aiwendy_refresh_token');
    // Backwards-compat (older key)
    localStorage.removeItem('auth_token');
    router.push('/auth/login');
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside
        className={cn(
          'relative z-20 flex h-full flex-col border-r bg-background transition-all duration-300',
          sidebarOpen ? 'w-64' : 'w-16',
          isMobile && !sidebarOpen && 'hidden'
        )}
      >
        {/* Logo and Toggle */}
        <div className="flex h-16 items-center justify-between border-b px-4">
          {sidebarOpen && (
            <Link href="/dashboard" className="flex items-center gap-2">
              <Brain className="h-6 w-6 text-primary" />
              <span className="text-lg font-bold">KeelTrader</span>
            </Link>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className={cn(!sidebarOpen && 'mx-auto')}
          >
            {sidebarOpen ? (
              <ChevronLeft className="h-4 w-4" />
            ) : (
              <Menu className="h-4 w-4" />
            )}
          </Button>
        </div>

        {/* Navigation */}
        <ProjectSelector collapsed={!sidebarOpen} />

        <ScrollArea className="flex-1 px-3 py-4">
          <nav className="space-y-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href ||
                (item.href !== '/dashboard' && pathname.startsWith(item.href));

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all hover:bg-accent',
                    isActive && 'bg-accent text-accent-foreground',
                    !sidebarOpen && 'justify-center'
                  )}
                  title={!sidebarOpen ? t(item.translationKey as any) : undefined}
                >
                  <Icon className="h-4 w-4" />
                  {sidebarOpen && (
                    <span>{t(item.translationKey as any)}</span>
                  )}
                </Link>
              );
            })}
          </nav>
        </ScrollArea>

        {/* Logout Button */}
        <div className="border-t p-3">
          {user?.email === GUEST_EMAIL && (
            <div
              className={cn(
                'mb-2 flex items-center gap-2',
                !sidebarOpen && 'justify-center'
              )}
            >
              <Badge variant="secondary">Guest</Badge>
              {sidebarOpen && (
                <Link
                  href="/auth/login"
                  className="text-xs text-muted-foreground underline underline-offset-4 hover:text-primary"
                >
                  Sign in
                </Link>
              )}
            </div>
          )}
          <Button
            variant="ghost"
            className={cn(
              'w-full justify-start gap-3',
              !sidebarOpen && 'justify-center px-3'
            )}
            onClick={handleLogout}
          >
            <LogOut className="h-4 w-4" />
            {sidebarOpen && <span>{t('common.logout')}</span>}
          </Button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Mobile Header */}
        {isMobile && (
          <header className="flex h-16 items-center justify-between border-b px-4 md:hidden">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              <Menu className="h-5 w-5" />
            </Button>
            <Link href="/dashboard" className="flex items-center gap-2">
              <Brain className="h-6 w-6 text-primary" />
              <span className="text-lg font-bold">KeelTrader</span>
            </Link>
            <div className="w-10" /> {/* Spacer for centering */}
          </header>
        )}

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto bg-background">
          {children}
        </main>
      </div>

      {/* Mobile Sidebar Overlay */}
      {isMobile && sidebarOpen && (
        <div
          className="fixed inset-0 z-10 bg-background/80 backdrop-blur-sm md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
}
