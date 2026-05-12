import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        obsidian: "#06070A",
        void: "#0B0D12",
        slate0: "#11141B",
        slate1: "#161A23",
        edge: "#1F2430",
        line: "#262C3A",
        text: "#ECEEF2",
        dim: "#C4CBD8",
        muted: "#99A1B2",
        mint: "#5EEAD4",
        "mint-soft": "#A7F3DE",
        lavender: "#A78BFA",
        "lavender-deep": "#7C5CFF",
        lime: "#BEF264",
        coral: "#FB7185",
        amber: "#FBBF24",
      },
      fontFamily: {
        display: ['"Instrument Serif"', "ui-serif", "Georgia", "serif"],
        sans: ['"Onest"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      letterSpacing: {
        widest2: "0.14em",
      },
      backdropBlur: {
        xs: "2px",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translate3d(0,0,0) scale(1)" },
          "50%": { transform: "translate3d(2%,-3%,0) scale(1.05)" },
        },
        sheen: {
          "0%": { transform: "translateX(-120%)" },
          "100%": { transform: "translateX(120%)" },
        },
        rise: {
          from: { opacity: "0", transform: "translateY(14px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        pulseRing: {
          "0%": { boxShadow: "0 0 0 0 rgba(94,234,212,0.45)" },
          "100%": { boxShadow: "0 0 0 14px rgba(94,234,212,0)" },
        },
        marquee: {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
      },
      animation: {
        float: "float 14s ease-in-out infinite",
        sheen: "sheen 1.6s cubic-bezier(.2,.7,.1,1) infinite",
        rise: "rise 700ms cubic-bezier(.2,.7,.1,1) both",
        pulseRing: "pulseRing 1.6s cubic-bezier(.2,.7,.1,1) infinite",
        marquee: "marquee 30s linear infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
