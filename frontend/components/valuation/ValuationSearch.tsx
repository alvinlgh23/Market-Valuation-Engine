"use client";
import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { resolveCompany } from "../../lib/company-research-api";

export function ValuationSearch() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!query.trim()) { setMessage("Enter a ticker or company name."); return; }
    setLoading(true); setMessage("Resolving security…");
    try {
      const { resolution } = await resolveCompany(query.trim());
      if (!resolution) throw new Error("Provider returned no security resolution.");
      if (!resolution.supported) { setMessage(`${resolution.research_state}: ${resolution.reason || "Security unavailable."}`); return; }
      setMessage("Security resolved. Checking valuation framework and financial coverage…");
      router.push(`/valuation/${encodeURIComponent(resolution.ticker)}`);
    } catch (error) { setMessage(`PROVIDER_ERROR: ${error instanceof Error ? error.message : String(error)}`); }
    finally { setLoading(false); }
  }
  return <form className="object-search-form" onSubmit={submit}><label htmlFor="valuation-ticker">Analyze a company valuation</label><div><input id="valuation-ticker" value={query} onChange={event => setQuery(event.target.value)} placeholder="TSM or company name" /><button disabled={loading} type="submit">{loading ? "Resolving…" : "Open valuation →"}</button></div><small>A resolved security may require another framework or have insufficient financial data.</small><p role="status">{message}</p></form>;
}
