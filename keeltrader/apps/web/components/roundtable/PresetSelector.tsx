"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { CoachPreset } from "@/lib/types/roundtable"
import { PRESET_ICONS } from "@/lib/types/roundtable"
import { useI18n } from "@/lib/i18n/provider"

interface PresetSelectorProps {
  presets: CoachPreset[]
  selectedPresetId?: string | null
  onSelect: (preset: CoachPreset) => void
  className?: string
}

export function PresetSelector({
  presets,
  selectedPresetId,
  onSelect,
  className,
}: PresetSelectorProps) {
  const { locale } = useI18n()
  const isZh = locale === "zh"
  return (
    <div className={cn("grid gap-4 md:grid-cols-2 lg:grid-cols-3", className)}>
      {presets.map((preset) => {
        const isSelected = selectedPresetId === preset.id
        const icon = PRESET_ICONS[preset.icon || ''] || '🎯'

        return (
          <Card
            key={preset.id}
            className={cn(
              "cursor-pointer transition-all hover:border-primary/50 hover:shadow-md",
              isSelected && "border-primary bg-primary/5 shadow-md"
            )}
            onClick={() => onSelect(preset)}
          >
            <CardHeader className="pb-3">
              <div className="flex items-center gap-3">
                <span className="text-2xl">{icon}</span>
                <div className="flex-1">
                  <CardTitle className="text-lg">{preset.name}</CardTitle>
                  <Badge variant="secondary" className="mt-1">
                    {isZh ? `${preset.coach_ids.length} 位教练` : `${preset.coach_ids.length} coaches`}
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <CardDescription className="line-clamp-2">
                {preset.description}
              </CardDescription>

              {/* Coach avatars */}
              <div className="flex items-center gap-1">
                <div className="flex -space-x-2">
                  {preset.coaches?.slice(0, 5).map((coach) => (
                    <Avatar
                      key={coach.id}
                      className="h-8 w-8 border-2 border-background"
                    >
                      <AvatarImage src={coach.avatar_url} alt={coach.name} />
                      <AvatarFallback className="text-xs">
                        {coach.name.charAt(0)}
                      </AvatarFallback>
                    </Avatar>
                  ))}
                </div>
                <span className="text-xs text-muted-foreground ml-2">
                  {preset.coaches?.map((c) => c.name).join(", ")}
                </span>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
