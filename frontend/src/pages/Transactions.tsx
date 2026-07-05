import { Link } from "react-router-dom";
import { useAnalysis } from "../store";
import TransactionsTable from "../components/TransactionsTable";

export default function Transactions() {
  const { result, fileName } = useAnalysis();

  if (!result || result.transactions.length === 0) {
    return (
      <section className="page">
        <div className="empty">
          <div className="big">No transactions yet</div>
          <p>Upload a statement to see the cleaned, categorized rows.</p>
          <Link to="/upload" className="btn primary" style={{ marginTop: "1rem" }}>
            Upload a statement
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section className="page">
      <div className="page-head">
        <div>
          <h1>Transactions</h1>
          <p className="sub">
            Cleaned &amp; categorized rows{fileName ? <> from <code>{fileName}</code></> : null}.
          </p>
        </div>
        <Link to="/dashboard" className="btn">
          Back to dashboard
        </Link>
      </div>

      <TransactionsTable transactions={result.transactions} />
    </section>
  );
}
