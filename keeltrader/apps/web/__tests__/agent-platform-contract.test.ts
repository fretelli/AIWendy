import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(__dirname, '..')

describe('Agent Platform contract', () => {
  it('uses the unified agent route without a standalone research hub', () => {
    const layout = fs.readFileSync(path.join(root, 'app/(app)/layout.tsx'), 'utf8')
    expect(layout).toContain("href: '/agent'")
    expect(layout).not.toContain("href: '/research'")
    expect(layout).not.toContain("href: '/chat'")
  })

  it('does not expose trade execution controls in the Agent workspace', () => {
    const page = fs.readFileSync(path.join(root, 'app/(app)/agent/page.tsx'), 'utf8')
    expect(page).not.toContain('place_order')
    expect(page).not.toContain('cancel_order')
    expect(page).not.toContain('execute_trade')
  })
})
