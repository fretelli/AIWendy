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

test('holder API client exposes search, watchlist, positions and inbox', () => {
  expect(api).toContain('searchHolders')
  expect(api).toContain('holderWatchlist')
  expect(api).toContain('holderPositions')
  expect(api).toContain('holderEvents')
})
