// Mirror of the backend canonical model (docs/architecture.md §5).
// Kept in sync with backend/app/models.py by hand for the prototype.

export type Category =
  | "Food"
  | "Travel"
  | "Shopping"
  | "Bills"
  | "EMI"
  | "Subscriptions"
  | "Salary"
  | "Rent"
  | "Investments"
  | "Other";

export type Direction = "debit" | "credit";
export type CategorySource = "rule" | "memory" | "llm";

export interface Transaction {
  id: string;
  date: string;
  description_raw: string;
  merchant: string | null;
  amount: number;
  direction: Direction;
  balance: number | null;
  category: Category;
  category_source: CategorySource;
  confidence: number | null;
  is_recurring: boolean;
  recurring_id: string | null;
}

export interface RecurringSeries {
  id: string;
  merchant: string;
  type: string;
  cadence: string;
  average_amount: number;
  occurrences: number;
  next_expected_date: string | null;
  transaction_ids: string[];
}

export interface CategoryBreakdown {
  category: Category;
  amount: number;
  pct: number;
}

export interface Summary {
  period: { start: string; end: string };
  total_income: number;
  total_spend: number;
  net_savings: number;
  savings_rate: number;
  by_category: CategoryBreakdown[];
  top_categories: Category[];
  biggest_transaction: {
    id: string;
    amount: number;
    merchant: string | null;
    description_raw: string | null;
    date: string | null;
  } | null;
  recurring_total: number;
  recurring_count: number;
  monthly_trend: { month: string; spend: number; income: number }[];
}

export interface Insight {
  title: string;
  detail: string;
  severity: "info" | "warning" | "positive";
}

export interface AnalyzeResponse {
  session_id: string;
  transactions: Transaction[];
  summary: Summary | null;
  recurring: RecurringSeries[];
  insights: Insight[];
}

export interface HealthResponse {
  status: string;
  version: string;
  llm_model: string;
  llm_enabled: boolean;
}
