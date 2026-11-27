import Link from "next/link";

/** The owner's mark (same as alvin-lim.com): a rounded black tile with a white line rising to a dot. */
export function BrandMark({ size = 32 }: { size?: number }) {
  return <svg className="brand-mark" width={size} height={size} viewBox="0 0 40 40" aria-hidden="true">
    <rect x="0.5" y="0.5" width="39" height="39" rx="10" fill="#000" stroke="rgba(255,255,255,.22)" />
    <polyline points="8,27.7 17,19.3 21.5,24 30.2,14.2" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
    <circle cx="31" cy="13.3" r="2.5" fill="#fff" />
  </svg>;
}

export function ChainstoxBrand({ compact = false, large = false }: { compact?: boolean; large?: boolean }) {
  return (
    <Link className={`chainstox-brand${compact ? " chainstox-brand-compact" : ""}`} href="/" aria-label="Chainstox, Market Intelligence System — home">
      <span className="chainstox-mark" aria-hidden="true"><BrandMark size={large ? 46 : compact ? 34 : 36} /></span>
      {!compact ? <span className="chainstox-wordmark"><strong>Chainstox</strong><small>Market Intelligence System</small></span> : null}
    </Link>
  );
}
