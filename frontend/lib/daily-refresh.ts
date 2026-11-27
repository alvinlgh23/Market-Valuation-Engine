"use client";
import { useEffect, useRef, useState } from "react";

// P20 item 6: the first visit of the day starts one background refresh (daily_refresh.py); pages show its
// progress and one data date, and reload their precomputed data when it finishes.
export type RefreshStatus = {
  state: "NEVER_RUN" | "RUNNING" | "DONE" | "FAILED";
  data_date?: string; started_at?: string; finished_at?: string;
  total?: number | null; done?: number; current?: string | null; companies?: number;
  errors?: Array<{ step: string; error: string }>; fresh?: boolean; error?: string;
  market?: { state?: string; as_of?: string | null; sector_rows?: number } | null;
};

const POLL_MS = 4000;
let started: Promise<RefreshStatus | null> | null = null;

async function ask(start: boolean): Promise<RefreshStatus | null> {
  try {
    const response = await fetch(`/api/research?action=daily-refresh${start ? "&start=1" : ""}`, { cache: "no-store" });
    const body = await response.json();
    return (body.refresh as RefreshStatus | undefined) ?? null;
  } catch {
    return null;
  }
}

/** Starts today's refresh once per page session; calls `onFinished` when a running refresh completes. */
export function useDailyRefresh(onFinished?: () => void): RefreshStatus | null {
  const [status, setStatus] = useState<RefreshStatus | null>(null);
  const finished = useRef(onFinished);
  useEffect(() => { finished.current = onFinished; }, [onFinished]);
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let wasRunning = false;
    const follow = (value: RefreshStatus | null) => {
      if (!active) return;
      setStatus(value);
      if (value?.state === "RUNNING") {
        wasRunning = true;
        timer = setTimeout(() => { void ask(false).then(follow); }, POLL_MS);
      } else if (wasRunning && value?.state === "DONE") {
        started = null;
        finished.current?.();
      }
    };
    started ??= ask(true);
    void started.then(follow);
    return () => { active = false; if (timer) clearTimeout(timer); };
  }, []);
  return status;
}

function clock(value?: string) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

function day(value?: string) {
  if (!value) return "an unknown date";
  const date = new Date(`${value}T12:00:00`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("en-US", { day: "numeric", month: "short" });
}

/** One line: what date the page's data is for, and whether today's update is still running. */
export function refreshLine(status: RefreshStatus | null): { text: string; tone: "running" | "done" | "failed" | "none" } | null {
  if (!status) return null;
  if (status.state === "RUNNING") {
    const progress = status.total ? ` · ${status.done ?? 0} of ${status.total} steps` : "";
    const current = status.current && status.current !== "starting" ? ` (${status.current})` : "";
    return { text: `Updating today's market and company data${progress}${current}. Showing the last saved data until it finishes.`, tone: "running" };
  }
  if (status.state === "DONE") {
    const errors = status.errors?.length ? ` · ${status.errors.length} could not be updated (${status.errors.map((item) => item.step).join(", ")})` : "";
    const market = status.market?.as_of ? ` · market prices to ${day(status.market.as_of)}${status.market.state === "STALE" ? " (refresh kept the last valid prices)" : ""}` : "";
    return { text: `Company data for ${day(status.data_date)}${status.finished_at ? `, updated ${clock(status.finished_at)}` : ""}${market}${errors}`, tone: errors ? "failed" : "done" };
  }
  if (status.state === "FAILED") return { text: `Today's company update did not finish; showing data from ${day(status.data_date)} or earlier.`, tone: "failed" };
  return null;
}
