// Category breakdown — a horizontal ranked bar.
//
// dataviz form pick: the reader's job is "compare magnitude, low→high" across
// categories, so this is a single-hue (blue) magnitude bar, NOT a rainbow of
// per-category colors. Direct value labels sit at each bar end; ranking carries
// the ordering. One hue is trivially colorblind-safe.

import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CategoryBreakdown } from "../types";
import { inr, pct } from "../format";

interface Props {
  data: CategoryBreakdown[];
}

interface TipProps {
  active?: boolean;
  payload?: { payload: CategoryBreakdown }[];
}

function CategoryTooltip({ active, payload }: TipProps) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="viz-tip">
      <div className="row">
        <span className="swatch" />
        <span className="k">{d.category}</span>
      </div>
      <div className="row">
        <span className="k">Spend</span>
        <span className="v">{inr(d.amount)}</span>
      </div>
      <div className="row">
        <span className="k">Share</span>
        <span className="v">{pct(d.pct)}</span>
      </div>
    </div>
  );
}

export default function CategoryChart({ data }: Props) {
  if (!data.length) {
    return <p className="muted">No spending recorded in this period.</p>;
  }

  const rows = data.map((d) => ({ ...d, name: d.category }));
  const height = Math.max(200, rows.length * 40);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        layout="vertical"
        data={rows}
        margin={{ top: 4, right: 64, bottom: 4, left: 8 }}
        barCategoryGap="28%"
      >
        <CartesianGrid horizontal={false} stroke="var(--viz-grid)" />
        <XAxis
          type="number"
          tickFormatter={(v) => inr(v)}
          tick={{ fill: "var(--viz-label)", fontSize: 11 }}
          axisLine={{ stroke: "var(--viz-axis)" }}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={92}
          tick={{ fill: "var(--text)", fontSize: 12 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip cursor={{ fill: "var(--viz-grid)", opacity: 0.4 }} content={<CategoryTooltip />} />
        <Bar dataKey="amount" fill="var(--series-blue)" radius={[0, 4, 4, 0]} barSize={18}>
          <LabelList
            dataKey="amount"
            position="right"
            formatter={(v: number) => inr(v)}
            style={{ fill: "var(--text)", fontSize: 11, fontWeight: 600 }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
