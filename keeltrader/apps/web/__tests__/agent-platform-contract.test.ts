import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(__dirname, '..')

describe('Agent Platform contract', () => {
  it('uses the unified agent route without a standalone research hub', () => {
    const layout = fs.readFileSync(path.join(root, 'app/(app)/layout.tsx'), 'utf8')
    expect(layout).toContain("href: '/agent'")
    expect(layout).not.toContain("href: '/research'")
    expect(layout).not.toContain("href: '/chat'")
    expect(layout).not.toContain("href: '/settings'")
    expect(fs.existsSync(path.join(root, 'app/(app)/settings/page.tsx'))).toBe(false)
  })

  it('uses a conversation-first workspace instead of the legacy tab console', () => {
    const page = fs.readFileSync(path.join(root, 'app/(app)/agent/page.tsx'), 'utf8')
    expect(page).toContain('新会话')
    expect(page).toContain('EventSource')
    expect(page).toContain("'/compact'")
    expect(page).toContain('需要你的批准')
    expect(page).toContain("'/ask'")
    expect(page).toContain("'/research'")
    expect(page).toContain("'/plan'")
    expect(page).toContain('PanelResizeHandle')
    expect(page).toContain('autoSaveId="keeltrader-agent-workspace"')
    expect(page).not.toContain('<select value={mode}')
    expect(page).not.toContain('连续追问、调用 report-kb 和 Tushare')
    expect(page).not.toContain('[Ask mode:')
    expect(page).not.toContain('<Tabs')
  })

  it('does not expose trade execution controls in the Agent workspace', () => {
    const page = fs.readFileSync(path.join(root, 'app/(app)/agent/page.tsx'), 'utf8')
    expect(page).not.toContain('place_order')
    expect(page).not.toContain('cancel_order')
    expect(page).not.toContain('execute_trade')
  })
})
