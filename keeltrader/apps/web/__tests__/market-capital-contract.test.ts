import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(__dirname, '..')
const page = fs.readFileSync(path.join(root, 'app/(app)/agent/capital/page.tsx'), 'utf8')
const api = fs.readFileSync(path.join(root, 'lib/api/agent-platform.ts'), 'utf8')
const desk = fs.readFileSync(path.join(root, 'app/(app)/agent/page.tsx'), 'utf8')

test('market capital page separates observable data from provider proxy', () => {
  expect(page).toContain('成交额不等于净流入')
  expect(page).toContain('供应商代理口径')
  expect(page).toContain('与可验证资金面隔离')
  expect(page).toContain('来源不可用')
  expect(page).not.toContain('综合评分')
  expect(page).not.toContain('仓位建议')
  expect(page).not.toContain('选股推荐')
})

test('market capital dashboard exposes interactive history and methodology', () => {
  expect(page).toContain('资金水位记录带')
  expect(page).toContain('数据口径中心')
  expect(page).toContain('<Brush')
  expect(page).toContain("type ChartMode = 'turnover' | 'breadth' | 'return'")
  expect(page).toContain('const WINDOWS = [20, 60, 120, 250] as const')
  expect(page).toContain('完整交易日与时间范围')
  expect(page).toContain('融资净额 = 融资买入额 − 融资偿还额')
  expect(page).toContain('不会以 0 或其他指标替代')
})

test('interactive chart is the first dashboard content, not hidden below the context block', () => {
  expect(page).toContain('data-chart-priority="primary"')
  expect(page.indexOf('<MarketTape')).toBeLessThan(page.indexOf('<MarketContext'))
})

test('market chart uses measured dimensions instead of the incompatible responsive wrapper', () => {
  expect(page).toContain('data-chart-canvas="market-capital"')
  expect(page).toContain('new ResizeObserver(measure)')
  expect(page).toContain('width={chartSize.width}')
  expect(page).toContain('height={chartSize.height}')
  expect(page).not.toContain('<ResponsiveContainer')
})

test('capital route is exposed in API client and research desk', () => {
  expect(api).toContain('marketCapital')
  expect(api).toContain('/market-capital?window=')
  expect(desk).toContain('href="/agent/capital"')
})
