// Shared placeholder for Phase 0 — each view is fleshed out in a later phase.

import type { ReactNode } from "react";

interface Props {
  title: string;
  phase: string;
  children?: ReactNode;
}

export default function Placeholder({ title, phase, children }: Props) {
  return (
    <section className="page">
      <h1>{title}</h1>
      <p className="muted">
        Scaffolded in Phase 0 — implemented in <strong>{phase}</strong>.
      </p>
      {children}
    </section>
  );
}
