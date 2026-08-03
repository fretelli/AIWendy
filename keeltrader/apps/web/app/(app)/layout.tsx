'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { AgentOsShell } from '@/components/agentos/agentos-shell';
import { AgentWorkspaceProvider } from '@/components/agentos/workspace-provider';

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isLoading, authRequired } = useAuth();

  useEffect(() => {
    if (authRequired && !isLoading && !user) {
      router.push(`/auth/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [user, isLoading, authRequired, router, pathname]);

  if (isLoading || (authRequired && !user)) {
    return (
      <div className="flex h-dvh items-center justify-center">
        <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  const content = (
    <main className="h-dvh min-h-0 overflow-hidden bg-background">
      <AgentOsShell>{children}</AgentOsShell>
    </main>
  );
  return pathname.startsWith('/agent/workspace')
    ? <AgentWorkspaceProvider>{content}</AgentWorkspaceProvider>
    : content;
}
