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

const ruleViolationLabels: Record<RuleViolationType, { zh: string; en: string }> = {
  [RuleViolationType.EARLY_EXIT]: { zh: '提前止盈', en: 'Take profit early' },
  [RuleViolationType.LATE_EXIT]: { zh: '晚止损', en: 'Stop loss too late' },
  [RuleViolationType.NO_STOP_LOSS]: { zh: '没有止损', en: 'No stop loss' },
  [RuleViolationType.OVER_LEVERAGE]: { zh: '过度杠杆', en: 'Over leverage' },
  [RuleViolationType.REVENGE_TRADE]: { zh: '报复性交易', en: 'Revenge trading' },
  [RuleViolationType.FOMO]: { zh: '追涨杀跌', en: 'Chasing / panic selling' },
  [RuleViolationType.POSITION_SIZE]: { zh: '仓位过大', en: 'Position too large' },
  [RuleViolationType.OTHER]: { zh: '其他', en: 'Other' },
};

export default function NewJournalEntry() {
  const router = useRouter();
  const { locale } = useI18n();
  const isZh = locale === 'zh';
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
      setError(err instanceof Error ? err.message : (isZh ? '创建日记失败' : 'Failed to create journal entry'));
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
        <h1 className="text-2xl font-bold mb-6">{isZh ? '新建交易日记' : 'New Journal Entry'}</h1>

        <form onSubmit={handleSubmit} className="rounded-lg border bg-card text-card-foreground shadow-sm p-6 space-y-6">
          {/* Basic Trade Information */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">{isZh ? '交易信息' : 'Trade Info'}</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">{isZh ? '交易标的 *' : 'Symbol *'}</label>
                <Input
                  type="text"
                  required
                  placeholder={isZh ? '如: AAPL, BTCUSDT' : 'e.g. AAPL, BTCUSDT'}
                  value={formData.symbol}
                  onChange={e => setFormData(prev => ({ ...prev, symbol: e.target.value }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{isZh ? '市场' : 'Market'}</label>
                <Input
                  type="text"
                  placeholder={isZh ? '如: stocks, crypto' : 'e.g. stocks, crypto'}
                  value={formData.market}
                  onChange={e => setFormData(prev => ({ ...prev, market: e.target.value }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{isZh ? '方向 *' : 'Direction *'}</label>
                <select
                  value={formData.direction}
                  onChange={e => setFormData(prev => ({ ...prev, direction: e.target.value as TradeDirection }))}
                  className="w-full h-10 px-3 py-2 border border-input rounded-md bg-background text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                >
                  <option value={TradeDirection.LONG}>{isZh ? '做多' : 'Long'}</option>
                  <option value={TradeDirection.SHORT}>{isZh ? '做空' : 'Short'}</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">{isZh ? '交易日期' : 'Trade Date'}</label>
              <Input
                type="datetime-local"
                value={formData.trade_date}
                onChange={e => setFormData(prev => ({ ...prev, trade_date: e.target.value }))}
              />
            </div>
          </div>

          {/* Entry/Exit Information */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">{isZh ? '入场/出场' : 'Entry / Exit'}</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">{isZh ? '入场价格' : 'Entry Price'}</label>
                <Input
                  type="number"
                  step="0.00001"
                  value={formData.entry_price || ''}
                  onChange={e => setFormData(prev => ({ ...prev, entry_price: parseFloat(e.target.value) || undefined }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{isZh ? '仓位大小' : 'Position Size'}</label>
                <Input
                  type="number"
                  step="0.00001"
                  value={formData.position_size || ''}
                  onChange={e => setFormData(prev => ({ ...prev, position_size: parseFloat(e.target.value) || undefined }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{isZh ? '入场时间' : 'Entry Time'}</label>
                <Input
                  type="datetime-local"
                  value={formData.entry_time}
                  onChange={e => setFormData(prev => ({ ...prev, entry_time: e.target.value }))}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">{isZh ? '出场价格' : 'Exit Price'}</label>
                <Input
                  type="number"
                  step="0.00001"
                  value={formData.exit_price || ''}
                  onChange={e => setFormData(prev => ({ ...prev, exit_price: parseFloat(e.target.value) || undefined }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{isZh ? '出场时间' : 'Exit Time'}</label>
                <Input
                  type="datetime-local"
                  value={formData.exit_time}
                  onChange={e => setFormData(prev => ({ ...prev, exit_time: e.target.value }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{isZh ? '交易结果' : 'Result'}</label>
                <select
                  value={formData.result}
                  onChange={e => setFormData(prev => ({ ...prev, result: e.target.value as TradeResult }))}
                  className="w-full h-10 px-3 py-2 border border-input rounded-md bg-background text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                >
                  <option value={TradeResult.OPEN}>{isZh ? '进行中' : 'Open'}</option>
                  <option value={TradeResult.WIN}>{isZh ? '盈利' : 'Win'}</option>
                  <option value={TradeResult.LOSS}>{isZh ? '亏损' : 'Loss'}</option>
                  <option value={TradeResult.BREAKEVEN}>{isZh ? '平局' : 'Breakeven'}</option>
                </select>
              </div>
            </div>
          </div>

          {/* Risk Management */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">{isZh ? '风险管理' : 'Risk Management'}</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">{isZh ? '止损价' : 'Stop Loss'}</label>
                <Input
                  type="number"
                  step="0.00001"
                  value={formData.stop_loss || ''}
                  onChange={e => setFormData(prev => ({ ...prev, stop_loss: parseFloat(e.target.value) || undefined }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{isZh ? '止盈价' : 'Take Profit'}</label>
                <Input
                  type="number"
                  step="0.00001"
                  value={formData.take_profit || ''}
                  onChange={e => setFormData(prev => ({ ...prev, take_profit: parseFloat(e.target.value) || undefined }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{isZh ? '风险回报比' : 'Risk/Reward'}</label>
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
            <h2 className="text-lg font-semibold">{isZh ? '心理与情绪' : 'Psychology & Emotions'}</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">{isZh ? '交易前情绪 (1-5)' : 'Emotion Before (1-5)'}</label>
                <Input
                  type="number"
                  min="1"
                  max="5"
                  value={formData.emotion_before || ''}
                  onChange={e => setFormData(prev => ({ ...prev, emotion_before: parseInt(e.target.value) || undefined }))}
                  placeholder={isZh ? '1=焦虑, 5=平静' : '1=Anxious, 5=Calm'}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{isZh ? '交易中情绪 (1-5)' : 'Emotion During (1-5)'}</label>
                <Input
                  type="number"
                  min="1"
                  max="5"
                  value={formData.emotion_during || ''}
                  onChange={e => setFormData(prev => ({ ...prev, emotion_during: parseInt(e.target.value) || undefined }))}
                  placeholder={isZh ? '1=焦虑, 5=平静' : '1=Anxious, 5=Calm'}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{isZh ? '交易后情绪 (1-5)' : 'Emotion After (1-5)'}</label>
                <Input
                  type="number"
                  min="1"
                  max="5"
                  value={formData.emotion_after || ''}
                  onChange={e => setFormData(prev => ({ ...prev, emotion_after: parseInt(e.target.value) || undefined }))}
                  placeholder={isZh ? '1=焦虑, 5=平静' : '1=Anxious, 5=Calm'}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">{isZh ? '信心水平 (1-5)' : 'Confidence (1-5)'}</label>
                <Input
                  type="number"
                  min="1"
                  max="5"
                  value={formData.confidence_level || ''}
                  onChange={e => setFormData(prev => ({ ...prev, confidence_level: parseInt(e.target.value) || undefined }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{isZh ? '压力水平 (1-5)' : 'Stress (1-5)'}</label>
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
                {isZh ? '遵守了交易规则' : 'Followed trading rules'}
              </label>

              {!formData.followed_rules && (
                <div className="mt-2 space-y-2">
                  <p className="text-sm text-muted-foreground">{isZh ? '违反的规则：' : 'Rule violations:'}</p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    {Object.entries(ruleViolationLabels).map(([key, label]) => (
                      <label key={key} className="flex items-center gap-2 text-sm">
                        <Checkbox
                          checked={formData.rule_violations.includes(key as RuleViolationType)}
                          onCheckedChange={() => handleRuleViolationChange(key as RuleViolationType)}
                        />
                        {isZh ? label.zh : label.en}
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Notes & Analysis */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">{isZh ? '笔记与分析' : 'Notes & Analysis'}</h2>

            <div>
              <label className="block text-sm font-medium mb-1">{isZh ? '策略名称' : 'Strategy'}</label>
              <Input
                type="text"
                value={formData.strategy_name}
                onChange={e => setFormData(prev => ({ ...prev, strategy_name: e.target.value }))}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">{isZh ? '入场理由' : 'Entry Rationale'}</label>
              <Textarea
                rows={3}
                value={formData.setup_description}
                onChange={e => setFormData(prev => ({ ...prev, setup_description: e.target.value }))}
                placeholder={isZh ? '描述为什么要进入这个交易...' : 'Why did you enter this trade...?'}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">{isZh ? '出场理由' : 'Exit Rationale'}</label>
              <Textarea
                rows={3}
                value={formData.exit_reason}
                onChange={e => setFormData(prev => ({ ...prev, exit_reason: e.target.value }))}
                placeholder={isZh ? '描述为什么要退出这个交易...' : 'Why did you exit this trade...?'}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">{isZh ? '经验教训' : 'Lessons Learned'}</label>
              <Textarea
                rows={3}
                value={formData.lessons_learned}
                onChange={e => setFormData(prev => ({ ...prev, lessons_learned: e.target.value }))}
                placeholder={isZh ? '这次交易学到了什么...' : 'What did you learn from this trade...?'}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">{isZh ? '其他笔记' : 'Notes'}</label>
              <Textarea
                rows={4}
                value={formData.notes}
                onChange={e => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                placeholder={isZh ? '任何其他想要记录的内容...' : 'Anything else you want to record...'}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">{isZh ? '标签' : 'Tags'}</label>
              <Input
                type="text"
                onKeyDown={handleTagInput}
                placeholder={isZh ? '输入标签后按回车或逗号添加' : 'Type a tag and press Enter or comma to add'}
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
              {isZh ? '取消' : 'Cancel'}
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {isSubmitting ? (isZh ? '保存中...' : 'Saving...') : (isZh ? '保存日记' : 'Save entry')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
