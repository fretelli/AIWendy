'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  Sword,
  BarChart3,
  Trophy,
  ScrollText,
  Crown,
  MessageSquare,
  Settings,
  LogOut,
  Menu,
  X,
} from 'lucide-react';

const NAV_ITEMS = [
  { href: '/character', icon: Sword, label: 'Character' },
  { href: '/chat', icon: MessageSquare, label: 'Chat' },
  { href: '/achievements', icon: Trophy, label: 'Achievements' },
  { href: '/quests', icon: ScrollText, label: 'Quests' },
  { href: '/leaderboard', icon: Crown, label: 'Leaderboard' },
  { href: '/settings', icon: Settings, label: 'Settings' },
];

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isLoading } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/auth/login');
    }
  }, [user, isLoading, router]);

  const handleLogout = () => {
    localStorage.removeItem('keeltrader_access_token');
    localStorage.removeItem('keeltrader_refresh_token');
    localStorage.removeItem('auth_token');
    router.push('/auth/login');
  };

  if (isLoading || !user) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-background">
      {/* Top bar */}
      <header className="flex h-14 items-center justify-between border-b px-4">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
          <Link href="/character" className="flex items-center gap-2">
            <span className="text-lg font-bold">KeelTrader</span>
            <span className="text-xs bg-primary/10 text-primary px-1.5 py-0.5 rounded">RPG</span>
          </Link>
        </div>

        <nav className="hidden md:flex items-center gap-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link key={item.href} href={item.href}>
                <Button
                  variant={isActive ? 'secondary' : 'ghost'}
                  size="sm"
                  className="gap-2"
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Button>
              </Link>
            );
          })}
        </nav>

        <Button variant="ghost" size="sm" onClick={handleLogout} className="gap-2">
          <LogOut className="h-4 w-4" />
          <span className="hidden md:inline">Logout</span>
        </Button>
      </header>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b p-2 space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link key={item.href} href={item.href} onClick={() => setMobileMenuOpen(false)}>
                <Button
                  variant={isActive ? 'secondary' : 'ghost'}
                  className="w-full justify-start gap-2"
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Button>
              </Link>
            );
          })}
        </div>
      )}

      {/* Content */}
      <main className="flex-1 overflow-hidden">
        {children}
      </main>
    </div>
  );
}
