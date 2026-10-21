const toneClass = (value: unknown) => {
  const text = String(value);
  if (text.includes("TRIGGERED") || text.includes("Weak") || text.includes("Underperform")) return "text-terminal-red";
  if (text.includes("WATCH") || text.includes("Demanding") || text.includes("Compressed")) return "text-terminal-amber";
  if (text.includes("NORMAL") || text.includes("Positive") || text.includes("+")) return "text-terminal-green";
  return "text-terminal-text";
};

export function TerminalTable<T extends object>({ rows, columns }: { rows: T[]; columns?: Array<keyof T & string> | string[] }) {
  const headers = columns ?? Object.keys(rows[0] ?? {});
  return (
    <div className="overflow-x-auto border border-terminal-line">
      <table className="w-full min-w-[520px] border-collapse text-left text-[12px] leading-5">
        <thead className="bg-terminal-panel2 text-[10px] uppercase tracking-[0.08em] text-terminal-muted">
          <tr>
            {headers.map((header) => (
              <th key={header} className="border-b border-terminal-line px-2 py-1 font-medium">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr key={idx} className="odd:bg-[#0a0c0c] even:bg-terminal-panel">
              {headers.map((header) => (
                <td key={header} className={`border-b border-terminal-line/70 px-2 py-1 align-top ${toneClass(row[header as keyof T])}`}>
                  {String(row[header as keyof T] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
