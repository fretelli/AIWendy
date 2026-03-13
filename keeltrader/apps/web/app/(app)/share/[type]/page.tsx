'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { CharacterCard } from '@/components/rpg/CharacterCard';
import { Card, CardContent } from '@/components/ui/card';
import { RadarChart } from '@/components/rpg/RadarChart';
import { XPBar } from '@/components/rpg/XPBar';
import { RankBadge } from '@/components/rpg/RankBadge';
import { getCharacterCard, getWeeklyCard } from '@/lib/rpg-api';
import type { CharacterData, WeeklyCardData } from '@/lib/rpg-api';

export default function SharePage() {
  const params = useParams();
  const type = params.type as string;
  const [characterData, setCharacterData] = useState<(CharacterData & { recent_achievements: any[] }) | null>(null);
  const [weeklyData, setWeeklyData] = useState<WeeklyCardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        if (type === 'character') {
          const data = await getCharacterCard();
          setCharacterData(data);
        } else if (type === 'weekly') {
          const data = await getWeeklyCard();
          setWeeklyData(data);
        } else {
          setError('Unknown card type');
        }
      } catch {
        setError('Failed to load card data. Please log in.');
      }
      setLoading(false);
    };
    load();
  }, [type]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-muted-foreground">{error}</p>
      </div>
    );
  }

  if (type === 'character' && characterData) {
    return (
      <div className="p-4 md:p-6 max-w-md mx-auto">
        <CharacterCard
          character={characterData}
          recentAchievements={characterData.recent_achievements}
        />
      </div>
    );
  }

  if (type === 'weekly' && weeklyData) {
    return (
      <div className="p-4 md:p-6 max-w-md mx-auto">
        <Card className="bg-gradient-to-br from-slate-900 to-slate-800 text-white border-0">
          <CardContent className="p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold">{weeklyData.nickname}</h2>
                <p className="text-sm text-slate-400">Weekly Report - {weeklyData.week_start}</p>
              </div>
              <RankBadge rank={weeklyData.rank} size="lg" />
            </div>

            <div className="grid grid-cols-2 gap-4 text-center">
              <div>
                <div className="text-2xl font-bold">{weeklyData.stats.total_trades}</div>
                <div className="text-xs text-slate-400">Total Trades</div>
              </div>
              <div>
                <div className="text-2xl font-bold">{weeklyData.stats.win_rate}%</div>
                <div className="text-xs text-slate-400">Win Rate</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-green-400">
                  {weeklyData.stats.wins}W
                </div>
                <div className="text-xs text-slate-400">Wins</div>
              </div>
              <div>
                <div className={`text-2xl font-bold ${weeklyData.stats.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  ${weeklyData.stats.total_pnl >= 0 ? '+' : ''}{weeklyData.stats.total_pnl}
                </div>
                <div className="text-xs text-slate-400">PnL</div>
              </div>
            </div>

            <RadarChart attributes={weeklyData.attributes} />

            <div className="text-center text-xs text-slate-500">
              KeelTrader RPG - Lv.{weeklyData.level}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return null;
}
