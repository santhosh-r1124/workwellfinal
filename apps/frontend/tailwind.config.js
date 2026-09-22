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
          ghost: "rgb(var(--accent-rgb) / 0.12)",
        },
        attention: {
          DEFAULT: channel("--attention-rgb"),
          ghost: "rgb(var(--attention-rgb) / 0.1)",
        },
        positive: {
          DEFAULT: channel("--positive-rgb"),
          ghost: "rgb(var(--positive-rgb) / 0.1)",
        },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
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
