'use client'

import { Anchor } from 'lucide-react'
import { useTheme } from 'next-themes'
import { Moon, Sun, Monitor } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'

export function KeelMark({ compact = false }: { compact?: boolean }) {
  return <span className="inline-flex items-center gap-2.5">
    <span className="relative grid h-8 w-8 place-items-center rounded-full border border-[hsl(var(--copper)/.55)] bg-card shadow-sm">
      <Anchor className="h-4 w-4 text-[hsl(var(--copper-foreground))]" strokeWidth={1.7} />
      <span className="absolute -bottom-0.5 h-px w-5 bg-[hsl(var(--accent))]" />
    </span>
    {!compact && <span className="font-display text-xl font-semibold tracking-[-0.02em]">KeelTrader</span>}
  </span>
}

export function ThemeMenu() {
  const { setTheme, theme } = useTheme()
  const icon = theme === 'dark' ? <Moon className="h-4 w-4" /> : theme === 'light' ? <Sun className="h-4 w-4" /> : <Monitor className="h-4 w-4" />
  return <DropdownMenu>
    <DropdownMenuTrigger asChild><Button variant="ghost" size="icon" aria-label="切换主题">{icon}</Button></DropdownMenuTrigger>
    <DropdownMenuContent align="end">
      <DropdownMenuItem onClick={() => setTheme('light')}><Sun className="mr-2 h-4 w-4" />明亮海图</DropdownMenuItem>
      <DropdownMenuItem onClick={() => setTheme('dark')}><Moon className="mr-2 h-4 w-4" />夜航模式</DropdownMenuItem>
      <DropdownMenuItem onClick={() => setTheme('system')}><Monitor className="mr-2 h-4 w-4" />跟随系统</DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
}
