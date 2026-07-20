import fs from 'node:fs'
import path from 'node:path'

const webRoot = path.resolve(__dirname, '..')

test('web release never rebuilds or recreates API dependencies', () => {
  const releaseScript = fs.readFileSync(
    path.resolve(webRoot, '../../scripts/release-web-overlay.sh'),
    'utf8'
  )

  expect(releaseScript).toContain('docker compose up -d --no-deps web')
  expect(releaseScript).not.toContain('docker compose up -d web')
})
