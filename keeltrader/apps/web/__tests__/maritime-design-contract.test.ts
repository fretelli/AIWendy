import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(__dirname, '..')

describe('maritime research workspace design', () => {
  it('defines the chart-room palette, typography, and reduced-motion treatment', () => {
    const css = fs.readFileSync(path.join(root, 'app/globals.css'), 'utf8')
    const layout = fs.readFileSync(path.join(root, 'app/layout.tsx'), 'utf8')
    expect(css).toContain('--copper:')
    expect(css).toContain('--deep-sounding:')
    expect(css).toContain('.research-bearing')
    expect(css).toContain('prefers-reduced-motion')
    expect(layout).toContain('Newsreader')
    expect(layout).toContain('IBM_Plex_Mono')
  })

  it('keeps one functional header and exposes theme and research state controls', () => {
    const appLayout = fs.readFileSync(path.join(root, 'app/(app)/layout.tsx'), 'utf8')
    const page = fs.readFileSync(path.join(root, 'app/(app)/agent/page.tsx'), 'utf8')
    expect(appLayout).not.toContain('<header')
    expect(page).toContain('ResearchBearing')
    expect(page).toContain('ThemeMenu')
    expect(page).toContain('只读，不执行交易')
    expect(page).toContain('PanelResizeHandle')
  })

  it('uses the unified private-research auth shell on every account entry page', () => {
    for (const route of ['login', 'register', 'forgot-password', 'reset-password']) {
      const page = fs.readFileSync(path.join(root, `app/auth/${route}/page.tsx`), 'utf8')
      expect(page).toContain('AuthShell')
    }
    const shell = fs.readFileSync(path.join(root, 'components/auth-shell.tsx'), 'utf8')
    expect(shell).toContain('只读基本面研究，不执行交易')
    expect(shell).toContain('私有部署自行 BYOK')
  })
})
