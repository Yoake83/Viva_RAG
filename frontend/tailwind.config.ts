import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        desk: "var(--desk)",
        paper: "var(--paper)",
        rule: "var(--rule)",
        margin: "var(--margin)",
        ink: "var(--ink)",
        soft: "var(--ink-soft)",
        hl: "var(--hl)",
        ok: "var(--ok)",
        warn: "var(--warn)",
      },
      fontFamily: {
        sans: ["'Bricolage Grotesque Variable'", "ui-sans-serif", "system-ui", "sans-serif"],
        serif: ["'Literata Variable'", "Georgia", "serif"],
      },
    },
  },
  plugins: [],
};
export default config;
