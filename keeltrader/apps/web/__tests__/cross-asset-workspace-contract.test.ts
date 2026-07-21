import fs from 'fs'
import path from 'path'

const root = path.resolve(__dirname, '..')

test('cross-asset routes preserve evidence-first and human-only product contract', () => {
  const rates = fs.readFileSync(path.join(root, 'app/(app)/agent/market/rates/page.tsx'), 'utf8')
  const opportunities = fs.readFileSync(path.join(root, 'app/(app)/agent/market/opportunities/page.tsx'), 'utf8')
  const options = fs.readFileSync(path.join(root, 'app/(app)/agent/capital/options/page.tsx'), 'utf8')
  const config = fs.readFileSync(path.join(root, 'next.config.js'), 'utf8')
  expect(rates).toContain('中国现券国债收益率曲线未接入')
  expect(rates).toContain('PanelResizeHandle')
  expect(opportunities).toContain('全部观察 · 不评分')
  expect(opportunities).toContain('待人工确认，未连接券商执行')
  expect(options).toContain('Black–76')
  expect(options).toContain('Gross OI-weighted sensitivity')
  expect(config).toContain("destination: '/agent/market/options'")
  expect(config).toContain('permanent: true')
})
