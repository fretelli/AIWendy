'use client';

import { Card, CardContent } from '@/components/ui/card';
import type { AchievementData } from '@/lib/rpg-api';

const RARITY_STYLES: Record<string, string> = {
  common: 'border-gray-300 dark:border-gray-600',
  rare: 'border-blue-400 dark:border-blue-500',
  epic: 'border-purple-500 dark:border-purple-400',
  legendary: 'border-yellow-500 dark:border-yellow-400 shadow-yellow-500/20 shadow-sm',
};

interface AchievementCardProps {
  achievement: AchievementData;
}

export function AchievementCard({ achievement }: AchievementCardProps) {
  const locked = !achievement.unlocked;
  const rarityStyle = RARITY_STYLES[achievement.rarity] || RARITY_STYLES.common;

  return (
    <Card className={`${rarityStyle} border-2 ${locked ? 'opacity-40 grayscale' : ''} transition-all hover:scale-[1.02]`}>
      <CardContent className="p-4 text-center space-y-2">
        <div className="text-3xl">{achievement.icon || (locked ? '' : '')}</div>
        <h3 className="font-semibold text-sm">{achievement.name}</h3>
        <p className="text-xs text-muted-foreground">{achievement.description}</p>
        <div className="flex items-center justify-center gap-2 text-xs">
          <span className={`capitalize font-medium ${locked ? '' : 'text-primary'}`}>
            {achievement.rarity}
          </span>
          <span className="text-muted-foreground">+{achievement.xp_reward} XP</span>
        </div>
        {achievement.unlocked_at && (
          <p className="text-xs text-muted-foreground">
            {new Date(achievement.unlocked_at).toLocaleDateString()}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
