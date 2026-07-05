import { Link } from "react-router-dom";
import { useAnalysis } from "../store";
import { inr, pct, monthLabel } from "../format";
import KpiTile from "../components/KpiTile";
import CategoryChart from "../components/CategoryChart";
import TrendChart from "../components/TrendChart";

function EmptyState() {
  return (
    <section className="page">
      <div className="empty">
        <div className="big">No statement analyzed yet</div>
        <p>Upload a CSV to see your income, spending and savings.</p>
        <Link to="/upload" className="btn primary" style={{ marginTop: "1rem" }}>
          Upload a statement
        </Link>
      </div>
    </section>
  );
}

export default function Dashboard() {
  const { result, fileName } = useAnalysis();

  if (!result?.summary) return <EmptyState />;

  const s = result.summary;
  const biggest = s.biggest_transaction;
  const period =
    s.period.start && s.period.end
      ? `${monthLabel(s.period.start.slice(0, 7))} → ${monthLabel(s.period.end.slice(0, 7))}`
      : "";

  return (
    <section className="page">
      <div className="page-head">
        <div>
          <h1>Dashboard</h1>
          <p className="sub">
            {fileName ? <code>{fileName}</code> : null} · {result.transactions.length}{" "}
            transactions · {period}
          </p>
        </div>
        <Link to="/upload" className="btn">
          Upload another
        </Link>
      </div>

      <div className="kpi-row">
        <KpiTile label="Income" value={inr(s.total_income)} tone="good" context="credits in period" />
        <KpiTile label="Spend" value={inr(s.total_spend)} context="debits in period" />
        <KpiTile
          label="Net savings"
          value={inr(s.net_savings)}
          tone={s.net_savings >= 0 ? "good" : "bad"}
          context="income − spend"
        />
        <KpiTile
          label="Savings rate"
          value={pct(s.savings_rate)}
          tone={s.savings_rate >= 0 ? "good" : "bad"}
          context="of income kept"
        />
      </div>

      {biggest && (
        <div className="card wide" style={{ marginBottom: "1rem" }}>
          <div className="callout">
            <div>
              <div className="card-sub" style={{ margin: 0 }}>Biggest transaction</div>
              <div className="who">{biggest.merchant ?? biggest.description_raw}</div>
              <div className="meta">
                {biggest.description_raw} · {biggest.date}
              </div>
            </div>
            <div className="amt">{inr(Math.abs(biggest.amount))}</div>
          </div>
        </div>
      )}

      <div className="card-grid">
        <div className="card">
          <h2>Spending by category</h2>
          <p className="card-sub">Share of {inr(s.total_spend)} total spend</p>
          <CategoryChart data={s.by_category} />
        </div>

        <div className="card">
          <h2>Monthly trend</h2>
          <p className="card-sub">Income vs spend over time</p>
          <TrendChart data={s.monthly_trend} />
        </div>
      </div>
    </section>
  );
}
