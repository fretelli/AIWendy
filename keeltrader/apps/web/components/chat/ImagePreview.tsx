'use client'

import { useState } from 'react'
import { X, ZoomIn, Loader2 } from 'lucide-react'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import { cn } from '@/lib/utils'

interface ImagePreviewProps {
  src: string
  alt?: string
  onRemove?: () => void
  className?: string
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
}

export function ImagePreview({
  src,
  alt = 'Image',
  onRemove,
  className,
  size = 'md',
  isLoading = false,
}: ImagePreviewProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [hasError, setHasError] = useState(false)

  const sizeClasses = {
    sm: 'w-16 h-16',
    md: 'w-24 h-24',
    lg: 'w-32 h-32',
  }

  if (hasError) {
    return (
      <div
        className={cn(
          'relative rounded-lg overflow-hidden bg-muted flex items-center justify-center',
          sizeClasses[size],
          className
        )}
      >
        <span className="text-xs text-muted-foreground">Failed</span>
      </div>
    )
  }

  return (
    <>
      <div
        className={cn(
          'relative group rounded-lg overflow-hidden border bg-muted',
          sizeClasses[size],
          className
        )}
      >
        {isLoading ? (
          <div className="absolute inset-0 flex items-center justify-center bg-muted">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            <img
              src={src}
              alt={alt}
              className="w-full h-full object-cover"
              onError={() => setHasError(true)}
            />
            <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
              <button
                onClick={() => setIsOpen(true)}
                className="p-1.5 rounded-full bg-white/20 hover:bg-white/40 transition-colors"
                type="button"
              >
                <ZoomIn className="h-4 w-4 text-white" />
              </button>
              {onRemove && (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onRemove()
                  }}
                  className="p-1.5 rounded-full bg-white/20 hover:bg-red-500/80 transition-colors"
                  type="button"
                >
                  <X className="h-4 w-4 text-white" />
                </button>
              )}
            </div>
          </>
        )}
      </div>

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="max-w-4xl p-0 overflow-hidden">
          <img
            src={src}
            alt={alt}
            className="w-full h-auto max-h-[80vh] object-contain"
          />
        </DialogContent>
      </Dialog>
    </>
  )
}
