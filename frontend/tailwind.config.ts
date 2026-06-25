import type { Config } from "tailwindcss";

/**
 * Tailwind scans these paths for class names. A small custom palette keeps the
 * safety-focused UI consistent (calm slate surfaces, a clear emergency accent).
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        emergency: {
          DEFAULT: "#dc2626",
          dark: "#991b1b",
        },
        safe: {
          DEFAULT: "#16a34a",
        },
      },
    },
  },
  plugins: [],
};

export default config;
