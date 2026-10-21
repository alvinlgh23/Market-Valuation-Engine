"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

const tooltipStyle = {
  background: "#0d0f0f",
  border: "1px solid #2a3030",
  color: "#e2e0d8",
  fontFamily: "var(--font-terminal)",
  fontSize: 12
};

export function IndexedLineChart({ data }: { data: Array<Record<string, string | number>> }) {
  return (
    <div className="h-56 border border-terminal-line bg-[#080909] p-2">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, left: -18, bottom: 0 }}>
          <CartesianGrid stroke="#202626" strokeDasharray="2 2" />
          <XAxis dataKey="period" stroke="#8a918c" tick={{ fontSize: 11 }} />
          <YAxis stroke="#8a918c" tick={{ fontSize: 11 }} />
          <Tooltip contentStyle={tooltipStyle} />
          <Legend wrapperStyle={{ fontSize: 11, color: "#8a918c" }} />
          <Line type="monotone" dataKey="price" stroke="#b36b65" strokeWidth={1.5} dot={false} />
          <Line type="monotone" dataKey="revenue" stroke="#d0a247" strokeWidth={1.5} dot={false} />
          <Line type="monotone" dataKey="eps" stroke="#83a883" strokeWidth={1.5} dot={false} />
          <Line type="monotone" dataKey="fcf" stroke="#9aa3a0" strokeWidth={1.5} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function CompactBarChart({ data }: { data: Array<Record<string, string | number>> }) {
  return (
    <div className="h-44 border border-terminal-line bg-[#080909] p-2">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 12, left: -18, bottom: 0 }}>
          <CartesianGrid stroke="#202626" strokeDasharray="2 2" />
          <XAxis dataKey="label" stroke="#8a918c" tick={{ fontSize: 11 }} />
          <YAxis stroke="#8a918c" tick={{ fontSize: 11 }} />
          <Tooltip contentStyle={tooltipStyle} />
          <Legend wrapperStyle={{ fontSize: 11, color: "#8a918c" }} />
          <Bar dataKey="capex" fill="#d0a247" />
          <Bar dataKey="operatingCashFlow" fill="#83a883" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
