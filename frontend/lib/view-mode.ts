"use client";
import { useSyncExternalStore } from "react";

// Plain / Pro view for the macro pages (2026-11-27): plain words for everyday investors by default, technical names
// and detail in Pro view. A per-viewer convenience kept in this browser; plain when storage is unavailable.
const PRO_KEY = "chainstox.macroPro";
const listeners = new Set<() => void>();
function read() { try { return window.localStorage.getItem(PRO_KEY) === "1"; } catch { return false; } }
export function useProView(): [boolean, (v: boolean) => void] {
  const pro = useSyncExternalStore((cb) => { listeners.add(cb); return () => { listeners.delete(cb); }; }, read, () => false);
  return [pro, (v: boolean) => { try { window.localStorage.setItem(PRO_KEY, v ? "1" : "0"); } catch { /* ignore */ } listeners.forEach((cb) => cb()); }];
}
