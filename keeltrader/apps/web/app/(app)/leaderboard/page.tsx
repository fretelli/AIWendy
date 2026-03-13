'use client';

import { useEffect, useState } from 'react';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { RankBadge } from '@/components/rpg/RankBadge';
import { getLeaderboard } from '@/lib/rpg-api';
import type { LeaderboardEntry } from '@/lib/rpg-api';

export default function LeaderboardPage() {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [period, setPeriod] = useState('weekly');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getLeaderboard(period)
      .then((data) => setEntries(data.entries))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [period]);

  return (
    <div className="p-4 md:p-6 max-w-3xl mx-auto space-y-6 overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Leaderboard</h1>
        <Tabs value={period} onValueChange={setPeriod}>
          <TabsList>
            <TabsTrigger value="weekly">Weekly</TabsTrigger>
            <TabsTrigger value="monthly">Monthly</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" />
            </div>
          ) : entries.length === 0 ? (
            <div className="text-center text-muted-foreground py-12">
              No leaderboard data yet. Start trading!
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">#</TableHead>
                  <TableHead>Trader</TableHead>
                  <TableHead className="text-center">Level</TableHead>
                  <TableHead className="text-center">Rank</TableHead>
                  <TableHead className="text-right">XP</TableHead>
                  <TableHead className="text-right">Win Rate</TableHead>
                  <TableHead className="text-right">PF</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {entries.map((entry) => (
                  <TableRow
                    key={entry.position}
                    className={entry.is_current_user ? 'bg-primary/5 font-semibold' : ''}
                  >
                    <TableCell>
                      {entry.position <= 3
                        ? ['', '', ''][entry.position - 1]
                        : entry.position}
                    </TableCell>
                    <TableCell>{entry.nickname}</TableCell>
                    <TableCell className="text-center">Lv.{entry.level}</TableCell>
                    <TableCell className="text-center">
                      <RankBadge rank={entry.rank} />
                    </TableCell>
                    <TableCell className="text-right">{entry.xp}</TableCell>
                    <TableCell className="text-right">{entry.win_rate}%</TableCell>
                    <TableCell className="text-right">{entry.profit_factor}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
