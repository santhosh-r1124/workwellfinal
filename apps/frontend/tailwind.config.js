/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        workwell: {
          bg: "#0f172a",
          panel: "#111827",
          accent: "#38bdf8",
        },
      },
    },
  },
  plugins: [],
};
