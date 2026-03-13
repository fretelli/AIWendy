'use client';

import { Badge } from '@/components/ui/badge';

const RANK_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  bronze: { label: 'Bronze', color: 'text-orange-700', bg: 'bg-orange-100 dark:bg-orange-900/30' },
  silver: { label: 'Silver', color: 'text-gray-500', bg: 'bg-gray-100 dark:bg-gray-800/50' },
  gold: { label: 'Gold', color: 'text-yellow-600', bg: 'bg-yellow-100 dark:bg-yellow-900/30' },
  platinum: { label: 'Platinum', color: 'text-cyan-600', bg: 'bg-cyan-100 dark:bg-cyan-900/30' },
  diamond: { label: 'Diamond', color: 'text-blue-500', bg: 'bg-blue-100 dark:bg-blue-900/30' },
};

interface RankBadgeProps {
  rank: string;
  size?: 'sm' | 'lg';
}

export function RankBadge({ rank, size = 'sm' }: RankBadgeProps) {
  const config = RANK_CONFIG[rank] || RANK_CONFIG.bronze;

  return (
    <Badge
      variant="outline"
      className={`${config.color} ${config.bg} border-current ${size === 'lg' ? 'text-base px-3 py-1' : ''}`}
    >
      {config.label}
    </Badge>
  );
}
