import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Dark theme palette
        ink: "#E8E8ED",
        muted: "#8E8E9A",
        line: "rgba(255,255,255,0.06)",
        surface: {
          DEFAULT: "#0D0D14",
          elevated: "#13131F",
          card: "#161625",
          hover: "#1C1C30",
        },
        neon: {
          50: "#E6FFF0",
          100: "#B3FFD4",
          200: "#80FFB8",
          300: "#4DFF9C",
          400: "#1AFF80",
          500: "#00E666",
          600: "#00B350",
          700: "#00803A",
          800: "#004D24",
          900: "#001A0E",
        },
        brand: {
          50: "#E6FFF0",
          100: "#B3FFD4",
          500: "#00E666",
          600: "#00CC5A",
          700: "#00B350",
          800: "#009940",
        },
        critical: "#FF4D4D",
        warn: "#FFB84D",
        good: "#00E666",
        risk: {
          low: "#00E666",
          medium: "#FFB84D",
          high: "#FF8C4D",
          critical: "#FF4D4D",
        },
      },
      fontFamily: {
        sans: ["Share Tech Mono", "JetBrains Mono", "Fira Code", "ui-monospace", "SF Mono", "Consolas", "monospace"],
        display: ["Orbitron", "Share Tech Mono", "sans-serif"],
        mono: ["Fira Code", "JetBrains Mono", "ui-monospace", "SF Mono", "Consolas", "monospace"],
      },
      boxShadow: {
        glow: "0 0 20px rgba(0, 230, 102, 0.15), 0 0 60px rgba(0, 230, 102, 0.05)",
        "glow-sm": "0 0 10px rgba(0, 230, 102, 0.1)",
        "glow-lg": "0 0 40px rgba(0, 230, 102, 0.2), 0 0 100px rgba(0, 230, 102, 0.08)",
        card: "0 1px 3px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.04)",
      },
      animation: {
        "pulse-glow": "pulseGlow 2s ease-in-out infinite",
        "slide-up": "slideUp 0.5s ease-out",
        "fade-in": "fadeIn 0.3s ease-out",
        "scan-line": "scanLine 3s linear infinite",
      },
      keyframes: {
        pulseGlow: {
          "0%, 100%": { boxShadow: "0 0 10px rgba(0, 230, 102, 0.1)" },
          "50%": { boxShadow: "0 0 25px rgba(0, 230, 102, 0.2)" },
        },
        slideUp: {
          from: { opacity: "0", transform: "translateY(20px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        fadeIn: {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        scanLine: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" },
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
