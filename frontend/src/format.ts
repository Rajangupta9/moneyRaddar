// Formatting helpers — Indian rupee grouping and percentages.

const INR = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

const INR_PRECISE = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/** ₹1,20,150 — whole rupees, Indian digit grouping. */
export function inr(amount: number): string {
  return INR.format(amount);
}

/** ₹1,20,150.00 — two decimals, for tables where paise matter. */
export function inrPrecise(amount: number): string {
  return INR_PRECISE.format(amount);
}

/** Signed rupee value with an explicit + / − sign (for transaction rows). */
export function inrSigned(amount: number): string {
  const sign = amount < 0 ? "−" : "+";
  return `${sign}${INR_PRECISE.format(Math.abs(amount))}`;
}

/** 0.3214 → "32%". */
export function pct(fraction: number, digits = 0): string {
  return `${(fraction * 100).toFixed(digits)}%`;
}

/** "2026-06" → "Jun 2026" for trend axis labels. */
export function monthLabel(month: string): string {
  const [y, m] = month.split("-");
  const date = new Date(Number(y), Number(m) - 1, 1);
  return date.toLocaleDateString("en-IN", { month: "short", year: "numeric" });
}
