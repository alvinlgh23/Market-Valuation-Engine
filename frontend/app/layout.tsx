import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Suspense } from "react";
import "./globals.css";

// Checklist 14.1: Geist (SIL Open Font License) for text, Geist Mono for figures; self-hosted by next/font.
const sans = Geist({ subsets: ["latin"], variable: "--font-geist-sans", display: "swap" });
const mono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono", display: "swap" });

export const metadata: Metadata = {
  title: "CHAINSTOX — Market Intelligence System",
  description: "Research terminal and explorable company economics reports"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable}`}>
      <body><Suspense fallback={<div className="app-route-loading" role="status">Loading research context…</div>}>{children}</Suspense></body>
    </html>
  );
}
