'use client';

import { useCallback, useState } from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { QuestCard } from '@/components/rpg/QuestCard';
import { getQuests, startQuest } from '@/lib/rpg-api';
import type { QuestData } from '@/lib/rpg-api';
import { useAsyncData } from '@/hooks/use-async-data';
import { clientErrorMessage, logClientError } from '@/lib/client-log';

const EMPTY_QUESTS: { active: QuestData[]; available: QuestData[]; completed: QuestData[] } = {
  active: [],
  available: [],
  completed: [],
};

export default function QuestsPage() {
  const loadQuests = useCallback(() => getQuests(), []);
  const { data, loading, error, reload } = useAsyncData(loadQuests, {
    initialData: EMPTY_QUESTS,
    errorMessage: 'Failed to load quests.',
    logScope: 'quests.load',
  });
  const [actionError, setActionError] = useState<string | null>(null);

  const handleStart = async (questId: string) => {
    setActionError(null);
    try {
      await startQuest(questId);
      await reload();
    } catch (e) {
      logClientError('quests.start', e);
      setActionError(clientErrorMessage(e, 'Failed to start quest.'));
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
      {(error || actionError) && (
        <Alert variant="destructive">
          <AlertDescription>{actionError || error}</AlertDescription>
        </Alert>
      )}

      {/* Active quests */}
      {data.active.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Active Quests</h2>
          {data.active.map((q) => (
            <QuestCard key={q.id || q.quest_id} quest={q} />
          ))}
        </div>
      )}

      {/* Available quests */}
      {data.available.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Available Quests</h2>
          {data.available.map((q) => (
            <QuestCard key={q.quest_id} quest={q} showStartButton onStart={handleStart} />
          ))}
        </div>
      )}

      {/* Completed */}
      {data.completed.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-muted-foreground">Completed</h2>
          {data.completed.map((q) => (
            <QuestCard key={q.id || q.quest_id} quest={q} />
          ))}
        </div>
      )}

      {data.active.length === 0 && data.available.length === 0 && (
        <div className="text-center text-muted-foreground py-12">
          No quests available. Check back later!
        </div>
      )}
    </div>
  );
}
