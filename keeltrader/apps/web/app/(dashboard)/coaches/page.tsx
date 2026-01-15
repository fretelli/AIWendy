"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Star, MessageCircle, Users, Trophy, Brain, Heart, BarChart3, Zap, HelpCircle } from "lucide-react"
import { toast } from "sonner"
import { API_V1_PREFIX } from "@/lib/config"
import { useI18n } from "@/lib/i18n/provider"
import { getActiveProjectId } from "@/lib/active-project"

interface Coach {
  id: string
  name: string
  avatar_url?: string
  description?: string
  bio?: string
  style: string
  personality_traits: string[]
  specialty: string[]
  language: string
  is_premium: boolean
  is_public: boolean
  total_sessions: number
  avg_rating?: number
  rating_count: number
}

const styleIcons: Record<string, any> = {
  empathetic: Heart,
  disciplined: Trophy,
  analytical: BarChart3,
  motivational: Zap,
  socratic: HelpCircle
}

const styleColors: Record<string, string> = {
  empathetic: "bg-pink-100 text-pink-800",
  disciplined: "bg-red-100 text-red-800",
  analytical: "bg-blue-100 text-blue-800",
  motivational: "bg-yellow-100 text-yellow-800",
  socratic: "bg-purple-100 text-purple-800"
}

export default function CoachesPage() {
  const router = useRouter()
  const { t } = useI18n()
  const [coaches, setCoaches] = useState<Coach[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedStyle, setSelectedStyle] = useState<string>("all")

  const styleLabel = (style: string): string => {
    if (style === "empathetic") return t("coaches.coachStyles.empathetic")
    if (style === "disciplined") return t("coaches.coachStyles.disciplined")
    if (style === "analytical") return t("coaches.coachStyles.analytical")
    if (style === "motivational") return t("coaches.coachStyles.motivational")
    if (style === "socratic") return t("coaches.coachStyles.socratic")
    return style
  }

  useEffect(() => {
    fetchCoaches()
  }, [])

  const fetchCoaches = async () => {
    try {
      const token = localStorage.getItem("keeltrader_access_token")
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
    } catch (error) {
      console.error("Error fetching coaches:", error)
      toast.error(t("coaches.errors.load"))
    } finally {
      setLoading(false)
    }
  }

  const startSession = async (coachId: string) => {
    try {
      const token = localStorage.getItem("keeltrader_access_token")
      const projectId = getActiveProjectId()
      const response = await fetch(`${API_V1_PREFIX}/coaches/sessions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": token ? `Bearer ${token}` : ""
        },
        body: JSON.stringify({
          coach_id: coachId,
          project_id: projectId,
          title: t("coaches.sessionTitle", { name: coaches.find(c => c.id === coachId)?.name || "" })
        })
      })

      if (!response.ok) {
        throw new Error("Failed to create session")
      }

      const session = await response.json()
      router.push(`/chat?session=${session.id}&coach=${coachId}`)
    } catch (error) {
      console.error("Error starting session:", error)
      toast.error(t("coaches.errors.startChat"))
    }
  }

  const filteredCoaches = selectedStyle === "all"
    ? coaches
    : coaches.filter(coach => coach.style === selectedStyle)

  const renderStars = (rating: number) => {
    return Array.from({ length: 5 }, (_, i) => (
      <Star
        key={i}
        className={`w-4 h-4 ${i < Math.floor(rating) ? "fill-yellow-400 text-yellow-400" : "text-gray-300"}`}
      />
    ))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">{t('coaches.marketplace')}</h1>
        <div className="mb-3 flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => router.push("/coaches/custom")}>
            {t("coaches.customCoaches")}
          </Button>
        </div>
        <p className="text-muted-foreground">
          {t("coaches.marketplaceSubtitle")}
        </p>
      </div>

      <Tabs value={selectedStyle} onValueChange={setSelectedStyle} className="mb-8">
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="all">{t("coaches.tabs.all")}</TabsTrigger>
          <TabsTrigger value="empathetic">{t('coaches.coachStyles.empathetic')}</TabsTrigger>
          <TabsTrigger value="disciplined">{t('coaches.coachStyles.disciplined')}</TabsTrigger>
          <TabsTrigger value="analytical">{t('coaches.coachStyles.analytical')}</TabsTrigger>
          <TabsTrigger value="motivational">{t('coaches.coachStyles.motivational')}</TabsTrigger>
          <TabsTrigger value="socratic">{t('coaches.coachStyles.socratic')}</TabsTrigger>
        </TabsList>
      </Tabs>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredCoaches.map((coach) => {
          const IconComponent = styleIcons[coach.style] || Brain
          return (
            <Card key={coach.id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between mb-4">
                  <Avatar className="w-16 h-16">
                    <AvatarImage src={coach.avatar_url} alt={coach.name} />
                    <AvatarFallback>
                      <IconComponent className="w-8 h-8" />
                    </AvatarFallback>
                  </Avatar>
                  {coach.is_premium && (
                    <Badge variant="secondary" className="bg-gradient-to-r from-yellow-400 to-yellow-600 text-white">
                      {t("coaches.premium")}
                    </Badge>
                  )}
                </div>
                <CardTitle className="text-xl mb-2">{coach.name}</CardTitle>
                <Badge className={styleColors[coach.style]}>
                  {styleLabel(coach.style)}
                </Badge>
              </CardHeader>
              <CardContent className="space-y-4">
                <CardDescription className="line-clamp-2">
                  {coach.description}
                </CardDescription>

                <div className="space-y-2">
                  <div className="flex flex-wrap gap-1">
                    {coach.specialty.slice(0, 3).map((spec, idx) => (
                      <Badge key={idx} variant="outline" className="text-xs">
                        {spec}
                      </Badge>
                    ))}
                    {coach.specialty.length > 3 && (
                      <Badge variant="outline" className="text-xs">
                        +{coach.specialty.length - 3}
                      </Badge>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between text-sm text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <Users className="w-4 h-4" />
                    <span>{coach.total_sessions} {t('coaches.sessions')}</span>
                  </div>
                  {coach.avg_rating && (
                    <div className="flex items-center gap-1">
                      {renderStars(coach.avg_rating)}
                      <span className="ml-1">({coach.rating_count})</span>
                    </div>
                  )}
                </div>

                <Button
                  className="w-full"
                  onClick={() => startSession(coach.id)}
                >
                  <MessageCircle className="w-4 h-4 mr-2" />
                  {t('coaches.startChat')}
                </Button>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {filteredCoaches.length === 0 && (
        <Card className="text-center py-12">
          <CardContent>
            <p className="text-muted-foreground">
              {t("coaches.noCoachesOfType")}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
