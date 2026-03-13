'use client';

import { Progress } from '@/components/ui/progress';

interface XPBarProps {
  level: number;
  xp: number;
  xpToNextLevel: number;
}

export function XPBar({ level, xp, xpToNextLevel }: XPBarProps) {
  const xpInCurrentLevel = xp % 100;
  const progress = xpToNextLevel > 0 ? (xpInCurrentLevel / 100) * 100 : 100;

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="font-semibold">Lv.{level}</span>
        <span className="text-muted-foreground">{xpInCurrentLevel} / 100 XP</span>
      </div>
      <Progress value={progress} className="h-3" />
    </div>
  );
}
