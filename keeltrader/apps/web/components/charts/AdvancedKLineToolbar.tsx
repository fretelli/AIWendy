'use client'

import { Download, RotateCcw, Settings, ZoomIn, ZoomOut } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'

import {
  ADVANCED_KLINE_INTERVALS,
  type AdvancedKLineInterval,
  type TechnicalIndicator,
} from './advanced-kline-config'
import { AdvancedKLineSettings } from './AdvancedKLineSettings'

interface AdvancedKLineToolbarProps {
  interval: AdvancedKLineInterval
  onIntervalChange: (interval: AdvancedKLineInterval) => void
  onZoomIn: () => void
  onZoomOut: () => void
  onReset: () => void
  onExport: () => void
  indicators: TechnicalIndicator[]
  onToggleIndicator: (indicatorName: string) => void
  showGrid: boolean
  onShowGridChange: (value: boolean) => void
  showCrosshair: boolean
  onShowCrosshairChange: (value: boolean) => void
  darkMode: boolean
  onDarkModeChange: (value: boolean) => void
}

export function AdvancedKLineToolbar({
  interval,
  onIntervalChange,
  onZoomIn,
  onZoomOut,
  onReset,
  onExport,
  indicators,
  onToggleIndicator,
  showGrid,
  onShowGridChange,
  showCrosshair,
  onShowCrosshairChange,
  darkMode,
  onDarkModeChange,
}: AdvancedKLineToolbarProps) {
  return (
    <div className="flex items-center gap-2">
      <Select
        value={interval}
        onValueChange={(value) => onIntervalChange(value as AdvancedKLineInterval)}
      >
        <SelectTrigger className="w-[100px]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {ADVANCED_KLINE_INTERVALS.map(value => (
            <SelectItem key={value} value={value}>
              {value}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <div className="flex gap-1">
        <Button variant="ghost" size="icon" onClick={onZoomIn}>
          <ZoomIn className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" onClick={onZoomOut}>
          <ZoomOut className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" onClick={onReset}>
          <RotateCcw className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" onClick={onExport}>
          <Download className="h-4 w-4" />
        </Button>
      </div>

      <Sheet>
        <SheetTrigger asChild>
          <Button variant="outline" size="icon">
            <Settings className="h-4 w-4" />
          </Button>
        </SheetTrigger>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Chart Settings</SheetTitle>
            <SheetDescription>
              Customize indicators and appearance
            </SheetDescription>
          </SheetHeader>

          <AdvancedKLineSettings
            indicators={indicators}
            onToggleIndicator={onToggleIndicator}
            showGrid={showGrid}
            onShowGridChange={onShowGridChange}
            showCrosshair={showCrosshair}
            onShowCrosshairChange={onShowCrosshairChange}
            darkMode={darkMode}
            onDarkModeChange={onDarkModeChange}
          />
        </SheetContent>
      </Sheet>
    </div>
  )
}
