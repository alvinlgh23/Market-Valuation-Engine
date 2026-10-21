import { TerminalPanel } from "./TerminalPanel";

export function DataQualityBlock({ source, coverage, refreshed }: { source: string; coverage: string; refreshed: string }) {
  return (
    <TerminalPanel title="Data Quality">
      <div className="grid gap-1 text-[12px] text-terminal-text">
        <div>Source: {source}</div>
        <div>Coverage: {coverage}</div>
        <div>Last refreshed: {refreshed}</div>
      </div>
    </TerminalPanel>
  );
}
