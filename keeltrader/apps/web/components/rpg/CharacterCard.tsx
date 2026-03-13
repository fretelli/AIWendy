'use client';

import { useRef, useCallback } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { RadarChart } from './RadarChart';
import { XPBar } from './XPBar';
import { RankBadge } from './RankBadge';
import type { CharacterData } from '@/lib/rpg-api';

interface CharacterCardProps {
  character: CharacterData;
  recentAchievements?: { id: string; name: string; icon: string; rarity: string }[];
  showShareButtons?: boolean;
}

export function CharacterCard({ character, recentAchievements, showShareButtons = true }: CharacterCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);

  const handleDownload = useCallback(async () => {
    if (!cardRef.current) return;
    try {
      const html2canvas = (await import('html2canvas')).default;
      const canvas = await html2canvas(cardRef.current, {
        backgroundColor: '#1a1a2e',
        scale: 2,
      });
      const link = document.createElement('a');
      link.download = `${character.nickname}-trading-card.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } catch {
      // html2canvas not available
    }
  }, [character.nickname]);

  const handleCopyLink = useCallback(() => {
    const url = `${window.location.origin}/share/character`;
    navigator.clipboard.writeText(url);
  }, []);

  return (
    <div className="space-y-3">
      <div ref={cardRef} className="rounded-xl overflow-hidden">
        <Card className="bg-gradient-to-br from-slate-900 to-slate-800 text-white border-0">
          <CardContent className="p-6 space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold">{character.nickname}</h2>
                <p className="text-sm text-slate-400">Trading RPG</p>
              </div>
              <RankBadge rank={character.rank} size="lg" />
            </div>

            {/* XP */}
            <XPBar level={character.level} xp={character.xp} xpToNextLevel={character.xp_to_next_level} />

            {/* Radar */}
            <RadarChart attributes={character.attributes} />

            {/* Recent achievements */}
            {recentAchievements && recentAchievements.length > 0 && (
              <div className="flex gap-2 justify-center flex-wrap">
                {recentAchievements.map((a) => (
                  <span key={a.id} className="text-lg" title={a.name}>
                    {a.icon || ''}
                  </span>
                ))}
              </div>
            )}

            {/* Stats summary */}
            <div className="grid grid-cols-5 gap-2 text-center text-xs">
              {Object.entries(character.attributes).map(([key, val]) => (
                <div key={key}>
                  <div className="font-bold text-lg">{val}</div>
                  <div className="text-slate-400 capitalize">{key.replace('_', ' ').slice(0, 6)}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {showShareButtons && (
        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="flex-1" onClick={handleDownload}>
            Download PNG
          </Button>
          <Button variant="outline" size="sm" className="flex-1" onClick={handleCopyLink}>
            Copy Link
          </Button>
        </div>
      )}
    </div>
  );
}
