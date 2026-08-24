import type { Config } from "tailwindcss";

/**
 * VisaGuard design tokens.
 *
 * The palette is a deep navy dark theme with one confident accent (blue) and a
 * semantic risk ramp. Token names are stable — `neon.*` predates the theme and
 * is kept as the accent alias so existing pages keep compiling.
 */
export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Text
        ink: "#E8EEF9",
        "ink-strong": "#F8FAFF",
        muted: "#93A2BC",
        "muted-soft": "#6B7C99",

        // Hairlines
        line: "rgba(148,163,184,0.14)",
        "line-strong": "rgba(148,163,184,0.26)",

        // Surfaces — a proper elevation ladder rather than three ad-hoc greys
        surface: {
          DEFAULT: "#080D18",
          sunken: "#050911",
          elevated: "#0D1524",
          card: "#111B2E",
          hover: "#17233A",
          active: "#1D2B45",
        },

        // Brand accent
        neon: {
          50: "#EFF6FF",
          100: "#DBEAFE",
          200: "#BFDBFE",
          300: "#93C5FD",
          400: "#60A5FA",
          500: "#3B82F6",
          600: "#2563EB",
          700: "#1D4ED8",
          800: "#1E40AF",
          900: "#172554",
        },
        brand: {
          50: "#EFF6FF",
          100: "#DBEAFE",
          200: "#BFDBFE",
          300: "#93C5FD",
          400: "#60A5FA",
          500: "#3B82F6",
          600: "#2563EB",
          700: "#1D4ED8",
          800: "#1E40AF",
        },
        // Secondary accent, used sparingly for "cleared / verified" states
        teal: {
          300: "#5EEAD4",
          400: "#2DD4BF",
          500: "#14B8A6",
        },

        critical: "#F04438",
        warn: "#F79009",
        good: "#12B76A",
        info: "#3B82F6",
        risk: {
          low: "#12B76A",
          medium: "#F79009",
          high: "#F97316",
          critical: "#F04438",
        },
      },

      fontFamily: {
        sans: [
          "Inter",
          "InterFallback",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "sans-serif",
        ],
        display: ["Sora", "Inter", "InterFallback", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: [
          "JetBrains Mono",
          "Fira Code",
          "ui-monospace",
          "SF Mono",
          "Consolas",
          "monospace",
        ],
      },

      fontSize: {
        // Fluid display sizes so the hero holds up from 360px to 1920px
        "display-sm": ["clamp(1.75rem, 1.3rem + 2vw, 2.5rem)", { lineHeight: "1.15", letterSpacing: "-0.02em" }],
        "display-md": ["clamp(2rem, 1.4rem + 3vw, 3.25rem)", { lineHeight: "1.08", letterSpacing: "-0.025em" }],
        "display-lg": ["clamp(2.5rem, 1.6rem + 4vw, 4rem)", { lineHeight: "1.05", letterSpacing: "-0.03em" }],
      },

      borderRadius: {
        "4xl": "2rem",
      },

      boxShadow: {
        // Real elevation
        xs: "0 1px 2px rgba(2,6,16,0.4)",
        card: "0 1px 2px rgba(2,6,16,0.5), 0 0 0 1px rgba(148,163,184,0.05)",
        raised: "0 4px 12px -2px rgba(2,6,16,0.65), 0 0 0 1px rgba(148,163,184,0.06)",
        float: "0 18px 40px -12px rgba(2,6,16,0.85), 0 0 0 1px rgba(148,163,184,0.07)",
        overlay: "0 32px 64px -16px rgba(2,6,16,0.9), 0 0 0 1px rgba(148,163,184,0.09)",
        // Accent glows, toned down from the prototype
        glow: "0 0 0 1px rgba(59,130,246,0.18), 0 10px 30px -10px rgba(59,130,246,0.35)",
        "glow-sm": "0 4px 14px -4px rgba(59,130,246,0.4)",
        "glow-lg": "0 0 0 1px rgba(59,130,246,0.24), 0 24px 60px -16px rgba(59,130,246,0.45)",
      },

      transitionTimingFunction: {
        out: "cubic-bezier(0.22, 1, 0.36, 1)",
      },

      animation: {
        "pulse-glow": "pulseGlow 2.4s ease-in-out infinite",
        "slide-up": "slideUp 0.6s cubic-bezier(0.22,1,0.36,1) both",
        "fade-in": "fadeIn 0.4s ease-out both",
        shimmer: "shimmer 1.6s linear infinite",
        marquee: "marquee 42s linear infinite",
        "scan-line": "scanLine 3s linear infinite",
      },
      keyframes: {
        pulseGlow: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(59,130,246,0.25)" },
          "50%": { boxShadow: "0 0 0 8px rgba(59,130,246,0)" },
        },
        slideUp: {
          from: { opacity: "0", transform: "translateY(16px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        fadeIn: { from: { opacity: "0" }, to: { opacity: "1" } },
        shimmer: {
          "0%": { backgroundPosition: "-500px 0" },
          "100%": { backgroundPosition: "500px 0" },
        },
        marquee: {
          from: { transform: "translateX(0)" },
          to: { transform: "translateX(-50%)" },
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
