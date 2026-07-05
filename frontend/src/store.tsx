// Shared analysis state — holds the result of the last /api/analyze call so the
// Upload, Dashboard and Transactions views work off one source of truth.
//
// The prototype keeps this in memory (no persistence) — refreshing the page
// clears it, which matches the privacy-by-default posture (docs/architecture §8).

import { createContext, useContext, useState, type ReactNode } from "react";
import type { AnalyzeResponse } from "./types";

interface Analysis {
  result: AnalyzeResponse | null;
  fileName: string | null;
  setResult: (result: AnalyzeResponse, fileName: string) => void;
  clear: () => void;
}

const AnalysisContext = createContext<Analysis | null>(null);

export function AnalysisProvider({ children }: { children: ReactNode }) {
  const [result, setResultState] = useState<AnalyzeResponse | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  function setResult(next: AnalyzeResponse, name: string) {
    setResultState(next);
    setFileName(name);
  }

  function clear() {
    setResultState(null);
    setFileName(null);
  }

  return (
    <AnalysisContext.Provider value={{ result, fileName, setResult, clear }}>
      {children}
    </AnalysisContext.Provider>
  );
}

export function useAnalysis(): Analysis {
  const ctx = useContext(AnalysisContext);
  if (!ctx) throw new Error("useAnalysis must be used within <AnalysisProvider>");
  return ctx;
}
