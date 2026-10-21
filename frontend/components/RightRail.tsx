import type { WatchItem } from "../lib/types";

const tone: Record<string, string> = {
  triggered: "text-terminal-amber",
  watch: "text-terminal-amber",
  positive: "text-terminal-green",
  negative: "text-terminal-red",
  normal: "text-terminal-text",
  muted: "text-terminal-muted"
};

export function RightRail({ watch }: { watch: WatchItem[] }) {
  return (
    <aside className="border-l border-terminal-line bg-terminal-panel p-2 text-[12px]">
      <div className="mb-2 border-b border-terminal-line pb-2 text-[10px] uppercase tracking-[0.08em] text-terminal-faint">Watch / Data</div>
      <div className="space-y-3">
        {watch.map((item) => (
          <div key={item.label} className="border-b border-terminal-line/70 pb-3">
            <div className="text-[10px] uppercase tracking-[0.08em] text-terminal-muted">{item.label}</div>
            <div className="mt-1 text-[16px] font-semibold tabular-nums text-terminal-text">{item.value}</div>
            {item.change ? <div className="mt-1 text-[11px] text-terminal-amber">▲ {item.change}</div> : null}
            {item.threshold ? (
              <div className="mt-2 grid grid-cols-[70px_1fr] gap-2 text-[10px] uppercase tracking-[0.08em]">
                <span className="text-terminal-faint">Threshold</span>
                <span className="text-terminal-muted">{item.threshold}</span>
              </div>
            ) : null}
            <div className="mt-2 grid grid-cols-[70px_1fr] gap-2 text-[10px] uppercase tracking-[0.08em]">
              <span className="text-terminal-faint">Status</span>
              <span className={tone[item.tone]}>{item.status}</span>
            </div>
            <div className="mt-2">
              <div className="text-[10px] uppercase tracking-[0.08em] text-terminal-faint">Why it matters</div>
              <p className="mt-1 text-[11px] normal-case leading-4 text-terminal-muted">{item.why}</p>
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
