// A single headline number (dataviz: "stat tile", not a one-bar chart).

interface Props {
  label: string;
  value: string;
  context?: string;
  tone?: "good" | "bad" | "neutral";
}

export default function KpiTile({ label, value, context, tone = "neutral" }: Props) {
  const toneClass = tone === "good" ? " good" : tone === "bad" ? " bad" : "";
  return (
    <div className="kpi">
      <div className="label">{label}</div>
      <div className={`value${toneClass}`}>{value}</div>
      {context && <div className="context">{context}</div>}
    </div>
  );
}
