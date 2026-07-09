'use client'

import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { agentsAPI } from '@/lib/api/agents'
import type { JsonObject } from '@/lib/types/json'

interface EventSubmitDialogProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

const EVENT_TYPES = [
  'price.alert',
  'trade.opened',
  'trade.closed',
  'order.requested',
  'agent.analysis',
  'agent.recommendation',
  'pattern.detected',
  'behavior.alert',
  'circuit_breaker.on',
  'circuit_breaker.off',
  'user.message',
  'user.command',
  'health.check',
]

function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message
  }

  if (typeof error === 'object' && error !== null && 'message' in error) {
    const message = (error as { message?: unknown }).message
    if (typeof message === 'string' && message.trim()) {
      return message
    }
  }

  return 'Failed to submit event'
}

export function EventSubmitDialog({ open, onClose, onSuccess }: EventSubmitDialogProps) {
  const [eventType, setEventType] = useState('')
  const [userId, setUserId] = useState('')
  const [payloadStr, setPayloadStr] = useState('{}')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    if (!eventType) {
      setError('Please select an event type')
      return
    }

    let payload: JsonObject = {}
    try {
      const parsed: unknown = JSON.parse(payloadStr)
      if (!isJsonObject(parsed)) {
        setError('Payload must be a JSON object')
        return
      }
      payload = parsed
    } catch {
      setError('Invalid JSON payload')
      return
    }

    setSubmitting(true)
    setError('')
    try {
      await agentsAPI.submitEvent({
        event_type: eventType,
        user_id: userId || undefined,
        payload,
      })
      onSuccess()
      onClose()
      setEventType('')
      setUserId('')
      setPayloadStr('{}')
    } catch (e: unknown) {
      setError(getErrorMessage(e))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Submit Event</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Event Type</Label>
            <Select value={eventType} onValueChange={setEventType}>
              <SelectTrigger>
                <SelectValue placeholder="Select event type" />
              </SelectTrigger>
              <SelectContent>
                {EVENT_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>{t}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>User ID (optional)</Label>
            <Input
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="e.g., default"
            />
          </div>

          <div className="space-y-2">
            <Label>Payload (JSON)</Label>
            <Textarea
              value={payloadStr}
              onChange={(e) => setPayloadStr(e.target.value)}
              className="font-mono text-sm"
              rows={5}
            />
          </div>

          {error && (
            <p className="text-sm text-red-500">{error}</p>
          )}

          <Button
            className="w-full"
            onClick={handleSubmit}
            disabled={submitting}
          >
            {submitting ? 'Submitting...' : 'Submit Event'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
