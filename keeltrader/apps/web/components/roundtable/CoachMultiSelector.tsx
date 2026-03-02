"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { cn } from "@/lib/utils"
import type { Coach } from "@/lib/api/coaches"
import { useI18n } from "@/lib/i18n/provider"

interface CoachMultiSelectorProps {
  coaches: Coach[]
  selectedIds: string[]
  onSelectionChange: (ids: string[]) => void
  minCount?: number
  maxCount?: number
  className?: string
}

export function CoachMultiSelector({
  coaches,
  selectedIds,
  onSelectionChange,
  minCount = 2,
  maxCount = 5,
  className,
}: CoachMultiSelectorProps) {
  const { t } = useI18n()
  const handleToggle = (coachId: string) => {
    if (selectedIds.includes(coachId)) {
      // Remove if already selected
      onSelectionChange(selectedIds.filter((id) => id !== coachId))
    } else {
      // Add if under max limit
      if (selectedIds.length < maxCount) {
        onSelectionChange([...selectedIds, coachId])
      }
    }
  }

  const isValid = selectedIds.length >= minCount && selectedIds.length <= maxCount

  return (
    <div className={cn("space-y-4", className)}>
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {t('roundtable.selectCoaches', { min: minCount, max: maxCount })}
        </p>
        <Badge variant={isValid ? "default" : "secondary"}>
          {t('roundtable.selected')} {selectedIds.length}/{maxCount}
        </Badge>
      </div>

      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {coaches.map((coach) => {
          const isSelected = selectedIds.includes(coach.id)
          const isDisabled = !isSelected && selectedIds.length >= maxCount

          return (
            <Card
              key={coach.id}
              className={cn(
                "cursor-pointer transition-all",
                isSelected && "border-primary bg-primary/5",
                isDisabled && "opacity-50 cursor-not-allowed",
                !isDisabled && "hover:border-primary/50"
              )}
              onClick={() => !isDisabled && handleToggle(coach.id)}
            >
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <Checkbox
                    checked={isSelected}
                    disabled={isDisabled}
                    className="mt-1"
                    onClick={(e) => e.stopPropagation()}
                    onCheckedChange={() => handleToggle(coach.id)}
                  />
                  <Avatar className="h-10 w-10">
                    <AvatarImage src={coach.avatar_url} alt={coach.name} />
                    <AvatarFallback>{coach.name.charAt(0)}</AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-sm font-medium">
                      {coach.name}
                    </CardTitle>
                    <Badge variant="outline" className="mt-1 text-xs">
                      {t(`coaches.coachStyles.${coach.style}` as any)}
                    </Badge>
                    <CardDescription className="text-xs mt-1 line-clamp-2">
                      {coach.description}
                    </CardDescription>
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {!isValid && selectedIds.length > 0 && (
        <p className="text-sm text-destructive">
          {t('roundtable.selectMinCoaches', { min: minCount })}
        </p>
      )}
    </div>
  )
}
