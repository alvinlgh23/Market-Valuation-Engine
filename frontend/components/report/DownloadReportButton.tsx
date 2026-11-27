"use client";
import { useState } from "react";

// "Full report": generates the research note PDF on the server (/api/report/[ticker]) and downloads it.
export function DownloadReportButton({ ticker, label = "Full report" }: { ticker: string; label?: string }) {
  const [state, setState] = useState<"idle" | "working" | "failed">("idle");
  async function download() {
    if (state === "working") return;
    setState("working");
    try {
      const response = await fetch(`/api/report/${encodeURIComponent(ticker)}`, { cache: "no-store" });
      if (!response.ok) throw new Error(String(response.status));
      const blob = await response.blob();
      const name = /filename="([^"]+)"/.exec(response.headers.get("Content-Disposition") ?? "")?.[1] ?? `CHAINSTOX_${ticker}.pdf`;
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = name;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
      setState("idle");
    } catch {
      setState("failed");
    }
  }
  return <button type="button" onClick={download} disabled={state === "working"} aria-busy={state === "working"}
    title="Download the research note as a PDF">
    {state === "working" ? "Generating PDF…" : state === "failed" ? "PDF failed · retry" : label}
  </button>;
}
