import Placeholder from "./Placeholder";

export default function Upload() {
  return (
    <Placeholder title="Upload Statement" phase="Phase 2 (M2)">
      <p className="muted">
        Drag-and-drop CSV upload wiring to <code>POST /api/analyze</code> lands
        here.
      </p>
    </Placeholder>
  );
}
