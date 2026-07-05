import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { getHealth } from "./api";
import type { HealthResponse } from "./types";
import Upload from "./pages/Upload";
import Dashboard from "./pages/Dashboard";
import Transactions from "./pages/Transactions";
import Recurring from "./pages/Recurring";
import Insights from "./pages/Insights";
import Report from "./pages/Report";

const NAV = [
  { to: "/upload", label: "Upload" },
  { to: "/dashboard", label: "Dashboard" },
  { to: "/transactions", label: "Transactions" },
  { to: "/recurring", label: "Recurring" },
  { to: "/insights", label: "Insights" },
  { to: "/report", label: "Report" },
];

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHealth().then(setHealth).catch((e) => setError(String(e)));
  }, []);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          RupeeRadar <span className="tag">₹</span>
        </div>
        <nav className="nav">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="status">
          {error ? (
            <span className="dot bad" title={error}>
              backend offline
            </span>
          ) : health ? (
            <span className="dot ok" title={`model: ${health.llm_model}`}>
              backend ok · v{health.version}
            </span>
          ) : (
            <span className="dot">connecting…</span>
          )}
        </div>
      </header>

      <main className="content">
        <Routes>
          <Route path="/" element={<Navigate to="/upload" replace />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/recurring" element={<Recurring />} />
          <Route path="/insights" element={<Insights />} />
          <Route path="/report" element={<Report />} />
        </Routes>
      </main>
    </div>
  );
}
