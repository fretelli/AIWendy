'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { RadarChart } from '@/components/rpg/RadarChart';
import { XPBar } from '@/components/rpg/XPBar';
import { RankBadge } from '@/components/rpg/RankBadge';
import { CharacterCard } from '@/components/rpg/CharacterCard';
import { getCharacter, getCharacterCard, recalculateCharacter } from '@/lib/rpg-api';
import type { CharacterData } from '@/lib/rpg-api';

export default function CharacterPage() {
  const [character, setCharacter] = useState<CharacterData | null>(null);
  const [recentAchievements, setRecentAchievements] = useState<{ id: string; name: string; icon: string; rarity: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [recalculating, setRecalculating] = useState(false);

  useEffect(() => {
    Promise.all([getCharacter(), getCharacterCard()])
      .then(([char, card]) => {
        setCharacter(char);
        setRecentAchievements(card.recent_achievements || []);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleRecalculate = async () => {
    setRecalculating(true);
    try {
      const result = await recalculateCharacter();
      setCharacter((prev) => prev ? {
        ...prev,
        level: result.level,
        xp: result.xp,
        rank: result.rank,
        attributes: result.attributes,
      } : prev);
      if (result.newly_unlocked.length > 0) {
        alert(`New achievements unlocked: ${result.newly_unlocked.map((a) => a.name).join(', ')}`);
      }
    } catch (e) {
      console.error(e);
    }
    setRecalculating(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!character) return <div className="p-6">Failed to load character</div>;

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-6 overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Character</h1>
        <Button onClick={handleRecalculate} disabled={recalculating} size="sm">
          {recalculating ? 'Recalculating...' : 'Recalculate'}
        </Button>
      </div>

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
