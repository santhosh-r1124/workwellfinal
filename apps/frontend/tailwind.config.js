/** Lets a token be used both as a solid colour and with /opacity modifiers. */
const channel = (name) => `rgb(var(${name}) / <alpha-value>)`;

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ground: channel("--ground-rgb"),
        surface: {
          DEFAULT: channel("--surface-rgb"),
          sunken: channel("--surface-sunken-rgb"),
          raised: channel("--surface-raised-rgb"),
        },
        line: {
          DEFAULT: channel("--line-rgb"),
          soft: channel("--line-soft-rgb"),
        },
        text: {
          DEFAULT: channel("--text-rgb"),
          muted: channel("--text-muted-rgb"),
          faint: channel("--text-faint-rgb"),
        },
        accent: {
          DEFAULT: channel("--accent-rgb"),
          deep: channel("--accent-deep-rgb"),
          /* A second, quieter step so "notable" and "normal" stay
             distinguishable in the light theme, where both the accent
             and its deep variant are simply black. */
          soft: channel("--accent-soft-rgb"),
          ghost: "var(--accent-ghost)",
        },
        "on-accent": channel("--on-accent-rgb"),
        attention: {
          DEFAULT: channel("--attention-rgb"),
          ghost: "var(--attention-ghost)",
        },
        positive: {
          DEFAULT: channel("--positive-rgb"),
          ghost: "var(--positive-ghost)",
        },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      backdropBlur: {
        glass: "20px",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "pulse-ring": {
          "0%": { transform: "scale(0.95)", opacity: "0.7" },
          "70%": { transform: "scale(1.25)", opacity: "0" },
          "100%": { transform: "scale(1.25)", opacity: "0" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.22s ease-out both",
        "pulse-ring": "pulse-ring 2.4s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
    },
  },
  plugins: [],
};
