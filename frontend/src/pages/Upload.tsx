import { useRef, useState, type DragEvent } from "react";
import { useNavigate } from "react-router-dom";
import { analyze } from "../api";
import { useAnalysis } from "../store";

export default function Upload() {
  const { setResult } = useAnalysis();
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);

  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(file: File) {
    setError(null);
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setError("Phase 1 supports CSV files only — try a .csv statement.");
      return;
    }
    setLoading(true);
    try {
      const result = await analyze(file);
      setResult(result, file.name);
      navigate("/dashboard");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }

  return (
    <section className="page">
      <div className="page-head">
        <div>
          <h1>Upload Statement</h1>
          <p className="sub">
            Drop a bank statement CSV — it's parsed, cleaned and categorized on
            the backend. Nothing is stored.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="dropzone">
          <div className="spinner" />
          <p className="big">Analyzing…</p>
          <p className="hint">Ingesting, cleaning, categorizing and computing metrics.</p>
        </div>
      ) : (
        <div
          className={`dropzone${dragging ? " drag" : ""}`}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          role="button"
          tabIndex={0}
        >
          <p className="big">Drag &amp; drop a CSV here</p>
          <p className="hint">or click to choose a file</p>
          <input
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            hidden
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
              e.target.value = "";
            }}
          />
        </div>
      )}

      {error && <div className="upload-error">{error}</div>}

      <p className="samples">
        No statement handy? Sample CSVs live in <code>sample_data/</code>{" "}
        (HDFC, ICICI and a generic export).
      </p>
    </section>
  );
}
