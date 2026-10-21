import Link from "next/link";

export function ChainstoxBrand({ compact = false }: { compact?: boolean }) {
  return (
    <Link className={`chainstox-brand${compact ? " chainstox-brand-compact" : ""}`} href="/" aria-label="Chainstox Research System home">
      <span className="chainstox-mark" aria-hidden="true"><span>C</span><span>L</span></span>
      {!compact ? <span className="chainstox-wordmark"><strong>CHAINSTOX</strong><small>Research System</small></span> : null}
    </Link>
  );
}
