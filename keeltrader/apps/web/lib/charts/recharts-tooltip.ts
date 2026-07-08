export type TooltipValue = string | number

export interface ChartTooltipEntry<TPayload> {
  name?: TooltipValue
  value?: TooltipValue
  payload?: TPayload
}

export interface ChartTooltipProps<TPayload> {
  active?: boolean
  payload?: ChartTooltipEntry<TPayload>[]
  label?: TooltipValue
}

export function firstTooltipEntry<TPayload>({
  active,
  payload,
}: ChartTooltipProps<TPayload>): ChartTooltipEntry<TPayload> | null {
  if (!active || !payload?.length) return null
  return payload[0] ?? null
}

export function activeTooltipEntries<TPayload>({
  active,
  payload,
}: ChartTooltipProps<TPayload>): ChartTooltipEntry<TPayload>[] {
  if (!active || !payload?.length) return []
  return payload
}

export function tooltipNumber(value: TooltipValue | undefined, fallback = 0): number {
  if (typeof value === 'number') return value
  if (typeof value === 'string') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : fallback
  }
  return fallback
}
