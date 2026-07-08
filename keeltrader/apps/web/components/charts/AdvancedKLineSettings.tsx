'use client'

import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'

import type { TechnicalIndicator } from './advanced-kline-config'

interface AdvancedKLineSettingsProps {
  indicators: TechnicalIndicator[]
  onToggleIndicator: (indicatorName: string) => void
  showGrid: boolean
  onShowGridChange: (value: boolean) => void
  showCrosshair: boolean
  onShowCrosshairChange: (value: boolean) => void
  darkMode: boolean
  onDarkModeChange: (value: boolean) => void
}

export function AdvancedKLineSettings({
  indicators,
  onToggleIndicator,
  showGrid,
  onShowGridChange,
  showCrosshair,
  onShowCrosshairChange,
  darkMode,
  onDarkModeChange,
}: AdvancedKLineSettingsProps) {
  return (
    <div className="mt-6 space-y-6">
      <div>
        <h3 className="mb-4 font-medium">Technical Indicators</h3>
        <div className="space-y-3">
          {indicators.map(indicator => (
            <div key={indicator.name} className="flex items-center justify-between">
              <Label htmlFor={indicator.name} className="font-normal">
                {indicator.name}
              </Label>
              <Switch
                id={indicator.name}
                checked={indicator.enabled}
                onCheckedChange={() => onToggleIndicator(indicator.name)}
              />
            </div>
          ))}
        </div>
      </div>

      <Separator />

      <div>
        <h3 className="mb-4 font-medium">Appearance</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label htmlFor="grid" className="font-normal">Show Grid</Label>
            <Switch
              id="grid"
              checked={showGrid}
              onCheckedChange={onShowGridChange}
            />
          </div>
          <div className="flex items-center justify-between">
            <Label htmlFor="crosshair" className="font-normal">Show Crosshair</Label>
            <Switch
              id="crosshair"
              checked={showCrosshair}
              onCheckedChange={onShowCrosshairChange}
            />
          </div>
          <div className="flex items-center justify-between">
            <Label htmlFor="dark" className="font-normal">Dark Mode</Label>
            <Switch
              id="dark"
              checked={darkMode}
              onCheckedChange={onDarkModeChange}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
