/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F4F1EC",
        ink: "#1C1917",
        muted: "#78716C",
        line: "#E6E1D8",
        accent: {
          DEFAULT: "#0F6E56",
          dark: "#0C5946",
          soft: "#E5F3EE",
        },
      },
      fontFamily: {
        sans: ["Plus Jakarta Sans", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(28, 25, 23, 0.04), 0 8px 24px rgba(28, 25, 23, 0.04)",
      },
    },
  },
  plugins: [],
};
