import { TerminalPanel } from "./TerminalPanel";

export function TriggerList({ title, items }: { title: string; items: string[] }) {
  return (
    <TerminalPanel title={title}>
      <ul className="space-y-1 text-[12px] leading-5 text-terminal-text">
        {items.map((item) => (
          <li key={item}>- {item}</li>
        ))}
      </ul>
    </TerminalPanel>
  );
}
