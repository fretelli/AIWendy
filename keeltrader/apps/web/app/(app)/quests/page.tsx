'use client';

import { useEffect, useState, useCallback } from 'react';
import { QuestCard } from '@/components/rpg/QuestCard';
import { getQuests, startQuest } from '@/lib/rpg-api';
import type { QuestData } from '@/lib/rpg-api';

export default function QuestsPage() {
  const [active, setActive] = useState<QuestData[]>([]);
  const [available, setAvailable] = useState<QuestData[]>([]);
  const [completed, setCompleted] = useState<QuestData[]>([]);
  const [loading, setLoading] = useState(true);

  const loadQuests = useCallback(async () => {
    try {
      const data = await getQuests();
      setActive(data.active);
      setAvailable(data.available);
      setCompleted(data.completed);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadQuests(); }, [loadQuests]);

  const handleStart = async (questId: string) => {
    try {
      await startQuest(questId);
      await loadQuests();
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 max-w-3xl mx-auto space-y-6 overflow-y-auto h-full">
      <h1 className="text-2xl font-bold">Quest Board</h1>

      {/* Active quests */}
      {active.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Active Quests</h2>
          {active.map((q) => (
            <QuestCard key={q.id || q.quest_id} quest={q} />
          ))}
        </div>
      )}

      {/* Available quests */}
      {available.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Available Quests</h2>
          {available.map((q) => (
            <QuestCard key={q.quest_id} quest={q} showStartButton onStart={handleStart} />
          ))}
        </div>
      )}

      {/* Completed */}
      {completed.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-muted-foreground">Completed</h2>
          {completed.map((q) => (
            <QuestCard key={q.id || q.quest_id} quest={q} />
          ))}
        </div>
      )}

      {active.length === 0 && available.length === 0 && (
        <div className="text-center text-muted-foreground py-12">
          No quests available. Check back later!
        </div>
      )}
    </div>
  );
}
