import {
  activeTooltipEntries,
  firstTooltipEntry,
  tooltipNumber,
  type ChartTooltipProps,
} from '@/lib/charts/recharts-tooltip'

interface ExamplePayload {
  label: string
  amount: number
}

describe('recharts tooltip helpers', () => {
  const activeProps: ChartTooltipProps<ExamplePayload> = {
    active: true,
    label: 'Jan 01',
    payload: [
      {
        name: 'Amount',
        value: '12.5',
        payload: { label: 'row', amount: 12.5 },
      },
    ],
  }

  it('returns the first active tooltip entry', () => {
    expect(firstTooltipEntry(activeProps)).toEqual(activeProps.payload?.[0])
    expect(firstTooltipEntry({ active: false, payload: activeProps.payload })).toBeNull()
    expect(firstTooltipEntry({ active: true, payload: [] })).toBeNull()
  })

  it('returns active entries only when tooltip is active', () => {
    expect(activeTooltipEntries(activeProps)).toHaveLength(1)
    expect(activeTooltipEntries({ active: false, payload: activeProps.payload })).toEqual([])
  })

  it('normalizes tooltip numeric values', () => {
    expect(tooltipNumber(12.5)).toBe(12.5)
    expect(tooltipNumber('12.5')).toBe(12.5)
    expect(tooltipNumber('not-a-number', 7)).toBe(7)
    expect(tooltipNumber(undefined, 3)).toBe(3)
  })
})
