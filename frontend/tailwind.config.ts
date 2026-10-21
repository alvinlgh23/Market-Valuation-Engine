import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        mono: ["var(--font-terminal)", "ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "monospace"]
      },
      colors: {
        terminal: {
          bg: "#070808",
          panel: "#0d0f0f",
          panel2: "#111414",
          line: "#2a3030",
          text: "#e2e0d8",
          muted: "#8a918c",
          faint: "#59605c",
          amber: "#d0a247",
          green: "#83a883",
          red: "#b36b65"
        }
      }
    }
  },
  plugins: []
};

export default config;
