"use client"

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { CoachBrief, RoundtableMessage, MessageType } from "@/lib/types/roundtable"
import { ImagePreview } from "@/components/chat/ImagePreview"
import { FileAttachment } from "@/components/chat/FileAttachment"
import type { AttachmentType } from "@/types/chat"
import { useI18n } from "@/lib/i18n/provider"

interface CoachResponseCardProps {
  message: RoundtableMessage
  coach?: CoachBrief | null
  isStreaming?: boolean
  className?: string
}

export function CoachResponseCard({
  message,
  coach,
  isStreaming = false,
  className,
}: CoachResponseCardProps) {
  const { locale } = useI18n()
  const isZh = locale === "zh"
  const isUser = message.role === "user"
  const isModerator = message.message_type && message.message_type !== "response"

  if (isUser) {
    const attachments = message.attachments || []
    const images = attachments.filter((a) => a.type === "image")
    const files = attachments.filter((a) => a.type !== "image")

    return (
      <div className={cn("flex justify-end", className)}>
        <div className="max-w-[80%] space-y-2">
          {attachments.length > 0 && (
            <div className="space-y-2">
              {images.length > 0 && (
                <div className="flex flex-wrap justify-end gap-2">
                  {images.map((img) => (
                    <ImagePreview
                      key={img.id}
                      src={img.thumbnailUrl || img.url}
                      alt={img.fileName}
                      size="sm"
                    />
                  ))}
                </div>
              )}
              {files.length > 0 && (
                <div className="space-y-2">
                  {files.map((file) => (
                    <FileAttachment
                      key={file.id}
                      fileName={file.fileName}
                      fileSize={file.fileSize}
                      type={file.type as AttachmentType}
                      url={file.url}
                      transcription={file.transcription}
                      extractedText={file.extractedText}
                      showPreview
                    />
                  ))}
                </div>
              )}
            </div>
          )}
          <div className="rounded-2xl rounded-tr-sm bg-primary px-4 py-3 text-primary-foreground">
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          </div>
        </div>
      </div>
    )
  }

  const coachInfo = coach || message.coach

  // Render moderator message with special styling
  if (isModerator) {
    return (
      <ModeratorCard
        message={message}
        coach={coachInfo}
        isStreaming={isStreaming}
        className={className}
      />
    )
  }

  // Regular coach response
  return (
    <Card className={cn("border-l-4", getCoachBorderColor(coachInfo?.style), className)}>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <Avatar className="h-10 w-10 shrink-0">
            <AvatarImage src={coachInfo?.avatar_url} alt={coachInfo?.name} />
            <AvatarFallback className="text-sm">
              {coachInfo?.name?.charAt(0) || "C"}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0 space-y-2">
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm">
                {coachInfo?.name || (isZh ? "教练" : "Coach")}
              </span>
              {coachInfo?.style && (
                <Badge variant="outline" className="text-xs">
                  {getStyleLabel(coachInfo.style, isZh)}
                </Badge>
              )}
              {isStreaming && (
                <Badge variant="secondary" className="text-xs animate-pulse">
                  {isZh ? "输入中..." : "Typing..."}
                </Badge>
              )}
            </div>
            <p className="text-sm text-foreground whitespace-pre-wrap">
              {message.content}
              {isStreaming && <span className="animate-pulse">▊</span>}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// Moderator card component
interface ModeratorCardProps {
  message: RoundtableMessage
  coach?: CoachBrief | null
  isStreaming?: boolean
  className?: string
}

function ModeratorCard({
  message,
  coach,
  isStreaming = false,
  className,
}: ModeratorCardProps) {
  const messageType = message.message_type || "response"
  const { locale } = useI18n()
  const isZh = locale === "zh"
  const typeLabel = getModeratorTypeLabel(messageType, isZh)
  const typeColor = getModeratorTypeColor(messageType)

  return (
    <Card
      className={cn(
        "border-l-4 border-l-amber-500",
        messageType === "opening" && "bg-amber-50/30 dark:bg-amber-950/20",
        messageType === "summary" && "bg-blue-50/30 dark:bg-blue-950/20",
        messageType === "closing" && "bg-green-50/30 dark:bg-green-950/20",
        className
      )}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <Avatar className="h-10 w-10 shrink-0 ring-2 ring-amber-500/50">
            <AvatarImage src={coach?.avatar_url} alt={coach?.name} />
            <AvatarFallback className="text-sm bg-amber-100 text-amber-700">
              {coach?.name?.charAt(0) || "H"}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0 space-y-2">
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm">
                {coach?.name || (isZh ? "主持人" : "Moderator")}
              </span>
              <Badge className={cn("text-xs", typeColor)}>
                {typeLabel}
              </Badge>
              {isStreaming && (
                <Badge variant="secondary" className="text-xs animate-pulse">
                  {isZh ? "输入中..." : "Typing..."}
                </Badge>
              )}
            </div>
            <p className="text-sm text-foreground whitespace-pre-wrap">
              {message.content}
              {isStreaming && <span className="animate-pulse">▊</span>}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function getModeratorTypeLabel(type: MessageType, isZh: boolean): string {
  const zh: Record<MessageType, string> = {
    response: "回复",
    opening: "开场",
    summary: "本轮总结",
    closing: "讨论总结",
  }
  const en: Record<MessageType, string> = {
    response: "Response",
    opening: "Opening",
    summary: "Round Summary",
    closing: "Closing Summary",
  }
  return (isZh ? zh : en)[type] || type
}

function getModeratorTypeColor(type: MessageType): string {
  const colors: Record<MessageType, string> = {
    response: "bg-gray-100 text-gray-700",
    opening: "bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300",
    summary: "bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300",
    closing: "bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300",
  }
  return colors[type] || colors.response
}

function getCoachBorderColor(style?: string): string {
  const colors: Record<string, string> = {
    empathetic: "border-l-pink-500",
    disciplined: "border-l-red-500",
    analytical: "border-l-blue-500",
    motivational: "border-l-yellow-500",
    socratic: "border-l-purple-500",
  }
  return colors[style || ""] || "border-l-gray-500"
}

function getStyleLabel(style: string, isZh: boolean): string {
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

// Round indicator component
interface RoundIndicatorProps {
  round: number
  className?: string
}

export function RoundIndicator({ round, className }: RoundIndicatorProps) {
  const { locale } = useI18n()
  const isZh = locale === "zh"
  return (
    <div className={cn("flex items-center justify-center py-4", className)}>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="h-px flex-1 bg-border min-w-[40px]" />
        <span className="px-3 py-1 bg-muted rounded-full">
          {isZh ? `第 ${round} 轮讨论` : `Round ${round}`}
        </span>
        <span className="h-px flex-1 bg-border min-w-[40px]" />
      </div>
    </div>
  )
}
