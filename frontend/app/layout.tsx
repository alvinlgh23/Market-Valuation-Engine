import type { Metadata } from "next";
import { Suspense } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "CHAINSTOX — Market Intelligence System",
  description: "Research terminal and explorable company economics reports"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body><Suspense fallback={<div className="app-route-loading" role="status">Loading research context…</div>}>{children}</Suspense></body>
    </html>
  );
}
