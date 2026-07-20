import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(__dirname, '..')
const page = fs.readFileSync(path.join(root, 'app/(app)/agent/holders/page.tsx'), 'utf8')
const api = fs.readFileSync(path.join(root, 'lib/api/agent-platform.ts'), 'utf8')

test('holder radar is a query workspace without scoring or recommendations', () => {
  expect(page).toContain('股东雷达')
  expect(page).toContain('不评分，不推荐')
  expect(page).toContain('当前持仓')
  expect(page).toContain('历史变化')
  expect(page).not.toContain('Sourcing')
  expect(page).not.toContain('综合评分')
})

test('holder radar shares the resizable workspace behavior', () => {
  expect(page).toContain('PanelResizeHandle')
  expect(page).toContain('autoSaveId="keeltrader-holder-radar-workspace"')
  expect(page).toContain('collapsible collapsedSize={0}')
  expect(page).toContain('打开关注股东')
  expect(page).toContain('打开披露变化')
  expect(page).not.toContain('xl:grid-cols-[290px_minmax(0,1fr)_330px]')
})

test('holder API client exposes search, watchlist, positions and inbox', () => {
  expect(api).toContain('searchHolders')
  expect(api).toContain('holderWatchlist')
  expect(api).toContain('holderPositions')
  expect(api).toContain('holderEvents')
})

test('historical holder events show restrained price-window estimates without claiming exact trades', () => {
  expect(api).toContain('HolderPriceEstimate')
  expect(api).toContain("side: 'buy' | 'sell' | 'possible_sell'")
  expect(page).toContain('披露区间估算')
  expect(page).toContain('可能卖出价格窗口')
  expect(page).toContain('无法可靠估算成交价格')
  expect(page).toContain('前复权收盘价成交量加权')
  expect(page).not.toContain('实际买入价')
  expect(page).not.toContain('实际卖出价')
})
