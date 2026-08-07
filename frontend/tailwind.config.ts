import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#111827",
        muted: "#6B7280",
        line: "#E5E7EB",
        brand: {
          50: "#EFF6FF", 100: "#DBEAFE", 500: "#3B82F6",
          600: "#2563EB", 700: "#1D4ED8", 800: "#1E40AF",
        },
        critical: "#B91C1C",
        warn: "#B45309",
        good: "#047857",
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
    },
  },
  plugins: [],
} satisfies Config;
