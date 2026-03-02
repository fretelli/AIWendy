'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  TradeDirection,
  TradeResult,
  RuleViolationType,
  JournalCreate
} from '@/lib/types/journal';
import { journalApi } from '@/lib/api/journal';
import { getActiveProjectId } from '@/lib/active-project';
import { useI18n } from '@/lib/i18n/provider';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

const ruleViolationKeys: Record<RuleViolationType, string> = {
  [RuleViolationType.EARLY_EXIT]: 'journalNew.ruleViolations.earlyExit',
  [RuleViolationType.LATE_EXIT]: 'journalNew.ruleViolations.lateExit',
  [RuleViolationType.NO_STOP_LOSS]: 'journalNew.ruleViolations.noStopLoss',
  [RuleViolationType.OVER_LEVERAGE]: 'journalNew.ruleViolations.overLeverage',
  [RuleViolationType.REVENGE_TRADE]: 'journalNew.ruleViolations.revengeTrade',
  [RuleViolationType.FOMO]: 'journalNew.ruleViolations.fomo',
  [RuleViolationType.POSITION_SIZE]: 'journalNew.ruleViolations.positionSize',
  [RuleViolationType.OTHER]: 'journalNew.ruleViolations.other',
};

export default function NewJournalEntry() {
  const router = useRouter();
  const { t } = useI18n();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState<JournalCreate>({
    symbol: '',
    market: '',
    direction: TradeDirection.LONG,
    trade_date: new Date().toISOString().slice(0, 16),

    entry_time: '',
    entry_price: undefined,
    position_size: undefined,

    exit_time: '',
    exit_price: undefined,

    result: TradeResult.OPEN,
    pnl_amount: undefined,
    pnl_percentage: undefined,

    stop_loss: undefined,
    take_profit: undefined,
    risk_reward_ratio: undefined,

    emotion_before: undefined,
    emotion_during: undefined,
    emotion_after: undefined,

    confidence_level: undefined,
    stress_level: undefined,
    followed_rules: true,
    rule_violations: [],

    setup_description: '',
    exit_reason: '',
    lessons_learned: '',
    notes: '',

    tags: [],
    strategy_name: '',

    screenshots: []
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      // Calculate PnL if entry and exit prices are provided
      if (formData.entry_price && formData.exit_price && formData.position_size) {
        const pnl = (formData.exit_price - formData.entry_price) * formData.position_size;
        formData.pnl_amount = formData.direction === TradeDirection.SHORT ? -pnl : pnl;
        formData.pnl_percentage = (pnl / (formData.entry_price * formData.position_size)) * 100;
      }

      const projectId = getActiveProjectId();
      await journalApi.create({ ...formData, project_id: projectId || undefined });
      router.push('/journal');
    } catch (err) {
      setError(err instanceof Error ? err.message : t('journalNew.createFailed'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRuleViolationChange = (violation: RuleViolationType) => {
    setFormData(prev => ({
      ...prev,
      rule_violations: prev.rule_violations.includes(violation)
        ? prev.rule_violations.filter(v => v !== violation)
        : [...prev.rule_violations, violation],
      followed_rules: false
    }));
  };

  const handleTagInput = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const input = e.currentTarget;
      const tag = input.value.trim();

      if (tag && !formData.tags.includes(tag)) {
        setFormData(prev => ({
          ...prev,
          tags: [...prev.tags, tag]
        }));
        input.value = '';
      }
    }
  };

  const removeTag = (tag: string) => {
    setFormData(prev => ({
      ...prev,
      tags: prev.tags.filter(t => t !== tag)
    }));
  };

  return (
    <div className="min-h-screen bg-muted/40 p-4">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">{t('journalNew.title')}</h1>

        <form onSubmit={handleSubmit} className="rounded-lg border bg-card text-card-foreground shadow-sm p-6 space-y-6">
          {/* Basic Trade Information */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">{t('journalNew.tradeInfo')}</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">{t('journalNew.symbol')}</label>
                <Input
                  type="text"
                  required
                  placeholder={t('journalNew.symbolPlaceholder')}
                  value={formData.symbol}
                  onChange={e => setFormData(prev => ({ ...prev, symbol: e.target.value }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{t('journalNew.market')}</label>
                <Input
                  type="text"
                  placeholder={t('journalNew.marketPlaceholder')}
                  value={formData.market}
                  onChange={e => setFormData(prev => ({ ...prev, market: e.target.value }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{t('journalNew.direction')}</label>
                <select
                  value={formData.direction}
                  onChange={e => setFormData(prev => ({ ...prev, direction: e.target.value as TradeDirection }))}
                  className="w-full h-10 px-3 py-2 border border-input rounded-md bg-background text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                >
                  <option value={TradeDirection.LONG}>{t('journalNew.long')}</option>
                  <option value={TradeDirection.SHORT}>{t('journalNew.short')}</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">{t('journalNew.tradeDate')}</label>
              <Input
                type="datetime-local"
                value={formData.trade_date}
                onChange={e => setFormData(prev => ({ ...prev, trade_date: e.target.value }))}
              />
            </div>
          </div>

          {/* Entry/Exit Information */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">{t('journalNew.entryExit')}</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">{t('journalNew.entryPrice')}</label>
                <Input
                  type="number"
                  step="0.00001"
                  value={formData.entry_price || ''}
                  onChange={e => setFormData(prev => ({ ...prev, entry_price: parseFloat(e.target.value) || undefined }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{t('journalNew.positionSize')}</label>
                <Input
                  type="number"
                  step="0.00001"
                  value={formData.position_size || ''}
                  onChange={e => setFormData(prev => ({ ...prev, position_size: parseFloat(e.target.value) || undefined }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{t('journalNew.entryTime')}</label>
                <Input
                  type="datetime-local"
                  value={formData.entry_time}
                  onChange={e => setFormData(prev => ({ ...prev, entry_time: e.target.value }))}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">{t('journalNew.exitPrice')}</label>
                <Input
                  type="number"
                  step="0.00001"
                  value={formData.exit_price || ''}
                  onChange={e => setFormData(prev => ({ ...prev, exit_price: parseFloat(e.target.value) || undefined }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{t('journalNew.exitTime')}</label>
                <Input
                  type="datetime-local"
                  value={formData.exit_time}
                  onChange={e => setFormData(prev => ({ ...prev, exit_time: e.target.value }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{t('journalNew.result')}</label>
                <select
                  value={formData.result}
                  onChange={e => setFormData(prev => ({ ...prev, result: e.target.value as TradeResult }))}
                  className="w-full h-10 px-3 py-2 border border-input rounded-md bg-background text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                >
                  <option value={TradeResult.OPEN}>{t('journalNew.resultOpen')}</option>
                  <option value={TradeResult.WIN}>{t('journalNew.resultWin')}</option>
                  <option value={TradeResult.LOSS}>{t('journalNew.resultLoss')}</option>
                  <option value={TradeResult.BREAKEVEN}>{t('journalNew.resultBreakeven')}</option>
                </select>
              </div>
            </div>
          </div>

          {/* Risk Management */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">{t('journalNew.riskManagement')}</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">{t('journalNew.stopLoss')}</label>
                <Input
                  type="number"
                  step="0.00001"
                  value={formData.stop_loss || ''}
                  onChange={e => setFormData(prev => ({ ...prev, stop_loss: parseFloat(e.target.value) || undefined }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{t('journalNew.takeProfit')}</label>
                <Input
                  type="number"
                  step="0.00001"
                  value={formData.take_profit || ''}
                  onChange={e => setFormData(prev => ({ ...prev, take_profit: parseFloat(e.target.value) || undefined }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{t('journalNew.riskReward')}</label>
                <Input
                  type="number"
                  step="0.01"
                  value={formData.risk_reward_ratio || ''}
                  onChange={e => setFormData(prev => ({ ...prev, risk_reward_ratio: parseFloat(e.target.value) || undefined }))}
                />
              </div>
            </div>
          </div>

          {/* Psychology & Emotions */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">{t('journalNew.psychology')}</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">{t('journalNew.emotionBefore')}</label>
                <Input
                  type="number"
                  min="1"
                  max="5"
                  value={formData.emotion_before || ''}
                  onChange={e => setFormData(prev => ({ ...prev, emotion_before: parseInt(e.target.value) || undefined }))}
                  placeholder={t('journalNew.emotionScale')}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{t('journalNew.emotionDuring')}</label>
                <Input
                  type="number"
                  min="1"
                  max="5"
                  value={formData.emotion_during || ''}
                  onChange={e => setFormData(prev => ({ ...prev, emotion_during: parseInt(e.target.value) || undefined }))}
                  placeholder={t('journalNew.emotionScale')}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{t('journalNew.emotionAfter')}</label>
                <Input
                  type="number"
                  min="1"
                  max="5"
                  value={formData.emotion_after || ''}
                  onChange={e => setFormData(prev => ({ ...prev, emotion_after: parseInt(e.target.value) || undefined }))}
                  placeholder={t('journalNew.emotionScale')}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">{t('journalNew.confidence')}</label>
                <Input
                  type="number"
                  min="1"
                  max="5"
                  value={formData.confidence_level || ''}
                  onChange={e => setFormData(prev => ({ ...prev, confidence_level: parseInt(e.target.value) || undefined }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{t('journalNew.stress')}</label>
                <Input
                  type="number"
                  min="1"
                  max="5"
                  value={formData.stress_level || ''}
                  onChange={e => setFormData(prev => ({ ...prev, stress_level: parseInt(e.target.value) || undefined }))}
                />
              </div>
            </div>

            <div>
              <label className="flex items-center gap-2 text-sm font-medium mb-2">
                <Checkbox
                  checked={formData.followed_rules}
                  onCheckedChange={(checked) => setFormData(prev => ({
                    ...prev,
                    followed_rules: checked,
                    rule_violations: checked ? [] : prev.rule_violations
                  }))}
                />
                {t('journalNew.followedRules')}
              </label>

              {!formData.followed_rules && (
                <div className="mt-2 space-y-2">
                  <p className="text-sm text-muted-foreground">{t('journalNew.ruleViolationsLabel')}</p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    {Object.entries(ruleViolationKeys).map(([key, translationKey]) => (
                      <label key={key} className="flex items-center gap-2 text-sm">
                        <Checkbox
                          checked={formData.rule_violations.includes(key as RuleViolationType)}
                          onCheckedChange={() => handleRuleViolationChange(key as RuleViolationType)}
                        />
                        {t(translationKey as any)}
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Notes & Analysis */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">{t('journalNew.notesAnalysis')}</h2>

            <div>
              <label className="block text-sm font-medium mb-1">{t('journalNew.strategy')}</label>
              <Input
                type="text"
                value={formData.strategy_name}
                onChange={e => setFormData(prev => ({ ...prev, strategy_name: e.target.value }))}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">{t('journalNew.entryRationale')}</label>
              <Textarea
                rows={3}
                value={formData.setup_description}
                onChange={e => setFormData(prev => ({ ...prev, setup_description: e.target.value }))}
                placeholder={t('journalNew.entryRationalePlaceholder')}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">{t('journalNew.exitRationale')}</label>
              <Textarea
                rows={3}
                value={formData.exit_reason}
                onChange={e => setFormData(prev => ({ ...prev, exit_reason: e.target.value }))}
                placeholder={t('journalNew.exitRationalePlaceholder')}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">{t('journalNew.lessonsLearned')}</label>
              <Textarea
                rows={3}
                value={formData.lessons_learned}
                onChange={e => setFormData(prev => ({ ...prev, lessons_learned: e.target.value }))}
                placeholder={t('journalNew.lessonsPlaceholder')}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">{t('journalNew.otherNotes')}</label>
              <Textarea
                rows={4}
                value={formData.notes}
                onChange={e => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                placeholder={t('journalNew.otherNotesPlaceholder')}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">{t('journalNew.tags')}</label>
              <Input
                type="text"
                onKeyDown={handleTagInput}
                placeholder={t('journalNew.tagsPlaceholder')}
              />
              {formData.tags.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {formData.tags.map(tag => (
                    <span
                      key={tag}
                      className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800"
                    >
                      {tag}
                      <button
                        type="button"
                        onClick={() => removeTag(tag)}
                        className="ml-2 text-blue-600 hover:text-blue-800"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Error display */}
          {error && (
            <div className="p-4 bg-red-50 text-red-600 rounded-md">
              {error}
            </div>
          )}

          {/* Form actions */}
          <div className="flex gap-4 justify-end">
            <button
              type="button"
              onClick={() => router.push('/journal')}
              className="px-6 py-2 rounded-md border border-input bg-background hover:bg-accent hover:text-accent-foreground"
            >
              {t('journalNew.cancel')}
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {isSubmitting ? t('journalNew.saving') : t('journalNew.saveEntry')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
