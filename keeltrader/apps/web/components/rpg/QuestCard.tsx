'use client';

import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import type { QuestData } from '@/lib/rpg-api';

const TYPE_LABELS: Record<string, string> = {
  daily: 'Daily',
  weekly: 'Weekly',
  special: 'Special',
};

interface QuestCardProps {
  quest: QuestData;
  onStart?: (questId: string) => void;
  showStartButton?: boolean;
}

export function QuestCard({ quest, onStart, showStartButton = false }: QuestCardProps) {
  const progress = quest.progress;
  const progressPercent = progress
    ? Math.min(100, (progress.current / Math.max(1, progress.target)) * 100)
    : 0;
  const isCompleted = quest.status === 'completed';

  return (
    <Card className={isCompleted ? 'border-green-500/50' : ''}>
      <CardContent className="p-4 space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div className="space-y-1 flex-1">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-sm">{quest.name}</h3>
              <Badge variant="outline" className="text-xs">
                {TYPE_LABELS[quest.quest_type] || quest.quest_type}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">{quest.description}</p>
          </div>
          <span className="text-sm font-medium text-primary whitespace-nowrap">
            +{quest.xp_reward} XP
          </span>
        </div>

        {progress && (
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Progress</span>
              <span>{progress.current} / {progress.target}</span>
            </div>
            <Progress value={progressPercent} className="h-2" />
          </div>
        )}

        {showStartButton && onStart && (
          <Button
            size="sm"
            variant="outline"
            className="w-full"
            onClick={() => onStart(quest.quest_id)}
          >
            Start Quest
          </Button>
        )}

        {isCompleted && (
          <div className="text-center text-xs text-green-600 font-medium">
            Completed {quest.completed_at ? new Date(quest.completed_at).toLocaleDateString() : ''}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
