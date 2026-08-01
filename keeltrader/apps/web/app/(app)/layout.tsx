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
  const { user, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading && !user) {
      router.push(`/auth/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [user, isLoading, router, pathname]);

  if (isLoading || !user) {
    return (
      <div className="flex h-dvh items-center justify-center">
        <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <main className="h-dvh min-h-0 overflow-hidden bg-background">
      <AgentWorkspaceProvider><AgentOsShell>{children}</AgentOsShell></AgentWorkspaceProvider>
    </main>
  );
}
