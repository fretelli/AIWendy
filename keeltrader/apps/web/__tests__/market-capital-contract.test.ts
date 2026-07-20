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

test('capital route is exposed in API client and research desk', () => {
  expect(api).toContain('marketCapital')
  expect(api).toContain('/market-capital?window=')
  expect(desk).toContain('href="/agent/capital"')
})
