'use client'

import { useState } from 'react'
import {
  FileText,
  FileSpreadsheet,
  FileImage,
  FileAudio,
  FileCode,
  File,
  Download,
  X,
  Loader2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { AttachmentType } from '@/types/chat'
import { formatFileSize } from '@/types/chat'

interface FileAttachmentProps {
  fileName: string
  fileSize: number
  type: AttachmentType
  url?: string
  transcription?: string
  extractedText?: string
  onRemove?: () => void
  onDownload?: () => void
  isLoading?: boolean
  className?: string
  showPreview?: boolean
}

const fileIcons: Record<AttachmentType, typeof File> = {
  pdf: FileText,
  word: FileText,
  excel: FileSpreadsheet,
  ppt: FileText,
  text: FileText,
  code: FileCode,
  image: FileImage,
  audio: FileAudio,
  file: File,
}

const fileColors: Record<AttachmentType, string> = {
  pdf: 'text-red-500',
  word: 'text-blue-500',
  excel: 'text-green-500',
  ppt: 'text-orange-500',
  text: 'text-gray-500',
  code: 'text-purple-500',
  image: 'text-pink-500',
  audio: 'text-yellow-500',
  file: 'text-gray-400',
}

export function FileAttachment({
  fileName,
  fileSize,
  type,
  url,
  transcription,
  extractedText,
  onRemove,
  onDownload,
  isLoading = false,
  className,
  showPreview = false,
}: FileAttachmentProps) {
  const [showExtracted, setShowExtracted] = useState(false)
  const Icon = fileIcons[type] || File
  const colorClass = fileColors[type] || 'text-gray-400'

  const hasExtractedContent = transcription || extractedText
  const extractedContent = transcription || extractedText

  const handleDownload = () => {
    if (onDownload) {
      onDownload()
    } else if (url) {
      window.open(url, '_blank')
    }
  }

  return (
    <div
      className={cn(
        'flex flex-col rounded-lg border bg-muted/50 overflow-hidden',
        className
      )}
    >
      <div className="flex items-center gap-3 p-3">
        {isLoading ? (
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        ) : (
          <Icon className={cn('h-8 w-8', colorClass)} />
        )}

        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate" title={fileName}>
            {fileName}
          </p>
          <p className="text-xs text-muted-foreground">
            {formatFileSize(fileSize)}
            {type !== 'file' && ` • ${type.toUpperCase()}`}
          </p>
        </div>

        <div className="flex items-center gap-1">
          {hasExtractedContent && showPreview && (
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0"
              onClick={() => setShowExtracted(!showExtracted)}
            >
              {showExtracted ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>
          )}

          {url && (
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0"
              onClick={handleDownload}
            >
              <Download className="h-4 w-4" />
            </Button>
          )}

          {onRemove && (
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0 hover:text-destructive"
              onClick={onRemove}
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Audio player for audio files */}
      {type === 'audio' && url && (
        <div className="px-3 pb-3">
          <audio src={url} controls className="w-full h-8" />
        </div>
      )}

      {/* Extracted content preview */}
      {showExtracted && extractedContent && (
        <div className="border-t px-3 py-2 bg-background/50">
          <p className="text-xs text-muted-foreground mb-1">
            {transcription ? 'Transcription:' : 'Extracted Text:'}
          </p>
          <p className="text-sm whitespace-pre-wrap max-h-32 overflow-y-auto">
            {extractedContent.length > 500
              ? extractedContent.slice(0, 500) + '...'
              : extractedContent}
          </p>
        </div>
      )}
    </div>
  )
}
