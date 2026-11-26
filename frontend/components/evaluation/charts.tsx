"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const SHORT: Record<string, string> = {
  technical_feasibility: "Technical",
  market_opportunity: "Market",
  competition: "Competition",
  business_model: "Business",
  resource_requirements: "Resources",
  execution_complexity: "Execution",
};

const tooltipStyle = {
  background: "var(--if-surface)",
  border: "1px solid var(--if-border)",
  borderRadius: 8,
  fontSize: 12,
  color: "var(--if-text)",
};

export interface RadarPoint {
  dimension: string;
  label: string;
  score: number;
  previous?: number | null;
}

export function DimensionRadar({ data, previousLabel }: { data: RadarPoint[]; previousLabel?: string }) {
  const rows = data.map((d) => ({ ...d, axis: SHORT[d.dimension] ?? d.label }));
  const hasPrevious = rows.some((r) => r.previous !== null && r.previous !== undefined);
  return (
    <div className="h-[260px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={rows} outerRadius="72%">
          <PolarGrid stroke="var(--if-border)" />
          <PolarAngleAxis dataKey="axis" tick={{ fill: "var(--if-muted)", fontSize: 11 }} />
          <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
          {hasPrevious && (
            <Radar
              name={previousLabel ?? "Previous version"}
              dataKey="previous"
              stroke="var(--if-muted)"
              strokeDasharray="4 3"
              fill="var(--if-muted)"
              fillOpacity={0.08}
            />
          )}
          <Radar
            name="This version"
            dataKey="score"
            stroke="var(--if-primary)"
            fill="var(--if-primary)"
            fillOpacity={0.22}
            strokeWidth={2}
          />
          <Tooltip contentStyle={tooltipStyle} />
          {hasPrevious && <Legend wrapperStyle={{ fontSize: 11 }} />}
        </RadarChart>
      </ResponsiveContainer>
      <table className="sr-only">
        <caption>Dimension scores</caption>
        <tbody>
          {rows.map((r) => (
            <tr key={r.dimension}>
              <th>{r.label}</th>
              <td>{r.score}</td>
              {hasPrevious && <td>{r.previous ?? "—"}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ScoreBars({
  data,
  labelA,
  labelB,
}: {
  data: { dimension: string; label: string; a: number | null; b: number | null }[];
  labelA: string;
  labelB: string;
}) {
  const rows = data.map((d) => ({ ...d, axis: SHORT[d.dimension] ?? d.label }));
  return (
    <div className="h-[260px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} barGap={2} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
          <CartesianGrid stroke="var(--if-border)" vertical={false} />
          <XAxis dataKey="axis" tick={{ fill: "var(--if-muted)", fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis domain={[0, 100]} tick={{ fill: "var(--if-muted)", fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--if-surface-soft)" }} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="a" name={labelA} fill="var(--if-muted)" fillOpacity={0.45} radius={[4, 4, 0, 0]} />
          <Bar dataKey="b" name={labelB} fill="var(--if-primary)" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
