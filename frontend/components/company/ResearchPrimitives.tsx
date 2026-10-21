import type { ReactNode } from "react";
import { confidenceLabel, directionLabel } from "../../lib/companyEconomicsAdapter";

export function SectionHeading({ number, title, eyebrow, id }: { number: string; title: string; eyebrow?: string; id?: string }) {
  return (
    <header className="research-section-heading" id={id}>
      <span className="research-kicker">{number} / {eyebrow ?? "Company Research"}</span>
      <h2>{title}</h2>
    </header>
  );
}

export function EvidenceTypeBadge({ type }: { type: "Direct" | "Proxy" | "Inference" }) {
  return <span className={`evidence-badge evidence-${type.toLowerCase()}`}>{type === "Direct" ? "Fact · Direct" : type === "Proxy" ? "Proxy · Calculated" : "Inference · Model"}</span>;
}

export function ConfidenceLabel({ value }: { value: string }) {
  return <span className="status-label status-neutral">{confidenceLabel(value)}</span>;
}

export function DirectionLabel({ value }: { value: string }) {
  const label = directionLabel(value);
  const tone = value === "EASING" ? "positive" : value === "TIGHTENING" ? "negative" : value === "MIXED" ? "caution" : "neutral";
  return <span className={`status-label status-${tone}`}>{label}</span>;
}

export function ResearchLabel({ children }: { children: ReactNode }) {
  return <span className="research-label">{children}</span>;
}

export function Unavailable({ reason = "Direct KPI unavailable" }: { reason?: string }) {
  return (
    <span className="unavailable-value">
      <strong>—</strong>
      <small>{reason}</small>
    </span>
  );
}

export function WhyItMatters({ children }: { children: ReactNode }) {
  return (
    <p className="why-it-matters">
      <span>Why this matters</span>
      {children}
    </p>
  );
}

export function InlineMetric({ label, value, detail }: { label: string; value: ReactNode; detail?: ReactNode }) {
  return (
    <div className="inline-metric">
      <ResearchLabel>{label}</ResearchLabel>
      <div className="inline-metric-value">{value}</div>
      {detail ? <div className="inline-metric-detail">{detail}</div> : null}
    </div>
  );
}

export function ResearchButton({ children, onClick, secondary = false, ariaLabel }: { children: ReactNode; onClick?: () => void; secondary?: boolean; ariaLabel?: string }) {
  return (
    <button type="button" className={`research-button${secondary ? " research-button-secondary" : ""}`} onClick={onClick} aria-label={ariaLabel}>
      {children}
    </button>
  );
}
