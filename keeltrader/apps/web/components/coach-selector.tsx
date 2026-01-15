"use client"

import { useEffect, useState } from "react"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Brain, Heart, Trophy, BarChart3, Zap, HelpCircle } from "lucide-react"
import { toast } from "sonner"
import { API_V1_PREFIX } from "@/lib/config"
import { useI18n } from "@/lib/i18n/provider"

interface Coach {
  id: string
  name: string
  avatar_url?: string
  description?: string
  style: string
  is_premium: boolean
}

interface CoachSelectorProps {
  selectedCoachId?: string
  onCoachChange: (coachId: string) => void
  className?: string
}

const styleIcons: Record<string, any> = {
  empathetic: Heart,
  disciplined: Trophy,
  analytical: BarChart3,
  motivational: Zap,
  socratic: HelpCircle
}

function getStyleName(style: string, isZh: boolean): string {
  const zh: Record<string, string> = {
    empathetic: "温和共情",
    disciplined: "严厉纪律",
    analytical: "数据分析",
    motivational: "激励鼓舞",
    socratic: "苏格拉底",
  }
  const en: Record<string, string> = {
    empathetic: "Empathetic",
    disciplined: "Disciplined",
    analytical: "Analytical",
    motivational: "Motivational",
    socratic: "Socratic",
  }
  return (isZh ? zh : en)[style] || style
}

export function CoachSelector({
  selectedCoachId = "wendy",
  onCoachChange,
  className
}: CoachSelectorProps) {
  const { locale } = useI18n()
  const isZh = locale === "zh"
  const [coaches, setCoaches] = useState<Coach[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedCoach, setSelectedCoach] = useState<Coach | null>(null)

  useEffect(() => {
    fetchCoaches()
  }, [])

  useEffect(() => {
    if (coaches.length > 0) {
      const coach = coaches.find(c => c.id === selectedCoachId) || coaches[0]
      setSelectedCoach(coach)
    }
  }, [coaches, selectedCoachId])

  const fetchCoaches = async () => {
    try {
      const token = localStorage.getItem("aiwendy_access_token")
      const response = await fetch(`${API_V1_PREFIX}/coaches`, {
        headers: {
          "Authorization": token ? `Bearer ${token}` : ""
        }
      })

      if (!response.ok) {
        throw new Error("Failed to fetch coaches")
      }

      const data = await response.json()
      setCoaches(data)

      // 设置默认教练
      if (data.length > 0) {
        const defaultCoach = data.find((c: Coach) => c.id === selectedCoachId) || data[0]
        setSelectedCoach(defaultCoach)
      }
    } catch (error) {
      console.error("Error fetching coaches:", error)
      toast.error(isZh ? "无法加载教练列表" : "Failed to load coach list")
    } finally {
      setLoading(false)
    }
  }

  const handleCoachChange = (coachId: string) => {
    const coach = coaches.find(c => c.id === coachId)
    if (coach) {
      setSelectedCoach(coach)
      onCoachChange(coachId)
    }
  }

  if (loading) {
    return (
      <Select disabled>
        <SelectTrigger className={className}>
          <SelectValue placeholder={isZh ? "加载中..." : "Loading..."} />
        </SelectTrigger>
      </Select>
    )
  }

  if (!selectedCoach || coaches.length === 0) {
    return (
      <Select disabled>
        <SelectTrigger className={className}>
          <SelectValue placeholder={isZh ? "暂无可用教练" : "No coaches available"} />
        </SelectTrigger>
      </Select>
    )
  }

  const IconComponent = styleIcons[selectedCoach.style] || Brain

  return (
    <Select value={selectedCoach.id} onValueChange={handleCoachChange}>
      <SelectTrigger className={className}>
        <SelectValue>
          <div className="flex items-center gap-2">
            <Avatar className="w-6 h-6">
              <AvatarImage src={selectedCoach.avatar_url} alt={selectedCoach.name} />
              <AvatarFallback className="text-xs">
                <IconComponent className="w-3 h-3" />
              </AvatarFallback>
            </Avatar>
            <span className="font-medium">{selectedCoach.name}</span>
            <Badge variant="secondary" className="text-xs">
              {getStyleName(selectedCoach.style, isZh)}
            </Badge>
            {selectedCoach.is_premium && (
              <Badge variant="outline" className="text-xs">
                Pro
              </Badge>
            )}
          </div>
        </SelectValue>
      </SelectTrigger>
      <SelectContent className="max-w-[400px]">
        {coaches.map((coach) => {
          const CoachIcon = styleIcons[coach.style] || Brain
          return (
            <SelectItem key={coach.id} value={coach.id}>
              <div className="flex items-start gap-3 py-1">
                <Avatar className="w-8 h-8 mt-0.5">
                  <AvatarImage src={coach.avatar_url} alt={coach.name} />
                  <AvatarFallback className="text-xs">
                    <CoachIcon className="w-4 h-4" />
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium">{coach.name}</span>
                    <Badge variant="secondary" className="text-xs">
                      {getStyleName(coach.style, isZh)}
                    </Badge>
                    {coach.is_premium && (
                      <Badge variant="outline" className="text-xs">
                        Pro
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground line-clamp-2">
                    {coach.description}
                  </p>
                </div>
              </div>
            </SelectItem>
          )
        })}
      </SelectContent>
    </Select>
  )
}
