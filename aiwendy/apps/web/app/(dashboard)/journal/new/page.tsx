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
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

const ruleViolationLabels: Record<RuleViolationType, string> = {
  [RuleViolationType.EARLY_EXIT]: '提前止盈',
  [RuleViolationType.LATE_EXIT]: '晚止损',
  [RuleViolationType.NO_STOP_LOSS]: '没有止损',
  [RuleViolationType.OVER_LEVERAGE]: '过度杠杆',
  [RuleViolationType.REVENGE_TRADE]: '报复性交易',
  [RuleViolationType.FOMO]: '追涨杀跌',
  [RuleViolationType.POSITION_SIZE]: '仓位过大',
  [RuleViolationType.OTHER]: '其他'
};

export default function NewJournalEntry() {
  const router = useRouter();
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
      setError(err instanceof Error ? err.message : '创建日记失败');
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
        <h1 className="text-2xl font-bold mb-6">新建交易日记</h1>

        <form onSubmit={handleSubmit} className="rounded-lg border bg-card text-card-foreground shadow-sm p-6 space-y-6">
          {/* Basic Trade Information */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">交易信息</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">交易标的 *</label>
                <Input
                  type="text"
                  required
                  placeholder="如: AAPL, BTCUSDT"
                  value={formData.symbol}
                  onChange={e => setFormData(prev => ({ ...prev, symbol: e.target.value }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">市场</label>
                <Input
                  type="text"
                  placeholder="如: stocks, crypto"
                  value={formData.market}
                  onChange={e => setFormData(prev => ({ ...prev, market: e.target.value }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">方向 *</label>
                <select
                  value={formData.direction}
                  onChange={e => setFormData(prev => ({ ...prev, direction: e.target.value as TradeDirection }))}
                  className="w-full h-10 px-3 py-2 border border-input rounded-md bg-background text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                >
                  <option value={TradeDirection.LONG}>做多</option>
                  <option value={TradeDirection.SHORT}>做空</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">交易日期</label>
              <Input
                type="datetime-local"
                value={formData.trade_date}
                onChange={e => setFormData(prev => ({ ...prev, trade_date: e.target.value }))}
              />
            </div>
          </div>

          {/* Entry/Exit Information */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">入场/出场</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">入场价格</label>
                <Input
                  type="number"
                  step="0.00001"
                  value={formData.entry_price || ''}
                  onChange={e => setFormData(prev => ({ ...prev, entry_price: parseFloat(e.target.value) || undefined }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">仓位大小</label>
                <Input
                  type="number"
                  step="0.00001"
                  value={formData.position_size || ''}
                  onChange={e => setFormData(prev => ({ ...prev, position_size: parseFloat(e.target.value) || undefined }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">入场时间</label>
                <Input
                  type="datetime-local"
                  value={formData.entry_time}
                  onChange={e => setFormData(prev => ({ ...prev, entry_time: e.target.value }))}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">出场价格</label>
                <Input
                  type="number"
                  step="0.00001"
                  value={formData.exit_price || ''}
                  onChange={e => setFormData(prev => ({ ...prev, exit_price: parseFloat(e.target.value) || undefined }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">出场时间</label>
                <Input
                  type="datetime-local"
                  value={formData.exit_time}
                  onChange={e => setFormData(prev => ({ ...prev, exit_time: e.target.value }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">交易结果</label>
                <select
                  value={formData.result}
                  onChange={e => setFormData(prev => ({ ...prev, result: e.target.value as TradeResult }))}
                  className="w-full h-10 px-3 py-2 border border-input rounded-md bg-background text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                >
                  <option value={TradeResult.OPEN}>进行中</option>
                  <option value={TradeResult.WIN}>盈利</option>
                  <option value={TradeResult.LOSS}>亏损</option>
                  <option value={TradeResult.BREAKEVEN}>平局</option>
                </select>
              </div>
            </div>
          </div>

          {/* Risk Management */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">风险管理</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">止损价</label>
                <Input
                  type="number"
                  step="0.00001"
                  value={formData.stop_loss || ''}
                  onChange={e => setFormData(prev => ({ ...prev, stop_loss: parseFloat(e.target.value) || undefined }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">止盈价</label>
                <Input
                  type="number"
                  step="0.00001"
                  value={formData.take_profit || ''}
                  onChange={e => setFormData(prev => ({ ...prev, take_profit: parseFloat(e.target.value) || undefined }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">风险回报比</label>
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
            <h2 className="text-lg font-semibold">心理与情绪</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">交易前情绪 (1-5)</label>
                <Input
                  type="number"
                  min="1"
                  max="5"
                  value={formData.emotion_before || ''}
                  onChange={e => setFormData(prev => ({ ...prev, emotion_before: parseInt(e.target.value) || undefined }))}
                  placeholder="1=焦虑, 5=平静"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">交易中情绪 (1-5)</label>
                <Input
                  type="number"
                  min="1"
                  max="5"
                  value={formData.emotion_during || ''}
                  onChange={e => setFormData(prev => ({ ...prev, emotion_during: parseInt(e.target.value) || undefined }))}
                  placeholder="1=焦虑, 5=平静"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">交易后情绪 (1-5)</label>
                <Input
                  type="number"
                  min="1"
                  max="5"
                  value={formData.emotion_after || ''}
                  onChange={e => setFormData(prev => ({ ...prev, emotion_after: parseInt(e.target.value) || undefined }))}
                  placeholder="1=焦虑, 5=平静"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">信心水平 (1-5)</label>
                <Input
                  type="number"
                  min="1"
                  max="5"
                  value={formData.confidence_level || ''}
                  onChange={e => setFormData(prev => ({ ...prev, confidence_level: parseInt(e.target.value) || undefined }))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">压力水平 (1-5)</label>
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
                遵守了交易规则
              </label>

              {!formData.followed_rules && (
                <div className="mt-2 space-y-2">
                  <p className="text-sm text-muted-foreground">违反的规则：</p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    {Object.entries(ruleViolationLabels).map(([key, label]) => (
                      <label key={key} className="flex items-center gap-2 text-sm">
                        <Checkbox
                          checked={formData.rule_violations.includes(key as RuleViolationType)}
                          onCheckedChange={() => handleRuleViolationChange(key as RuleViolationType)}
                        />
                        {label}
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Notes & Analysis */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">笔记与分析</h2>

            <div>
              <label className="block text-sm font-medium mb-1">策略名称</label>
              <Input
                type="text"
                value={formData.strategy_name}
                onChange={e => setFormData(prev => ({ ...prev, strategy_name: e.target.value }))}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">入场理由</label>
              <Textarea
                rows={3}
                value={formData.setup_description}
                onChange={e => setFormData(prev => ({ ...prev, setup_description: e.target.value }))}
                placeholder="描述为什么要进入这个交易..."
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">出场理由</label>
              <Textarea
                rows={3}
                value={formData.exit_reason}
                onChange={e => setFormData(prev => ({ ...prev, exit_reason: e.target.value }))}
                placeholder="描述为什么要退出这个交易..."
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">经验教训</label>
              <Textarea
                rows={3}
                value={formData.lessons_learned}
                onChange={e => setFormData(prev => ({ ...prev, lessons_learned: e.target.value }))}
                placeholder="这次交易学到了什么..."
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">其他笔记</label>
              <Textarea
                rows={4}
                value={formData.notes}
                onChange={e => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                placeholder="任何其他想要记录的内容..."
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">标签</label>
              <Input
                type="text"
                onKeyDown={handleTagInput}
                placeholder="输入标签后按回车或逗号添加"
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
              取消
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {isSubmitting ? '保存中...' : '保存日记'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
