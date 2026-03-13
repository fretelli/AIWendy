'use client';

import { useEffect, useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AchievementCard } from '@/components/rpg/AchievementCard';
import { getAchievements } from '@/lib/rpg-api';
import type { AchievementData } from '@/lib/rpg-api';

const CATEGORIES = ['all', 'trading', 'discipline', 'milestones', 'streaks'] as const;

export default function AchievementsPage() {
  const [achievements, setAchievements] = useState<AchievementData[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    getAchievements()
      .then((data) => setAchievements(data.achievements))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  const filtered = filter === 'all'
    ? achievements
    : achievements.filter((a) => a.category === filter);

  const unlocked = filtered.filter((a) => a.unlocked);
  const locked = filtered.filter((a) => !a.unlocked);

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-6 overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Achievements</h1>
        <span className="text-sm text-muted-foreground">
          {achievements.filter((a) => a.unlocked).length} / {achievements.length} unlocked
        </span>
      </div>

      <Tabs value={filter} onValueChange={setFilter}>
        <TabsList>
          {CATEGORIES.map((cat) => (
            <TabsTrigger key={cat} value={cat} className="capitalize">
              {cat}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {/* Unlocked */}
      {unlocked.length > 0 && (
        <div>
          <h2 className="text-sm font-medium text-muted-foreground mb-3">Unlocked</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {unlocked.map((a) => (
              <AchievementCard key={a.id} achievement={a} />
            ))}
          </div>
        </div>
      )}

      {/* Locked */}
      {locked.length > 0 && (
        <div>
          <h2 className="text-sm font-medium text-muted-foreground mb-3">Locked</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {locked.map((a) => (
              <AchievementCard key={a.id} achievement={a} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
