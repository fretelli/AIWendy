import type { ReactNode } from 'react'
import { CheckCircle2, LockKeyhole } from 'lucide-react'

import { KeelMark, ThemeMenu } from '@/components/keel-brand'

export function AuthShell({ children, eyebrow = 'Private fundamental research' }: { children: ReactNode; eyebrow?: string }) {
  return <main className="grid min-h-dvh bg-background lg:grid-cols-[minmax(0,1.08fr)_minmax(420px,.92fr)]">
    <section className="chart-surface relative hidden overflow-hidden border-r px-12 py-10 lg:flex lg:flex-col">
      <KeelMark />
      <div className="my-auto max-w-xl"><div className="mb-5 flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-[hsl(var(--copper-foreground))]"><span className="h-px w-10 bg-[hsl(var(--copper)/.7)]" />{eyebrow}</div><h1 className="font-display text-6xl font-medium leading-[.98] tracking-[-0.045em]">把判断留在证据航迹上。</h1><p className="mt-6 max-w-lg text-base leading-7 text-muted-foreground">围绕你的自选公司，持续整理财务数据、研报证据、关键风险与证伪条件。</p><div className="mt-10 grid max-w-md gap-3 text-sm"><div className="flex items-center gap-3"><CheckCircle2 className="h-4 w-4 text-[hsl(var(--accent))]" />只读基本面研究，不执行交易</div><div className="flex items-center gap-3"><LockKeyhole className="h-4 w-4 text-[hsl(var(--copper-foreground))]" />模型凭证加密保存，私有部署自行 BYOK</div></div></div>
      <div className="font-data text-[10px] uppercase tracking-[0.16em] text-muted-foreground">KeelTrader · Research, not execution</div>
    </section>
    <section className="relative flex min-h-dvh items-center justify-center px-5 py-12 sm:px-10"><div className="absolute left-5 top-5 lg:hidden"><KeelMark /></div><div className="absolute right-5 top-5"><ThemeMenu /></div><div className="w-full max-w-md">{children}</div></section>
  </main>
}
