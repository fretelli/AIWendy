'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { StreamEvent, StreamInfo } from '@/lib/types/agents'

interface EventStreamProps {
  events: StreamEvent[]
  streamInfo: StreamInfo | null
  loading: boolean
  onSubmitEvent: () => void
}

function formatTimestamp(ts?: string): string {
  if (!ts) return '-'
  try {
    const d = new Date(ts)
    if (isNaN(d.getTime())) return ts
    return d.toLocaleString()
  } catch {
    return ts
  }
}

function eventTypeBadgeVariant(type?: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (!type) return 'outline'
  if (type.includes('error') || type.includes('circuit_breaker')) return 'destructive'
  if (type.includes('trade') || type.includes('order')) return 'default'
  if (type.includes('agent')) return 'secondary'
  return 'outline'
}

export function EventStream({ events, streamInfo, loading, onSubmitEvent }: EventStreamProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  if (loading && events.length === 0) {
    return <div className="text-sm text-muted-foreground">Loading...</div>
  }

  return (
    <div className="space-y-4">
      {/* Stream Info + Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          {streamInfo && (
            <>
              <span className="text-sm text-muted-foreground">
                Stream: {streamInfo.stream}
              </span>
              <Badge variant="outline">
                {streamInfo.length} events
              </Badge>
              {streamInfo.groups !== undefined && (
                <Badge variant="outline">
                  {streamInfo.groups} groups
                </Badge>
              )}
            </>
          )}
          {streamInfo?.message && (
            <span className="text-sm text-muted-foreground">{streamInfo.message}</span>
          )}
        </div>
        <Button size="sm" onClick={onSubmitEvent}>Submit Event</Button>
      </div>

      {/* Events Table */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Recent Events ({events.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {events.length === 0 ? (
            <p className="text-sm text-muted-foreground">No events yet</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[180px]">Time</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Agent</TableHead>
                  <TableHead>Payload</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {events.map((event) => {
                  const isExpanded = expandedId === event.stream_id
                  const payloadStr = typeof event.payload === 'object'
                    ? JSON.stringify(event.payload, null, 2)
                    : String(event.payload || '-')

                  return (
                    <TableRow
                      key={event.stream_id}
                      className="cursor-pointer"
                      onClick={() => setExpandedId(isExpanded ? null : event.stream_id)}
                    >
                      <TableCell className="text-xs font-mono">
                        {formatTimestamp(event.timestamp)}
                      </TableCell>
                      <TableCell>
                        <Badge variant={eventTypeBadgeVariant(event.type)}>
                          {event.type || 'unknown'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs">{event.source || '-'}</TableCell>
                      <TableCell className="text-xs">{event.agent_id || '-'}</TableCell>
                      <TableCell>
                        {isExpanded ? (
                          <pre className="max-h-40 overflow-auto whitespace-pre-wrap rounded bg-muted p-2 text-xs">
                            {payloadStr}
                          </pre>
                        ) : (
                          <span className="text-xs text-muted-foreground truncate block max-w-[200px]">
                            {payloadStr.length > 60 ? payloadStr.slice(0, 60) + '...' : payloadStr}
                          </span>
                        )}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
