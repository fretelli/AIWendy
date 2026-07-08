'use client';

import { useCallback, useState } from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { RadarChart } from '@/components/rpg/RadarChart';
import { XPBar } from '@/components/rpg/XPBar';
import { RankBadge } from '@/components/rpg/RankBadge';
import { CharacterCard } from '@/components/rpg/CharacterCard';
import { getCharacter, getCharacterCard, recalculateCharacter } from '@/lib/rpg-api';
import type { CharacterData } from '@/lib/rpg-api';
import { useAsyncData } from '@/hooks/use-async-data';
import { clientErrorMessage, logClientError } from '@/lib/client-log';

type CharacterCardAchievement = { id: string; name: string; icon: string; rarity: string };
type CharacterPageData = {
  character: CharacterData | null;
  recentAchievements: CharacterCardAchievement[];
};

const EMPTY_CHARACTER_DATA: CharacterPageData = {
  character: null,
  recentAchievements: [],
};

export default function CharacterPage() {
  const [recalculating, setRecalculating] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const loadCharacter = useCallback(async (): Promise<CharacterPageData> => {
    const [character, card] = await Promise.all([getCharacter(), getCharacterCard()]);
    return {
      character,
      recentAchievements: card.recent_achievements || [],
    };
  }, []);

  const { data, setData, loading, error } = useAsyncData(loadCharacter, {
    initialData: EMPTY_CHARACTER_DATA,
    errorMessage: 'Failed to load character.',
    logScope: 'character.load',
  });

  const handleRecalculate = async () => {
    setActionError(null);
    setRecalculating(true);
    try {
      const result = await recalculateCharacter();
      setData((prev) => ({
        ...prev,
        character: prev.character ? {
          ...prev.character,
          level: result.level,
          xp: result.xp,
          rank: result.rank,
          attributes: result.attributes,
        } : prev.character,
      }));
      if (result.newly_unlocked.length > 0) {
        alert(`New achievements unlocked: ${result.newly_unlocked.map((a) => a.name).join(', ')}`);
      }
    } catch (e) {
      logClientError('character.recalculate', e);
      setActionError(clientErrorMessage(e, 'Failed to recalculate character.'));
    } finally {
      setRecalculating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  const { character, recentAchievements } = data;

  if (!character) {
    return (
      <div className="p-6">
        <Alert variant="destructive">
          <AlertDescription>{error || 'Failed to load character.'}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-6 overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Character</h1>
        <Button onClick={handleRecalculate} disabled={recalculating} size="sm">
          {recalculating ? 'Recalculating...' : 'Recalculate'}
        </Button>
      </div>
      {(error || actionError) && (
        <Alert variant="destructive">
          <AlertDescription>{actionError || error}</AlertDescription>
        </Alert>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        {/* Left: Stats */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>{character.nickname}</CardTitle>
                <RankBadge rank={character.rank} size="lg" />
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <XPBar level={character.level} xp={character.xp} xpToNextLevel={character.xp_to_next_level} />
              <div className="grid grid-cols-5 gap-2 text-center text-sm">
                {Object.entries(character.attributes).map(([key, val]) => (
                  <div key={key}>
                    <div className="font-bold text-xl">{val}</div>
                    <div className="text-xs text-muted-foreground capitalize">
                      {key.replace('_', '\n').split('\n')[0]}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Attribute Radar</CardTitle>
            </CardHeader>
            <CardContent>
              <RadarChart attributes={character.attributes} />
            </CardContent>
          </Card>
        </div>

        {/* Right: Shareable Card */}
        <div>
          <h2 className="text-lg font-semibold mb-3">Trading Card</h2>
          <CharacterCard
            character={character}
            recentAchievements={recentAchievements}
          />
        </div>
      </div>
    </div>
  );
}
