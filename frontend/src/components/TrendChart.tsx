// Monthly trend — income vs spend over time.
//
// dataviz form pick: "trend over time" with two distinct series to tell apart →
// categorical, two hues (blue spend / aqua income, adjacent CVD ΔE 24.2 — well
// clear of the ≥12 target). Legend is always present for ≥2 series; visible dots
// so a single-month statement still shows its point.

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { MonthlyTrendPoint } from "../types";
import { inr, monthLabel } from "../format";

interface Props {
  data: MonthlyTrendPoint[];
}

interface TipProps {
  active?: boolean;
  label?: string;
  payload?: { name: string; value: number; color: string }[];
}

function TrendTooltip({ active, label, payload }: TipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="viz-tip">
      <div className="row">
        <span className="k">{monthLabel(label ?? "")}</span>
      </div>
      {payload.map((p) => (
        <div className="row" key={p.name}>
          <span className="swatch" style={{ background: p.color }} />
          <span className="k">{p.name}</span>
          <span className="v">{inr(p.value)}</span>
        </div>
      ))}
    </div>
  );
}

export default function TrendChart({ data }: Props) {
  if (!data.length) {
    return <p className="muted">No dated transactions to trend.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: 8 }}>
        <CartesianGrid vertical={false} stroke="var(--viz-grid)" />
        <XAxis
          dataKey="month"
          tickFormatter={monthLabel}
          tick={{ fill: "var(--viz-label)", fontSize: 11 }}
          axisLine={{ stroke: "var(--viz-axis)" }}
          tickLine={false}
        />
        <YAxis
          tickFormatter={(v) => inr(v)}
          tick={{ fill: "var(--viz-label)", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={70}
        />
        <Tooltip content={<TrendTooltip />} />
        <Legend wrapperStyle={{ fontSize: 12, color: "var(--muted)" }} />
        <Line
          type="monotone"
          dataKey="income"
          name="Income"
          stroke="var(--series-aqua)"
          strokeWidth={2}
          dot={{ r: 4, fill: "var(--series-aqua)" }}
          activeDot={{ r: 6 }}
        />
        <Line
          type="monotone"
          dataKey="spend"
          name="Spend"
          stroke="var(--series-blue)"
          strokeWidth={2}
          dot={{ r: 4, fill: "var(--series-blue)" }}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
