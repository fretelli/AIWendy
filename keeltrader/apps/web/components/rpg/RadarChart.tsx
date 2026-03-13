'use client';

import {
  Radar,
  RadarChart as RechartsRadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from 'recharts';

interface RadarChartProps {
  attributes: {
    discipline: number;
    patience: number;
    risk_management: number;
    decisiveness: number;
    consistency: number;
  };
}

const LABELS: Record<string, string> = {
  discipline: 'Discipline',
  patience: 'Patience',
  risk_management: 'Risk Mgmt',
  decisiveness: 'Decisiveness',
  consistency: 'Consistency',
};

export function RadarChart({ attributes }: RadarChartProps) {
  const data = Object.entries(attributes).map(([key, value]) => ({
    attribute: LABELS[key] || key,
    value,
    fullMark: 100,
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <RechartsRadarChart data={data} cx="50%" cy="50%" outerRadius="75%">
        <PolarGrid stroke="hsl(var(--border))" />
        <PolarAngleAxis
          dataKey="attribute"
          tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
        />
        <PolarRadiusAxis
          angle={90}
          domain={[0, 100]}
          tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }}
        />
        <Radar
          name="Attributes"
          dataKey="value"
          stroke="hsl(var(--primary))"
          fill="hsl(var(--primary))"
          fillOpacity={0.25}
          strokeWidth={2}
        />
      </RechartsRadarChart>
    </ResponsiveContainer>
  );
}
