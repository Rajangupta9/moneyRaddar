// Searchable / filterable table of cleaned transactions.
//
// This is also the dataviz "table view" that backs the charts — every number on
// the dashboard is inspectable here, row by row.

import { useMemo, useState } from "react";
import type { Category, Transaction } from "../types";
import { inrSigned } from "../format";

const CATEGORIES: (Category | "All")[] = [
  "All",
  "Food",
  "Travel",
  "Shopping",
  "Bills",
  "EMI",
  "Subscriptions",
  "Salary",
  "Rent",
  "Investments",
  "Other",
];

interface Props {
  transactions: Transaction[];
}

export default function TransactionsTable({ transactions }: Props) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<Category | "All">("All");

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return transactions.filter((t) => {
      if (category !== "All" && t.category !== category) return false;
      if (!q) return true;
      return (
        t.description_raw.toLowerCase().includes(q) ||
        (t.merchant ?? "").toLowerCase().includes(q)
      );
    });
  }, [transactions, query, category]);

  return (
    <div>
      <div className="toolbar">
        <input
          type="search"
          placeholder="Search description or merchant…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search transactions"
        />
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value as Category | "All")}
          aria-label="Filter by category"
        >
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c === "All" ? "All categories" : c}
            </option>
          ))}
        </select>
        <span className="chip" style={{ alignSelf: "center" }}>
          {rows.length} of {transactions.length}
        </span>
      </div>

      <div className="table-wrap">
        <table className="txns">
          <thead>
            <tr>
              <th>Date</th>
              <th>Description</th>
              <th>Merchant</th>
              <th>Category</th>
              <th style={{ textAlign: "right" }}>Amount</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={5} className="desc" style={{ textAlign: "center" }}>
                  No transactions match your filters.
                </td>
              </tr>
            ) : (
              rows.map((t) => (
                <tr key={t.id}>
                  <td>{t.date}</td>
                  <td className="desc">{t.description_raw}</td>
                  <td>{t.merchant ?? "—"}</td>
                  <td>
                    <span className="pill">{t.category}</span>
                  </td>
                  <td className="num">
                    <span className={t.amount < 0 ? "amt-out" : "amt-in"}>
                      {inrSigned(t.amount)}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
