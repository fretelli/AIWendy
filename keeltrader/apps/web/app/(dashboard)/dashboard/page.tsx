'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useI18n } from '@/lib/i18n/provider';
import { LanguageSwitcher } from '@/components/ui/language-switcher';
import { toast } from 'sonner';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
  BarChart3,
  Calendar,
  Target,
  Brain,
} from 'lucide-react';
import { API_V1_PREFIX } from '@/lib/config';
import { useActiveProjectId } from '@/lib/active-project';
import type { JournalStatistics } from '@/lib/types/journal';

// Mock data
const mockStats = {
  totalPnL: 12500.50,
  winRate: 0.65,
  totalTrades: 142,
  todayPnL: 850.25,
  weekPnL: 3200.00,
  monthPnL: 8900.00,
  avgWin: 450.00,
  avgLoss: -180.00,
  profitFactor: 2.5,
  sharpeRatio: 1.8,
  maxDrawdown: -0.12,
};

export default function DashboardPage() {
  const { t, locale, formatCurrency, formatNumber, formatDate } = useI18n();
  const [selectedPeriod, setSelectedPeriod] = useState('week');
  const { projectId, ready } = useActiveProjectId();
  const [statsByPeriod, setStatsByPeriod] = useState<Record<string, JournalStatistics> | null>(null);

  const userName = t('dashboard.sampleUserName');

  useEffect(() => {
    if (!ready) return;
    const token = localStorage.getItem('aiwendy_access_token');

    const fetchStats = async () => {
      try {
        const periods = ['today', 'week', 'month', 'year', 'all'] as const;
        const entries = await Promise.all(
          periods.map(async (period) => {
            const params = new URLSearchParams({ period });
            if (projectId) params.set('project_id', projectId);
            const res = await fetch(`${API_V1_PREFIX}/analysis/stats?${params.toString()}`, {
              headers: token ? { Authorization: `Bearer ${token}` } : undefined,
            });
            if (!res.ok) throw new Error(`Failed to fetch stats: ${period}`);
            const data = (await res.json()) as JournalStatistics;
            return [period, data] as const;
          })
        );

        setStatsByPeriod(Object.fromEntries(entries));
      } catch (error) {
        console.error('Error fetching stats:', error);
        toast.error(t('dashboard.errors.loadStats'));
      }
    };

    fetchStats();
  }, [ready, projectId, locale]);

  const statsForPeriod = statsByPeriod?.[selectedPeriod] || null;
  const statsAll = statsByPeriod?.all || null;
  const todayPnL = statsByPeriod?.today?.total_pnl ?? mockStats.todayPnL;
  const weekPnL = statsByPeriod?.week?.total_pnl ?? mockStats.weekPnL;
  const monthPnL = statsByPeriod?.month?.total_pnl ?? mockStats.monthPnL;
  const yearPnL = statsByPeriod?.year?.total_pnl ?? mockStats.totalPnL;

  const totalPnL = statsAll?.total_pnl ?? mockStats.totalPnL;
  const winRatePercent = statsForPeriod?.win_rate ?? (mockStats.winRate * 100);
  const totalTrades = statsForPeriod?.total_trades ?? mockStats.totalTrades;
  const profitFactor = statsAll?.profit_factor ?? mockStats.profitFactor;
  const avgWin = statsForPeriod?.average_win ?? mockStats.avgWin;
  const avgLoss = statsForPeriod?.average_loss ?? mockStats.avgLoss;
  const winningTrades = statsForPeriod?.winning_trades ?? Math.round(mockStats.totalTrades * mockStats.winRate);
  const losingTrades = statsForPeriod?.losing_trades ?? Math.round(mockStats.totalTrades * (1 - mockStats.winRate));

  const emotionalState = (() => {
    const stress = statsForPeriod?.average_stress;
    if (stress == null || stress === 0) return t('dashboard.emotions.calm');
    if (stress <= 2) return t('dashboard.emotions.calm');
    if (stress <= 3.5) return t('dashboard.emotions.neutral');
    return t('dashboard.emotions.stressed');
  })();

  return (
    <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
      {/* Header with language switcher */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {t('dashboard.title')}
          </h1>
          <p className="text-muted-foreground">
            {t('dashboard.welcome', { name: userName })}
          </p>
        </div>
        <LanguageSwitcher />
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {t('dashboard.totalPnL')}
            </CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(totalPnL)}
            </div>
            <p className="text-xs text-muted-foreground">
              {totalPnL > 0 ? (
                <span className="text-green-600 flex items-center gap-1">
                  <TrendingUp className="h-3 w-3" />
                  +{formatNumber(totalPnL / 100)}%
                </span>
              ) : (
                <span className="text-red-600 flex items-center gap-1">
                  <TrendingDown className="h-3 w-3" />
                  {formatNumber(totalPnL / 100)}%
                </span>
              )}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {t('dashboard.winRate')}
            </CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatNumber(winRatePercent)}%
            </div>
            <p className="text-xs text-muted-foreground">
              {t('dashboard.totalTrades')}: {totalTrades}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {t('dashboard.profitFactor')}
            </CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatNumber(profitFactor)}
            </div>
            <p className="text-xs text-muted-foreground">
              {t('dashboard.sharpeRatio')}: {formatNumber(mockStats.sharpeRatio)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {t('dashboard.emotionalState')}
            </CardTitle>
            <Brain className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {emotionalState}
            </div>
            <p className="text-xs text-muted-foreground">
              {t('dashboard.riskScore')}: 35/100
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Performance Tabs */}
      <Card>
        <CardHeader>
          <CardTitle>{t('dashboard.performance')}</CardTitle>
          <CardDescription>
            {t('dashboard.lastUpdated', { date: formatDate(new Date(), 'long') })}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={selectedPeriod} onValueChange={setSelectedPeriod}>
            <TabsList>
              <TabsTrigger value="today">{t('dashboard.todaysPnL')}</TabsTrigger>
              <TabsTrigger value="week">{t('dashboard.weekPnL')}</TabsTrigger>
              <TabsTrigger value="month">{t('dashboard.monthPnL')}</TabsTrigger>
              <TabsTrigger value="year">{t('dashboard.yearPnL')}</TabsTrigger>
            </TabsList>
            <TabsContent value="today" className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-lg font-medium">{t('dashboard.todaysPnL')}</span>
                <span className={`text-2xl font-bold ${todayPnL > 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatCurrency(todayPnL)}
                </span>
              </div>
            </TabsContent>
            <TabsContent value="week" className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-lg font-medium">{t('dashboard.weekPnL')}</span>
                <span className={`text-2xl font-bold ${weekPnL > 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatCurrency(weekPnL)}
                </span>
              </div>
            </TabsContent>
            <TabsContent value="month" className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-lg font-medium">{t('dashboard.monthPnL')}</span>
                <span className={`text-2xl font-bold ${monthPnL > 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatCurrency(monthPnL)}
                </span>
              </div>
            </TabsContent>
            <TabsContent value="year" className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-lg font-medium">{t('dashboard.yearPnL')}</span>
                <span className="text-2xl font-bold text-green-600">
                  {formatCurrency(yearPnL)}
                </span>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Trading Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>{t('dashboard.winningTrades')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">{t('dashboard.avgWin')}</span>
                <span className="font-medium">{formatCurrency(avgWin)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">{t('common.all')}</span>
                <span className="font-medium">
                  {winningTrades}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('dashboard.losingTrades')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">{t('dashboard.avgLoss')}</span>
                <span className="font-medium">{formatCurrency(avgLoss)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">{t('common.all')}</span>
                <span className="font-medium">
                  {losingTrades}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('dashboard.maxDrawdown')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">{t('dashboard.percentage')}</span>
                <span className="font-medium text-red-600">
                  {formatNumber(mockStats.maxDrawdown * 100)}%
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">
                  {t('dashboard.recoveryTime')}
                </span>
                <span className="font-medium">
                  {t('dashboard.recoveryDays', { days: 12 })}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Call to Action */}
      <Card>
        <CardHeader>
          <CardTitle>{t('dashboard.suggestions')}</CardTitle>
        </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">
                {t('dashboard.suggestionsIntro')}
              </p>
              <ul className="list-disc list-inside space-y-1 text-sm">
                <li>{t('dashboard.suggestionsItems.keepStrategy')}</li>
                <li>{t('dashboard.suggestionsItems.trailingStops')}</li>
                <li>{t('dashboard.suggestionsItems.reviewJournal')}</li>
              </ul>
            <div className="flex gap-2 pt-4">
              <Button>
                <BarChart3 className="mr-2 h-4 w-4" />
                {t('nav.analysis')}
              </Button>
              <Button variant="outline">
                <Calendar className="mr-2 h-4 w-4" />
                {t('nav.journal')}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
